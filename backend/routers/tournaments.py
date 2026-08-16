# routers/tournaments.py

from fastapi import APIRouter
from database import get_connection

router = APIRouter(prefix="/tournaments", tags=["tournaments"])


@router.get("/")
def list_tournaments():
    """List all tournaments, for tagging uploads to one."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT id, name, type, year, host_school, location
        FROM tournaments ORDER BY name
    """)
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows
