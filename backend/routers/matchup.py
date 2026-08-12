# routers/matchup.py

from fastapi import APIRouter, HTTPException, Query
from analytics.matchup_engine import get_head_to_head

router = APIRouter(prefix="/matchup", tags=["matchup"])


@router.get("/")
def head_to_head(
    team1: int = Query(..., description="Team 1 ID"),
    team2: int = Query(..., description="Team 2 ID"),
):
    """
    Full head-to-head matchup analysis: team comparison, per-category advantages,
    player matchups, UC recommendations, and scouting report.
    """
    if team1 == team2:
        raise HTTPException(status_code=400, detail="Cannot compare a team against itself.")
    return get_head_to_head(team1, team2)
