# analytics/team_analyzer.py
# Team-level analytics: coverage heatmap, gap identification, overall strength.

from database import get_connection
from config import GAP_THRESHOLD
from analytics.player_analyzer import get_all_players_for_team, get_player_category_stats


def get_team_category_coverage(team_id: int, tournament_id: int = None) -> dict:
    """
    For each category, returns the best accuracy among all team players
    (for coverage/gap-finding — "does someone on this roster know this
    category" is genuinely a best-player question) AND a pooled team
    accuracy (total correct / total buzzed-in across every player who's
    faced it — for get_team_overview's overall_strength, since players are
    assigned per round, not routed to their specialty category, so a
    realistic strength estimate needs the whole roster's performance, not
    just whoever happened to do best).

    Also flags categories as gaps if best accuracy < GAP_THRESHOLD.

    Returns:
        {
          "CATEGORY_NAME": {
            "best_accuracy": float,
            "best_player": str,
            "best_buzzed_in": int,      # sample size behind best_accuracy
            "team_accuracy": float,     # pooled across all players
            "team_buzzed_in": int,      # pooled sample size
            "is_gap": bool,
            "player_scores": [{"name": str, "accuracy": float}, ...]
          },
          ...
        }
    """
    players = get_all_players_for_team(team_id, tournament_id)
    coverage = {}

    for player in players:
        cat_stats = get_player_category_stats(player["id"], tournament_id)
        for cat, stats in cat_stats.items():
            if cat not in coverage:
                coverage[cat] = {
                    "best_accuracy": None,
                    "best_player": None,
                    "best_buzzed_in": 0,
                    "team_correct": 0,
                    "team_buzzed_in": 0,
                    "is_gap": True,
                    "player_scores": [],
                }
            entry = coverage[cat]
            entry["player_scores"].append({
                "player_id": player["id"],
                "name": player["name"],
                "accuracy": stats["accuracy"],
                "buzzed_in": stats["buzzed_in"],
            })
            entry["team_correct"] += stats["answered_correctly"]
            entry["team_buzzed_in"] += stats["buzzed_in"]
            # First player sets the initial "best" even at 0% accuracy, so a
            # category no one has ever gotten right still carries a real
            # sample size instead of defaulting to 0.
            if entry["best_accuracy"] is None or stats["accuracy"] > entry["best_accuracy"]:
                entry["best_accuracy"] = stats["accuracy"]
                entry["best_player"] = player["name"]
                entry["best_buzzed_in"] = stats["buzzed_in"]

    # Determine gaps and finalize the pooled team accuracy
    for cat, entry in coverage.items():
        entry["is_gap"] = entry["best_accuracy"] < GAP_THRESHOLD
        entry["team_accuracy"] = (
            round(entry["team_correct"] / entry["team_buzzed_in"], 4)
            if entry["team_buzzed_in"] > 0 else 0.0
        )
        del entry["team_correct"]  # internal accumulator, not part of the public shape

    return coverage


def get_team_overview(team_id: int, tournament_id: int = None) -> dict:
    """
    Full team overview dict: players, category coverage, strengths, gaps,
    win/loss record, standings.
    """
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT id, name FROM teams WHERE id = ?", (team_id,))
    team = cur.fetchone()
    if not team:
        conn.close()
        return {}

    # Win/loss record — optionally filtered by tournament
    t_filter = "AND tournament_id = ?" if tournament_id else ""
    t_params = (team_id, tournament_id) if tournament_id else (team_id,)
    cur.execute(f"""
        SELECT SUM(win) AS wins,
               COUNT(*) - SUM(win) AS losses,
               SUM(points_for) AS total_pts,
               SUM(points_against) AS total_opp_pts
        FROM team_game_results
        WHERE team_id = ? {t_filter}
    """, t_params)
    record = cur.fetchone()

    # Standings — optionally filtered by tournament
    cur.execute(f"""
        SELECT wins, losses, total_points, total_opp_pts
        FROM standings WHERE team_id = ? {t_filter}
    """, t_params)
    standing = cur.fetchone()

    # Playoff record — tracked separately from round-robin (team_game_results
    # above only covers round-robin; playoff_results has no win/loss column,
    # so it's derived here from the two scores).
    pr_filter = "AND tournament_id = ?" if tournament_id else ""
    pr_params = (team_id, team_id, tournament_id) if tournament_id else (team_id, team_id)
    cur.execute(f"""
        SELECT team1_id, team1_score, team2_id, team2_score
        FROM playoff_results
        WHERE (team1_id = ? OR team2_id = ?) {pr_filter}
    """, pr_params)
    playoff_wins = playoff_losses = playoff_points_for = playoff_points_against = 0
    for row in cur.fetchall():
        if row["team1_id"] == team_id:
            my_score, opp_score = row["team1_score"], row["team2_score"]
        else:
            my_score, opp_score = row["team2_score"], row["team1_score"]
        playoff_points_for += my_score
        playoff_points_against += opp_score
        if my_score > opp_score:
            playoff_wins += 1
        else:
            playoff_losses += 1

    # Ultimate Challenge totals — optionally filtered by tournament. UC is
    # worth up to 500 pts/game (often more than the entire Face-Off round)
    # but has no per-player attribution, so it can't join the per-category
    # coverage above; it's folded into overall_strength as one more
    # sample-weighted term instead.
    uc_filter = "AND g.tournament_id = ?" if tournament_id else ""
    uc_params = (team_id, tournament_id) if tournament_id else (team_id,)
    cur.execute(f"""
        SELECT SUM(u.questions_correct) AS correct, SUM(u.questions_attempted) AS attempted
        FROM uc_events u JOIN games g ON g.id = u.game_id
        WHERE u.team_id = ? {uc_filter}
    """, uc_params)
    uc_row = cur.fetchone()
    uc_correct = uc_row["correct"] or 0
    uc_attempted = uc_row["attempted"] or 0

    conn.close()

    coverage = get_team_category_coverage(team_id, tournament_id)
    players = get_all_players_for_team(team_id, tournament_id)

    # Compute overall team strength as a weighted average of pooled
    # per-category accuracy — total correct / total buzzed-in across every
    # player who's faced that category, not just whoever did best. Players
    # are assigned per round in this format, not routed to their specialty
    # category, so a single star can't be routed to the exact category they
    # know best; a realistic strength number needs the whole roster's
    # performance, not its ceiling. (best_accuracy/best_player are kept
    # as-is for the coverage heatmap and gap-finding above, where "does
    # someone on this roster know this" is correctly a best-player question.)
    # A 0% category is a real result and must count toward the average —
    # excluding it would let a team's worst categories vanish from their
    # own strength score. Weighted by sample size so a category backed by
    # 8-10 attempts counts more than one decided by a single lucky buzz.
    total_weight = sum(v["team_buzzed_in"] for v in coverage.values())
    weighted_sum = sum(v["team_accuracy"] * v["team_buzzed_in"] for v in coverage.values())

    uc_accuracy = round(uc_correct / uc_attempted, 4) if uc_attempted > 0 else None
    if uc_attempted > 0:
        weighted_sum += uc_accuracy * uc_attempted
        total_weight += uc_attempted

    overall_strength = round(weighted_sum / total_weight, 4) if total_weight > 0 else 0.0

    # Top 3 strongest and weakest categories
    sorted_cats = sorted(coverage.items(), key=lambda x: x[1]["best_accuracy"], reverse=True)
    top_categories = [
        {"category": k, "accuracy": v["best_accuracy"], "best_player": v["best_player"]}
        for k, v in sorted_cats[:3]
    ]
    weak_categories = [
        {"category": k, "accuracy": v["best_accuracy"], "best_player": v["best_player"]}
        for k, v in sorted_cats[-3:] if v["is_gap"]
    ]

    round_robin_wins = record["wins"] or 0 if record else 0
    round_robin_losses = record["losses"] or 0 if record else 0

    return {
        "id": team["id"],
        "name": team["name"],
        "overall_strength": overall_strength,
        # wins/losses is the TOTAL record (round-robin + playoffs) — the
        # single number every page should show by default. Consumers that
        # want the breakdown use round_robin_wins/losses and
        # playoff_wins/losses directly instead of re-deriving it themselves,
        # which is what let Team Overview and Head-to-Head disagree before.
        "wins": round_robin_wins + playoff_wins,
        "losses": round_robin_losses + playoff_losses,
        "round_robin_wins": round_robin_wins,
        "round_robin_losses": round_robin_losses,
        "total_points": record["total_pts"] or 0 if record else 0,
        "total_opp_points": record["total_opp_pts"] or 0 if record else 0,
        "category_coverage": coverage,
        "top_categories": top_categories,
        "weak_categories": weak_categories,
        "players": players,
        "standings": dict(standing) if standing else {},
        "uc_accuracy": uc_accuracy,
        "uc_attempted": uc_attempted,
        "playoff_wins": playoff_wins,
        "playoff_losses": playoff_losses,
        "playoff_points_for": playoff_points_for,
        "playoff_points_against": playoff_points_against,
    }


def get_all_teams(tournament_id: int = None) -> list:
    """
    Return a summary list of teams with basic stats. Pass tournament_id to
    only include teams that actually played in that tournament (rather than
    every team, most of whom never touched a given site).
    """
    conn = get_connection()
    cur = conn.cursor()
    if tournament_id:
        cur.execute("""
            SELECT DISTINCT t.id, t.name
            FROM teams t
            JOIN games g ON (g.team1_id = t.id OR g.team2_id = t.id)
            WHERE g.tournament_id = ?
            ORDER BY t.name
        """, (tournament_id,))
    else:
        cur.execute("SELECT id, name FROM teams ORDER BY name")
    rows = cur.fetchall()
    conn.close()

    teams = []
    for row in rows:
        overview = get_team_overview(row["id"], tournament_id)
        teams.append({
            "id": row["id"],
            "name": row["name"],
            "overall_strength": overview.get("overall_strength", 0),
            "wins": overview.get("wins", 0),
            "losses": overview.get("losses", 0),
        })
    return sorted(teams, key=lambda t: t["overall_strength"], reverse=True)
