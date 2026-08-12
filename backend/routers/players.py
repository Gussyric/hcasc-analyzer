# routers/players.py

from fastapi import APIRouter, HTTPException
from analytics.player_analyzer import get_player_profile
from database import get_connection

router = APIRouter(prefix="/players", tags=["players"])


@router.get("/{player_id}")
def get_player(player_id: int):
    """Full player profile including per-category stats."""
    profile = get_player_profile(player_id)
    if not profile:
        raise HTTPException(status_code=404, detail=f"Player {player_id} not found.")
    return profile
