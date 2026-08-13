# analytics/player_analyzer.py
# Derives per-player performance metrics from the database.

from database import get_connection
from config import MIN_SAMPLE_SIZE


def get_player_category_stats(player_id: int, tournament_id: int = None) -> dict:
    """
    Returns per-category accuracy stats for a player, sourced from
    player_stats (summary PDF) and game_events (scoresheet data).

    Priority: player_stats rows are the authoritative per-category source
    since they come from official tournament documents.
    """
    conn = get_connection()
    cur = conn.cursor()

    # From player_stats (summary PDF)
    t_filter = "AND tournament_id = ?" if tournament_id else ""
    t_params = (player_id, tournament_id) if tournament_id else (player_id,)
    cur.execute(f"""
        SELECT category,
               SUM(questions_heard)    AS heard,
               SUM(buzzed_in)          AS buzzed,
               SUM(answered_correctly) AS correct
        FROM player_stats
        WHERE player_id = ? {t_filter}
        GROUP BY category
    """, t_params)
    stats_rows = cur.fetchall()

    # From game_events (scoresheet) — supplemental
    ge_filter = "AND g.tournament_id = ?" if tournament_id else ""
    ge_params = (player_id, player_id, player_id, player_id) + ((tournament_id,) if tournament_id else ())
    cur.execute(f"""
        SELECT ge.category,
               COUNT(*) AS attempts,
               SUM(CASE WHEN ge.team1_player_id = ? AND ge.team1_fo_correct = 1 THEN 1
                        WHEN ge.team2_player_id = ? AND ge.team2_fo_correct = 1 THEN 1
                        ELSE 0 END) AS correct
        FROM game_events ge
        JOIN games g ON g.id = ge.game_id
        WHERE (ge.team1_player_id = ? OR ge.team2_player_id = ?) {ge_filter}
        GROUP BY ge.category
    """, ge_params)
    event_rows = cur.fetchall()

    conn.close()

    # Merge: prefer player_stats; supplement with game_events for missing categories
    categories = {}

    for row in stats_rows:
        cat = row["category"]
        heard = row["heard"] or 0
        buzzed = row["buzzed"] or 0
        correct = row["correct"] or 0
        accuracy = round(correct / buzzed, 4) if buzzed > 0 else 0.0
        categories[cat] = {
            "category": cat,
            "questions_heard": heard,
            "buzzed_in": buzzed,
            "answered_correctly": correct,
            "accuracy": accuracy,
            "sample_reliable": buzzed >= MIN_SAMPLE_SIZE,
            "source": "summary",
        }

    for row in event_rows:
        cat = row["category"]
        if cat in categories:
            continue  # already have summary data
        attempts = row["attempts"] or 0
        correct = row["correct"] or 0
        accuracy = round(correct / attempts, 4) if attempts > 0 else 0.0
        categories[cat] = {
            "category": cat,
            "questions_heard": attempts,
            "buzzed_in": attempts,
            "answered_correctly": correct,
            "accuracy": accuracy,
            "sample_reliable": attempts >= MIN_SAMPLE_SIZE,
            "source": "scoresheet",
        }

    return categories


def get_player_overall_strength(player_id: int) -> float:
    """
    Weighted average accuracy across all categories with reliable samples.
    Returns a 0.0-1.0 score.
    """
    stats = get_player_category_stats(player_id)
    if not stats:
        return 0.0

    reliable = [v for v in stats.values() if v["sample_reliable"]]
    if not reliable:
        # Fall back to all categories if nothing is reliable
        reliable = list(stats.values())
    if not reliable:
        return 0.0

    # Weight by number of questions buzzed in (more attempts = more weight)
    total_weight = sum(v["buzzed_in"] for v in reliable)
    if total_weight == 0:
        return 0.0

    weighted_sum = sum(v["accuracy"] * v["buzzed_in"] for v in reliable)
    return round(weighted_sum / total_weight, 4)


def get_player_profile(player_id: int) -> dict:
    """Full player profile dict suitable for API response."""
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT p.id, p.name, t.name AS team_name, t.id AS team_id
        FROM players p
        JOIN teams t ON t.id = p.team_id
        WHERE p.id = ?
    """, (player_id,))
    row = cur.fetchone()
    conn.close()

    if not row:
        return {}

    category_stats = get_player_category_stats(player_id)
    overall = get_player_overall_strength(player_id)

    return {
        "id": row["id"],
        "name": row["name"],
        "team_id": row["team_id"],
        "team_name": row["team_name"],
        "overall_strength": overall,
        "category_stats": list(category_stats.values()),
    }


def get_all_players_for_team(team_id: int) -> list:
    """Return profile dicts for all players on a team, sorted by overall strength."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id FROM players WHERE team_id = ?", (team_id,))
    rows = cur.fetchall()
    conn.close()

    profiles = [get_player_profile(r["id"]) for r in rows]
    return sorted(profiles, key=lambda p: p.get("overall_strength", 0), reverse=True)
