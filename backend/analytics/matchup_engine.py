# analytics/matchup_engine.py
# Head-to-head analysis: team vs team and player vs player.

from database import get_connection
from analytics.team_analyzer import get_team_category_coverage, get_team_overview
from analytics.player_analyzer import get_all_players_for_team, get_player_category_stats
from analytics.uc_analyzer import get_uc_recommendation, get_team_uc_stats


def get_head_to_head(team1_id: int, team2_id: int) -> dict:
    """
    Full head-to-head analysis between two teams.
    Returns team comparison, per-category advantages, player matchups,
    UC comparison, and a scouting report.
    """
    t1 = get_team_overview(team1_id)
    t2 = get_team_overview(team2_id)

    t1_coverage = get_team_category_coverage(team1_id)
    t2_coverage = get_team_category_coverage(team2_id)

    all_cats = sorted(set(list(t1_coverage.keys()) + list(t2_coverage.keys())))

    # Per-category comparison
    category_comparison = []
    t1_advantages = 0
    t2_advantages = 0
    toss_ups = 0

    for cat in all_cats:
        t1_acc = t1_coverage.get(cat, {}).get("best_accuracy", 0.0)
        t2_acc = t2_coverage.get(cat, {}).get("best_accuracy", 0.0)
        t1_player = t1_coverage.get(cat, {}).get("best_player", "—")
        t2_player = t2_coverage.get(cat, {}).get("best_player", "—")

        diff = t1_acc - t2_acc
        if diff > 0.10:
            advantage = "team1"
            t1_advantages += 1
        elif diff < -0.10:
            advantage = "team2"
            t2_advantages += 1
        else:
            advantage = "even"
            toss_ups += 1

        category_comparison.append({
            "category": cat,
            "team1_accuracy": round(t1_acc, 4),
            "team1_best_player": t1_player,
            "team2_accuracy": round(t2_acc, 4),
            "team2_best_player": t2_player,
            "advantage": advantage,
            "margin": round(abs(diff), 4),
        })

    # Overall strength comparison
    t1_strength = t1.get("overall_strength", 0)
    t2_strength = t2.get("overall_strength", 0)

    # Player vs player matchups
    player_matchups = _player_matchups(team1_id, team2_id)

    # UC comparison
    uc_rec_t1 = get_uc_recommendation(team1_id, team2_id)
    uc_rec_t2 = get_uc_recommendation(team2_id, team1_id)
    t1_uc = get_team_uc_stats(team1_id)
    t2_uc = get_team_uc_stats(team2_id)

    # Check historical head-to-head in the database
    historical = _get_historical_matchups(team1_id, team2_id)

    # Scouting report
    scouting_report = _build_scouting_report(
        t1, t2, category_comparison, t1_advantages, t2_advantages,
        uc_rec_t1, uc_rec_t2, historical
    )

    return {
        "team1": {"id": team1_id, "name": t1.get("name"), "overall_strength": t1_strength,
                  "wins": t1.get("wins", 0), "losses": t1.get("losses", 0)},
        "team2": {"id": team2_id, "name": t2.get("name"), "overall_strength": t2_strength,
                  "wins": t2.get("wins", 0), "losses": t2.get("losses", 0)},
        "overall_advantage": "team1" if t1_strength > t2_strength else (
            "team2" if t2_strength > t1_strength else "even"
        ),
        "category_comparison": category_comparison,
        "category_advantages": {
            "team1": t1_advantages,
            "team2": t2_advantages,
            "even": toss_ups,
        },
        "player_matchups": player_matchups,
        "uc": {
            "team1_recommendation": uc_rec_t1.get("recommendation"),
            "team1_reason": uc_rec_t1.get("reason"),
            "team2_recommendation": uc_rec_t2.get("recommendation"),
            "team2_reason": uc_rec_t2.get("reason"),
            "team1_uc_strength": _uc_strength(t1_uc),
            "team2_uc_strength": _uc_strength(t2_uc),
        },
        "historical_matchups": historical,
        "scouting_report": scouting_report,
    }


def _uc_strength(uc_stats: dict) -> float:
    """Average accuracy across all UC categories a team has played."""
    cats = uc_stats.get("per_category", {})
    if not cats:
        return 0.0
    accs = [v["avg_accuracy"] for v in cats.values()]
    return round(sum(accs) / len(accs), 4) if accs else 0.0


def _player_matchups(team1_id: int, team2_id: int) -> list:
    """
    Cross-match players by overall strength rank.
    P1 rank1 vs P2 rank1, P1 rank2 vs P2 rank2, etc.
    """
    t1_players = get_all_players_for_team(team1_id)
    t2_players = get_all_players_for_team(team2_id)

    matchups = []
    max_len = max(len(t1_players), len(t2_players))

    for i in range(max_len):
        p1 = t1_players[i] if i < len(t1_players) else None
        p2 = t2_players[i] if i < len(t2_players) else None

        if p1 and p2:
            # Per-category comparison
            p1_cats = get_player_category_stats(p1["id"])
            p2_cats = get_player_category_stats(p2["id"])
            all_cats = set(list(p1_cats.keys()) + list(p2_cats.keys()))

            cat_details = []
            for cat in sorted(all_cats):
                p1_acc = p1_cats.get(cat, {}).get("accuracy", 0)
                p2_acc = p2_cats.get(cat, {}).get("accuracy", 0)
                cat_details.append({
                    "category": cat,
                    "player1_accuracy": round(p1_acc, 4),
                    "player2_accuracy": round(p2_acc, 4),
                    "advantage": "player1" if p1_acc > p2_acc + 0.10
                                 else "player2" if p2_acc > p1_acc + 0.10 else "even"
                })

            advantage = (
                "player1" if p1["overall_strength"] > p2["overall_strength"]
                else "player2" if p2["overall_strength"] > p1["overall_strength"]
                else "even"
            )
        else:
            cat_details = []
            advantage = "player1" if p1 else "player2"

        matchups.append({
            "position": i + 1,
            "player1": {"id": p1["id"], "name": p1["name"],
                         "overall_strength": p1["overall_strength"]} if p1 else None,
            "player2": {"id": p2["id"], "name": p2["name"],
                         "overall_strength": p2["overall_strength"]} if p2 else None,
            "advantage": advantage,
            "category_details": cat_details,
        })

    return matchups


def _get_historical_matchups(team1_id: int, team2_id: int) -> list:
    """Pull any previous games between these two teams from the database."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT g.game_number, g.match_number, g.room,
               t1.name AS team1_name, g.team1_score,
               t2.name AS team2_name, g.team2_score
        FROM games g
        JOIN teams t1 ON t1.id = g.team1_id
        JOIN teams t2 ON t2.id = g.team2_id
        WHERE (g.team1_id = ? AND g.team2_id = ?)
           OR (g.team1_id = ? AND g.team2_id = ?)
        ORDER BY g.match_number, g.game_number
    """, (team1_id, team2_id, team2_id, team1_id))
    rows = cur.fetchall()
    conn.close()

    return [
        {
            "game": row["game_number"],
            "match": row["match_number"],
            "room": row["room"],
            "team1": row["team1_name"],
            "team1_score": row["team1_score"],
            "team2": row["team2_name"],
            "team2_score": row["team2_score"],
            "winner": row["team1_name"] if row["team1_score"] > row["team2_score"]
                      else row["team2_name"],
        }
        for row in rows
    ]


def _build_scouting_report(t1, t2, cat_comparison, t1_adv, t2_adv,
                           uc_rec_t1, uc_rec_t2, historical) -> list:
    """Generate a list of plain-language scouting insights."""
    report = []
    t1_name = t1.get("name", "Team 1")
    t2_name = t2.get("name", "Team 2")

    # Overall strength
    t1_str = t1.get("overall_strength", 0)
    t2_str = t2.get("overall_strength", 0)
    if abs(t1_str - t2_str) < 0.05:
        report.append(f"{t1_name} and {t2_name} are closely matched overall "
                       f"({t1_str*100:.1f}% vs {t2_str*100:.1f}%).")
    elif t1_str > t2_str:
        report.append(f"{t1_name} holds an overall strength advantage "
                       f"({t1_str*100:.1f}% vs {t2_str*100:.1f}%).")
    else:
        report.append(f"{t2_name} holds an overall strength advantage "
                       f"({t2_str*100:.1f}% vs {t1_str*100:.1f}%).")

    # Category dominance
    if t1_adv > t2_adv:
        report.append(f"{t1_name} leads in {t1_adv} categories vs {t2_adv} for {t2_name}.")
    elif t2_adv > t1_adv:
        report.append(f"{t2_name} leads in {t2_adv} categories vs {t1_adv} for {t1_name}.")

    # Highlight biggest mismatches
    big_gaps = [c for c in cat_comparison if c["margin"] > 0.30]
    for gap in big_gaps[:3]:
        winner = t1_name if gap["advantage"] == "team1" else t2_name
        loser = t2_name if gap["advantage"] == "team1" else t1_name
        report.append(
            f"Major edge for {winner} in '{gap['category']}' "
            f"({gap['team1_accuracy']*100:.0f}% vs {gap['team2_accuracy']*100:.0f}%)."
        )

    # UC recommendations
    uc1 = uc_rec_t1.get("recommendation")
    uc2 = uc_rec_t2.get("recommendation")
    if uc1:
        report.append(f"UC strategy for {t1_name}: {uc_rec_t1.get('reason', '')}")
    if uc2:
        report.append(f"UC strategy for {t2_name}: {uc_rec_t2.get('reason', '')}")

    # Historical record
    if historical:
        t1_wins = sum(1 for g in historical if g["winner"] == t1_name)
        t2_wins = sum(1 for g in historical if g["winner"] == t2_name)
        report.append(
            f"Historical record in this dataset: {t1_name} {t1_wins} - {t2_wins} {t2_name}."
        )

    return report
