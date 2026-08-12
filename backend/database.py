# database.py - SQLite schema definition and connection management

import sqlite3
import os
from config import DATABASE_PATH


def get_connection() -> sqlite3.Connection:
    """Return a SQLite connection with row_factory set for dict-like access."""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    """Create all tables if they don't already exist."""
    conn = get_connection()
    cur = conn.cursor()

    # -------------------------------------------------------------------------
    # teams
    # -------------------------------------------------------------------------
    cur.execute("""
        CREATE TABLE IF NOT EXISTS teams (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            name        TEXT    NOT NULL UNIQUE,
            room        TEXT,           -- e.g. "1", "2"
            created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # -------------------------------------------------------------------------
    # players
    # -------------------------------------------------------------------------
    cur.execute("""
        CREATE TABLE IF NOT EXISTS players (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            team_id     INTEGER NOT NULL REFERENCES teams(id),
            name        TEXT    NOT NULL,
            UNIQUE(team_id, name)
        )
    """)

    # -------------------------------------------------------------------------
    # games  (one row per scoresheet)
    # -------------------------------------------------------------------------
    cur.execute("""
        CREATE TABLE IF NOT EXISTS games (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            match_number    INTEGER,
            game_number     INTEGER,
            room            TEXT,
            team1_id        INTEGER REFERENCES teams(id),
            team2_id        INTEGER REFERENCES teams(id),
            team1_score     INTEGER,
            team2_score     INTEGER,
            source_file     TEXT,
            created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # -------------------------------------------------------------------------
    # game_events  (one row per question attempt in a Face-Off round)
    # -------------------------------------------------------------------------
    cur.execute("""
        CREATE TABLE IF NOT EXISTS game_events (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            game_id         INTEGER NOT NULL REFERENCES games(id),
            round_number    INTEGER NOT NULL,   -- 1, 2, or 3
            question_number INTEGER,
            category        TEXT,
            -- left side (team1)
            team1_player_id INTEGER REFERENCES players(id),
            team1_fo_pts    INTEGER DEFAULT 0,
            team1_bonus_pts INTEGER DEFAULT 0,
            team1_fo_correct    INTEGER DEFAULT 0,  -- 1 = yes, 0 = no
            -- right side (team2)
            team2_player_id INTEGER REFERENCES players(id),
            team2_fo_pts    INTEGER DEFAULT 0,
            team2_bonus_pts INTEGER DEFAULT 0,
            team2_fo_correct    INTEGER DEFAULT 0
        )
    """)

    # -------------------------------------------------------------------------
    # uc_events  (one row per Ultimate Challenge round — two per game)
    # -------------------------------------------------------------------------
    cur.execute("""
        CREATE TABLE IF NOT EXISTS uc_events (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            game_id             INTEGER NOT NULL REFERENCES games(id),
            team_id             INTEGER NOT NULL REFERENCES teams(id),
            category            TEXT    NOT NULL,
            points_scored       INTEGER DEFAULT 0,
            questions_correct   INTEGER DEFAULT 0,  -- count of question numbers listed
            questions_attempted INTEGER DEFAULT 10, -- always 10 in UC
            correct_q_numbers   TEXT    -- comma-separated, e.g. "1,2,6,9,10"
        )
    """)

    # -------------------------------------------------------------------------
    # player_stats  (from ASUPlayerStats summary PDF — one row per player/game)
    # -------------------------------------------------------------------------
    cur.execute("""
        CREATE TABLE IF NOT EXISTS player_stats (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            player_id           INTEGER NOT NULL REFERENCES players(id),
            match_label         TEXT,   -- e.g. "Rm 2 - Gm 5"
            category            TEXT,
            questions_heard     INTEGER DEFAULT 0,
            buzzed_in           INTEGER DEFAULT 0,
            answered_correctly  INTEGER DEFAULT 0,
            accuracy_pct        REAL    DEFAULT 0.0
        )
    """)

    # -------------------------------------------------------------------------
    # team_game_results  (from ASUResultsByTeam summary PDF)
    # -------------------------------------------------------------------------
    cur.execute("""
        CREATE TABLE IF NOT EXISTS team_game_results (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            team_id         INTEGER NOT NULL REFERENCES teams(id),
            opponent_id     INTEGER REFERENCES teams(id),
            points_for      INTEGER DEFAULT 0,
            points_against  INTEGER DEFAULT 0,
            win             INTEGER DEFAULT 0,  -- 1 = win, 0 = loss
            room            TEXT
        )
    """)

    # -------------------------------------------------------------------------
    # standings  (from ASURoundRobinResults)
    # -------------------------------------------------------------------------
    cur.execute("""
        CREATE TABLE IF NOT EXISTS standings (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            team_id         INTEGER NOT NULL REFERENCES teams(id),
            room            TEXT,
            wins            INTEGER DEFAULT 0,
            losses          INTEGER DEFAULT 0,
            total_points    INTEGER DEFAULT 0,
            total_opp_pts   INTEGER DEFAULT 0
        )
    """)

    # -------------------------------------------------------------------------
    # playoff_results  (from ASUPlayoffResults)
    # -------------------------------------------------------------------------
    cur.execute("""
        CREATE TABLE IF NOT EXISTS playoff_results (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            game_number INTEGER,
            team1_id    INTEGER REFERENCES teams(id),
            team1_score INTEGER,
            team2_id    INTEGER REFERENCES teams(id),
            team2_score INTEGER
        )
    """)

    conn.commit()
    conn.close()
    print(f"[DB] Initialized database at '{DATABASE_PATH}'")


def reset_db():
    """Drop and recreate the database — useful during development."""
    if os.path.exists(DATABASE_PATH):
        os.remove(DATABASE_PATH)
        print(f"[DB] Removed existing database '{DATABASE_PATH}'")
    init_db()


if __name__ == "__main__":
    init_db()
