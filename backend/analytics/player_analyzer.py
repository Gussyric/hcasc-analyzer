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


def get_player_points_breakdown(player_id: int) -> dict:
    """
    Points a player personally earned (Face-Off + Bonus) per game, and
    their share of their team's game and season point totals.

    Ultimate Challenge points are NOT included — UC is a single team-wide
    category pick with no per-player attribution in the source data, so
    "team total" here means the team's full game/season score while
    "player points" only ever covers their Face-Off + Bonus contributions.
    """
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT team_id FROM players WHERE id = ?", (player_id,))
    row = cur.fetchone()
    if not row:
        conn.close()
        return {}
    team_id = row["team_id"]

    cur.execute("""
        SELECT g.id AS game_id, g.match_number, g.game_number, g.room,
               g.team1_id, g.team1_score, g.team2_score,
               t1.name AS team1_name, t2.name AS team2_name,
               SUM(CASE WHEN ge.team1_player_id = ? THEN ge.team1_fo_pts + ge.team1_bonus_pts
                        WHEN ge.team2_player_id = ? THEN ge.team2_fo_pts + ge.team2_bonus_pts
                        ELSE 0 END) AS player_points
        FROM game_events ge
        JOIN games g ON g.id = ge.game_id
        JOIN teams t1 ON t1.id = g.team1_id
        JOIN teams t2 ON t2.id = g.team2_id
        WHERE ge.team1_player_id = ? OR ge.team2_player_id = ?
        GROUP BY g.id
        ORDER BY g.match_number, g.game_number
    """, (player_id, player_id, player_id, player_id))
    game_rows = cur.fetchall()

    per_game = []
    season_player_points = 0
    for r in game_rows:
        is_team1 = r["team1_id"] == team_id
        team_game_points = r["team1_score"] if is_team1 else r["team2_score"]
        opponent = r["team2_name"] if is_team1 else r["team1_name"]
        player_points = r["player_points"] or 0
        season_player_points += player_points
        per_game.append({
            "match": r["match_number"],
            "game": r["game_number"],
            "room": r["room"],
            "opponent": opponent,
            "player_points": player_points,
            "team_game_points": team_game_points,
            "share_of_game": round(player_points / team_game_points, 4) if team_game_points else 0.0,
        })

    cur.execute("""
        SELECT SUM(CASE WHEN team1_id = ? THEN team1_score
                         WHEN team2_id = ? THEN team2_score
                         ELSE 0 END) AS total
        FROM games WHERE team1_id = ? OR team2_id = ?
    """, (team_id, team_id, team_id, team_id))
    team_season_total = cur.fetchone()["total"] or 0

    conn.close()

    return {
        "per_game": per_game,
        "season_player_points": season_player_points,
        "team_season_total_points": team_season_total,
        "season_share": round(season_player_points / team_season_total, 4) if team_season_total else 0.0,
    }


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
    points = get_player_points_breakdown(player_id)

    return {
        "id": row["id"],
        "name": row["name"],
        "team_id": row["team_id"],
        "team_name": row["team_name"],
        "overall_strength": overall,
        "category_stats": list(category_stats.values()),
        "points_per_game": points.get("per_game", []),
        "season_player_points": points.get("season_player_points", 0),
        "team_season_total_points": points.get("team_season_total_points", 0),
        "season_points_share": points.get("season_share", 0.0),
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
