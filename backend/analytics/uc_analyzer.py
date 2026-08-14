# analytics/uc_analyzer.py
# Ultimate Challenge performance analytics and recommendations.
# UC: team selects a category, 60 seconds, 10 questions, 50 pts each = 500 max.

from database import get_connection
from config import UC_MAX_POINTS, UC_MAX_QUESTIONS


def get_team_uc_stats(team_id: int) -> dict:
    """
    Aggregate UC performance for a team across all games.
    Returns per-category stats and an overall UC strength score.
    """
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT category,
               COUNT(*)                    AS times_selected,
               SUM(points_scored)          AS total_pts,
               SUM(questions_correct)      AS total_correct,
               SUM(questions_attempted)    AS total_attempted,
               AVG(questions_correct * 1.0 / questions_attempted) AS avg_accuracy
        FROM uc_events
        WHERE team_id = ?
        GROUP BY category
        ORDER BY avg_accuracy DESC
    """, (team_id,))
    rows = cur.fetchall()
    conn.close()

    per_category = {}
    for row in rows:
        cat = row["category"]
        times = row["times_selected"] or 0
        total_pts = row["total_pts"] or 0
        total_correct = row["total_correct"] or 0
        total_attempted = row["total_attempted"] or 0
        avg_acc = row["avg_accuracy"] or 0.0

        per_category[cat] = {
            "category": cat,
            "times_selected": times,
            "total_points_scored": total_pts,
            "total_correct": total_correct,
            "total_attempted": total_attempted,
            "avg_accuracy": round(avg_acc, 4),
            "avg_points_per_game": round(total_pts / times, 1) if times > 0 else 0.0,
            "max_possible_per_game": UC_MAX_POINTS,
        }

    # Sort by avg accuracy desc
    sorted_cats = sorted(per_category.values(), key=lambda x: x["avg_accuracy"], reverse=True)

    # Most frequently chosen category
    most_common = max(per_category.items(), key=lambda x: x[1]["times_selected"], default=(None, {}))[0]

    return {
        "team_id": team_id,
        "per_category": per_category,
        "sorted_by_accuracy": sorted_cats,
        "most_selected_category": most_common,
        "top_3_recommended": sorted_cats[:3],
    }


def get_uc_recommendation(team_id: int, opponent_id: int = None) -> dict:
    """
    Recommend a UC category for the given team.
    If opponent_id is provided, factors in the opponent's UC weaknesses.

    Strategy:
      - Primary: your highest-accuracy UC category
      - With opponent: your best category where opponent has lowest accuracy (or hasn't played)
    """
    team_stats = get_team_uc_stats(team_id)
    opp_stats = get_team_uc_stats(opponent_id) if opponent_id else None

    my_cats = team_stats["per_category"]
    opp_cats = opp_stats["per_category"] if opp_stats else {}

    if not my_cats:
        return {
            "recommendation": None,
            "reason": "No Ultimate Challenge data available for this team.",
        }

    # Score each of my UC categories
    scored = []
    for cat, my_data in my_cats.items():
        my_acc = my_data["avg_accuracy"]
        # Opponent's accuracy in same category (lower is better for us).
        # None means the opponent has never played this category — there's
        # no real number to report, and blending in a guessed value would
        # quietly bias the score, so we fall back to your own accuracy.
        opp_data = opp_cats.get(cat)
        opp_acc = opp_data["avg_accuracy"] if opp_data else None

        if opponent_id and opp_acc is not None:
            score = (my_acc * 0.6) + ((1 - opp_acc) * 0.4)
        else:
            score = my_acc

        scored.append({
            "category": cat,
            "your_accuracy": my_acc,
            "your_avg_points": my_data["avg_points_per_game"],
            "times_selected": my_data["times_selected"],
            "opponent_accuracy": round(opp_acc, 4) if opp_acc is not None else None,
            "opponent_times_selected": opp_data["times_selected"] if opp_data else 0,
            "opponent_has_data": opp_acc is not None,
            "recommendation_score": round(score, 4),
        })

    scored.sort(key=lambda x: x["recommendation_score"], reverse=True)

    top = scored[0] if scored else None
    reason = ""
    if top:
        reason = (
            f"'{top['category']}' is your strongest UC category "
            f"({top['your_accuracy']*100:.1f}% accuracy, "
            f"avg {top['your_avg_points']:.0f} pts/game)."
        )
        if opponent_id:
            if top["opponent_accuracy"] is not None:
                reason += (
                    f" Opponent accuracy in this category: "
                    f"{top['opponent_accuracy']*100:.1f}%."
                )
            else:
                reason += " Opponent has no recorded history in this category."

    return {
        "recommendation": top,
        "all_options": scored,
        "reason": reason,
    }


def get_game_uc_history(team_id: int) -> list:
    """Return chronological list of UC events for a team."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT u.category, u.points_scored, u.questions_correct,
               u.questions_attempted, u.correct_q_numbers,
               g.game_number, g.match_number, g.room
        FROM uc_events u
        JOIN games g ON g.id = u.game_id
        WHERE u.team_id = ?
        ORDER BY g.match_number, g.game_number
    """, (team_id,))
    rows = cur.fetchall()
    conn.close()

    return [
        {
            "match": row["match_number"],
            "game": row["game_number"],
            "room": row["room"],
            "category": row["category"],
            "points_scored": row["points_scored"],
            "questions_correct": row["questions_correct"],
            "questions_attempted": row["questions_attempted"],
            "accuracy": round(row["questions_correct"] / row["questions_attempted"], 4)
                        if row["questions_attempted"] > 0 else 0.0,
            "correct_questions": row["correct_q_numbers"],
        }
        for row in rows
    ]
