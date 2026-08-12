# routers/teams.py

from fastapi import APIRouter, HTTPException
from analytics.team_analyzer import get_all_teams, get_team_overview
from analytics.lineup_optimizer import get_lineup_recommendations
from analytics.uc_analyzer import get_team_uc_stats, get_uc_recommendation, get_game_uc_history
from database import get_connection

router = APIRouter(prefix="/teams", tags=["teams"])


@router.get("/")
def list_teams():
    """List all teams with basic stats, sorted by overall strength."""
    return get_all_teams()


@router.get("/{team_id}/overview")
def team_overview(team_id: int):
    """Full team overview: strength, coverage heatmap, player list, record."""
    overview = get_team_overview(team_id)
    if not overview:
        raise HTTPException(status_code=404, detail=f"Team {team_id} not found.")
    return overview


@router.get("/{team_id}/lineup")
def team_lineup(team_id: int):
    """Optimal 3-player lineup recommendations from the full roster."""
    result = get_lineup_recommendations(team_id)
    if "error" in result:
        raise HTTPException(status_code=422, detail=result["error"])
    return result


@router.get("/{team_id}/ultimate-challenge")
def team_uc(team_id: int, opponent_id: int = None):
    """
    Ultimate Challenge stats and category recommendation.
    Pass ?opponent_id=X for a matchup-specific recommendation.
    """
    stats = get_team_uc_stats(team_id)
    recommendation = get_uc_recommendation(team_id, opponent_id)
    history = get_game_uc_history(team_id)
    return {
        "stats": stats,
        "recommendation": recommendation,
        "history": history,
    }


@router.get("/{team_id}/players")
def team_players(team_id: int):
    """All player profiles for a team."""
    from analytics.player_analyzer import get_all_players_for_team
    players = get_all_players_for_team(team_id)
    if not players:
        raise HTTPException(status_code=404, detail=f"No players found for team {team_id}.")
    return players
