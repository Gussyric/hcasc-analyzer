# analytics/lineup_optimizer.py
# Scores every 3-of-4 player combination and ranks them with explanations.

from itertools import combinations
from analytics.player_analyzer import get_all_players_for_team, get_player_category_stats
from config import GAP_THRESHOLD


def _score_combination(players: list, all_categories: set) -> dict:
    """
    Score a group of 3 players on:
      - Coverage breadth: fraction of categories with at least one player >= GAP_THRESHOLD
      - Combined strength: sum of best accuracy per category
      - Depth: average of all best-per-category accuracies
    Returns a score dict.
    """
    # Per-category best accuracy across the 3 players
    cat_best = {}
    for player in players:
        cat_stats = get_player_category_stats(player["id"])
        for cat, stats in cat_stats.items():
            if cat not in cat_best or stats["accuracy"] > cat_best[cat]["accuracy"]:
                cat_best[cat] = {"accuracy": stats["accuracy"], "player": player["name"]}

    # Coverage breadth (out of all categories seen in this tournament)
    covered = sum(1 for c in cat_best.values() if c["accuracy"] >= GAP_THRESHOLD)
    total_cats = max(len(all_categories), 1)
    coverage_score = covered / total_cats

    # Combined strength
    accuracies = [c["accuracy"] for c in cat_best.values()]
    combined_strength = sum(accuracies) / len(accuracies) if accuracies else 0.0

    # Gaps in this combination
    gaps = [cat for cat, v in cat_best.items() if v["accuracy"] < GAP_THRESHOLD]

    return {
        "coverage_score": round(coverage_score, 4),
        "combined_strength": round(combined_strength, 4),
        "overall_score": round((coverage_score * 0.5) + (combined_strength * 0.5), 4),
        "categories_covered": covered,
        "total_categories": total_cats,
        "category_best": cat_best,
        "gaps": gaps,
    }


def get_lineup_recommendations(team_id: int) -> dict:
    """
    Enumerate all C(n,3) player combinations for a team.
    For a 4-player roster this is exactly 4 combinations.
    Returns ranked combinations with explanations.
    """
    players = get_all_players_for_team(team_id)

    if len(players) < 3:
        return {
            "error": f"Team only has {len(players)} player(s). Need at least 3.",
            "combinations": []
        }

    # Gather all categories seen across this team
    all_categories = set()
    for p in players:
        all_categories.update(get_player_category_stats(p["id"]).keys())

    results = []
    for combo in combinations(players, 3):
        score_data = _score_combination(list(combo), all_categories)

        # Who is sitting out?
        combo_ids = {p["id"] for p in combo}
        bench = [p for p in players if p["id"] not in combo_ids]
        bench_names = [p["name"] for p in bench]

        # Explanation: what do we lose by benching these players?
        bench_impact = []
        for benched in bench:
            b_cats = get_player_category_stats(benched["id"])
            unique_strong = []
            for cat, stats in b_cats.items():
                if stats["accuracy"] >= GAP_THRESHOLD:
                    # Check if anyone else on the lineup covers this
                    others_cover = any(
                        get_player_category_stats(p["id"]).get(cat, {}).get("accuracy", 0) >= GAP_THRESHOLD
                        for p in combo
                    )
                    if not others_cover:
                        unique_strong.append(cat)
            if unique_strong:
                bench_impact.append(
                    f"Benching {benched['name']} leaves gap in: {', '.join(unique_strong)}"
                )

        explanation = bench_impact if bench_impact else [
            f"Benching {', '.join(bench_names)} has minimal coverage impact."
        ]

        results.append({
            "players": [{"id": p["id"], "name": p["name"],
                         "overall_strength": p["overall_strength"]} for p in combo],
            "bench": bench_names,
            "overall_score": score_data["overall_score"],
            "coverage_score": score_data["coverage_score"],
            "combined_strength": score_data["combined_strength"],
            "categories_covered": score_data["categories_covered"],
            "total_categories": score_data["total_categories"],
            "gaps": score_data["gaps"],
            "explanation": explanation,
        })

    # Sort: highest overall_score first
    results.sort(key=lambda x: x["overall_score"], reverse=True)

    # Rank them
    for i, r in enumerate(results):
        r["rank"] = i + 1

    return {
        "team_id": team_id,
        "total_players": len(players),
        "combinations": results,
        "recommended": results[0] if results else None,
    }
