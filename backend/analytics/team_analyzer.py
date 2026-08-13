# analytics/team_analyzer.py
# Team-level analytics: coverage heatmap, gap identification, overall strength.

from database import get_connection
from config import GAP_THRESHOLD
from analytics.player_analyzer import get_all_players_for_team, get_player_category_stats


def get_team_category_coverage(team_id: int, tournament_id: int = None) -> dict:
    """
    For each category, returns the best accuracy among all team players.
    Also flags categories as gaps if best accuracy < GAP_THRESHOLD.

    Returns:
        {
          "CATEGORY_NAME": {
            "best_accuracy": float,
            "best_player": str,
            "is_gap": bool,
            "player_scores": [{"name": str, "accuracy": float}, ...]
          },
          ...
        }
    """
    players = get_all_players_for_team(team_id)
    coverage = {}

    for player in players:
        cat_stats = get_player_category_stats(player["id"])
        for cat, stats in cat_stats.items():
            if cat not in coverage:
                coverage[cat] = {
                    "best_accuracy": 0.0,
                    "best_player": None,
                    "is_gap": True,
                    "player_scores": [],
                }
            coverage[cat]["player_scores"].append({
                "player_id": player["id"],
                "name": player["name"],
                "accuracy": stats["accuracy"],
                "buzzed_in": stats["buzzed_in"],
            })
            if stats["accuracy"] > coverage[cat]["best_accuracy"]:
                coverage[cat]["best_accuracy"] = stats["accuracy"]
                coverage[cat]["best_player"] = player["name"]

    # Determine gaps
    for cat in coverage:
        coverage[cat]["is_gap"] = coverage[cat]["best_accuracy"] < GAP_THRESHOLD

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

    conn.close()

    coverage = get_team_category_coverage(team_id, tournament_id)
    players = get_all_players_for_team(team_id)

    # Compute overall team strength as avg of best-per-category accuracies
    best_scores = [v["best_accuracy"] for v in coverage.values() if v["best_accuracy"] > 0]
    overall_strength = round(sum(best_scores) / len(best_scores), 4) if best_scores else 0.0

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

    wins = record["wins"] or 0 if record else 0
    losses = record["losses"] or 0 if record else 0

    return {
        "id": team["id"],
        "name": team["name"],
        "overall_strength": overall_strength,
        "wins": wins,
        "losses": losses,
        "total_points": record["total_pts"] or 0 if record else 0,
        "total_opp_points": record["total_opp_pts"] or 0 if record else 0,
        "category_coverage": coverage,
        "top_categories": top_categories,
        "weak_categories": weak_categories,
        "players": players,
        "standings": dict(standing) if standing else {},
    }


def get_all_teams() -> list:
    """Return a summary list of all teams with basic stats."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, name FROM teams ORDER BY name")
    rows = cur.fetchall()
    conn.close()

    teams = []
    for row in rows:
        overview = get_team_overview(row["id"])
        teams.append({
            "id": row["id"],
            "name": row["name"],
            "overall_strength": overview.get("overall_strength", 0),
            "wins": overview.get("wins", 0),
            "losses": overview.get("losses", 0),
        })
    return sorted(teams, key=lambda t: t["overall_strength"], reverse=True)
