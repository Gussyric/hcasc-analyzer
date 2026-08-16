# main.py - FastAPI application entry point

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from database import init_db
from routers import upload, teams, players, matchup, tournaments
from config import CATEGORIES

app = FastAPI(
    title="HCASC Team & Player Strength Analyzer",
    description="Analyzes HCASC NQT scoresheet and summary PDFs to provide "
                "team strength, player performance, lineup optimization, "
                "Ultimate Challenge strategy, and head-to-head matchup analysis.",
    version="1.0.0",
)

# Allow React dev server on port 3000
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize DB on startup
@app.on_event("startup")
def startup_event():
    init_db()

# Register routers
app.include_router(upload.router)
app.include_router(teams.router)
app.include_router(players.router)
app.include_router(matchup.router)
app.include_router(tournaments.router)


@app.get("/")
def root():
    return {
        "service": "HCASC Analyzer API",
        "version": "1.0.0",
        "endpoints": [
            "POST /upload/pdf",
            "POST /upload/batch-scoresheets",
            "GET  /teams/",
            "GET  /teams/{id}/overview",
            "GET  /teams/{id}/players",
            "GET  /teams/{id}/lineup",
            "GET  /teams/{id}/ultimate-challenge",
            "GET  /matchup/?team1={id}&team2={id}",
            "GET  /players/{id}",
            "GET  /tournaments/",
        ],
    }


@app.get("/config/categories")
def get_categories():
    """Return the currently configured list of academic categories."""
    return {"categories": CATEGORIES}
