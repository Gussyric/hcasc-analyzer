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
    # tournaments  (one row per NQT site or NCT)
    # -------------------------------------------------------------------------
    cur.execute("""
        CREATE TABLE IF NOT EXISTS tournaments (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            name        TEXT    NOT NULL UNIQUE,  -- e.g. "ASU NQT 2026"
            type        TEXT,                     -- "NQT" or "NCT"
            year        INTEGER,
            host_school TEXT,
            location    TEXT
        )
    """)

    # -------------------------------------------------------------------------
    # teams
    # -------------------------------------------------------------------------
    cur.execute("""
        CREATE TABLE IF NOT EXISTS teams (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            name        TEXT    NOT NULL UNIQUE,
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
            tournament_id   INTEGER REFERENCES tournaments(id),
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
            round_number    INTEGER NOT NULL,
            question_number INTEGER,
            category        TEXT,
            team1_player_id INTEGER REFERENCES players(id),
            team1_fo_pts    INTEGER DEFAULT 0,
            team1_bonus_pts INTEGER DEFAULT 0,
            team1_fo_correct    INTEGER DEFAULT 0,
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
            questions_correct   INTEGER DEFAULT 0,
            questions_attempted INTEGER DEFAULT 10,
            correct_q_numbers   TEXT
        )
    """)

    # -------------------------------------------------------------------------
    # player_stats  (from PlayerStats summary PDF)
    # -------------------------------------------------------------------------
    cur.execute("""
        CREATE TABLE IF NOT EXISTS player_stats (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            tournament_id       INTEGER REFERENCES tournaments(id),
            player_id           INTEGER NOT NULL REFERENCES players(id),
            match_label         TEXT,
            category            TEXT,
            questions_heard     INTEGER DEFAULT 0,
            buzzed_in           INTEGER DEFAULT 0,
            answered_correctly  INTEGER DEFAULT 0,
            accuracy_pct        REAL    DEFAULT 0.0
        )
    """)

    # -------------------------------------------------------------------------
    # team_game_results  (from ResultsByTeam summary PDF)
    # -------------------------------------------------------------------------
    cur.execute("""
        CREATE TABLE IF NOT EXISTS team_game_results (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            tournament_id   INTEGER REFERENCES tournaments(id),
            team_id         INTEGER NOT NULL REFERENCES teams(id),
            opponent_id     INTEGER REFERENCES teams(id),
            points_for      INTEGER DEFAULT 0,
            points_against  INTEGER DEFAULT 0,
            win             INTEGER DEFAULT 0,
            room            TEXT
        )
    """)

    # -------------------------------------------------------------------------
    # standings  (from RoundRobinResults summary PDF)
    # -------------------------------------------------------------------------
    cur.execute("""
        CREATE TABLE IF NOT EXISTS standings (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            tournament_id   INTEGER REFERENCES tournaments(id),
            team_id         INTEGER NOT NULL REFERENCES teams(id),
            room            TEXT,
            wins            INTEGER DEFAULT 0,
            losses          INTEGER DEFAULT 0,
            total_points    INTEGER DEFAULT 0,
            total_opp_pts   INTEGER DEFAULT 0
        )
    """)

    # -------------------------------------------------------------------------
    # playoff_results  (from PlayoffResults summary PDF)
    # -------------------------------------------------------------------------
    cur.execute("""
        CREATE TABLE IF NOT EXISTS playoff_results (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            tournament_id   INTEGER REFERENCES tournaments(id),
            game_number     INTEGER,
            team1_id        INTEGER REFERENCES teams(id),
            team1_score     INTEGER,
            team2_id        INTEGER REFERENCES teams(id),
            team2_score     INTEGER
        )
    """)

    # -------------------------------------------------------------------------
    # imported_files  (dedup guard — one row per PDF ever successfully parsed)
    # -------------------------------------------------------------------------
    cur.execute("""
        CREATE TABLE IF NOT EXISTS imported_files (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            file_hash       TEXT    NOT NULL UNIQUE,
            filename        TEXT,
            file_type       TEXT,
            tournament_id   INTEGER REFERENCES tournaments(id),
            imported_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    conn.close()
    print(f"[DB] Initialized database at '{DATABASE_PATH}'")


def hash_file(filepath: str) -> str:
    """Return the sha256 hex digest of a file's contents — the dedup key
    for imported_files. Content-based (not filename-based) so a renamed
    duplicate is still caught and a same-named-but-different file isn't."""
    import hashlib
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def get_imported_file(cur, file_hash: str):
    """Return the imported_files row for this hash, or None if never imported."""
    cur.execute("SELECT * FROM imported_files WHERE file_hash = ?", (file_hash,))
    return cur.fetchone()


def record_file_import(cur, file_hash: str, filename: str, file_type: str,
                        tournament_id: int = None) -> int:
    """Mark a file as imported so re-parsing it is a no-op. Call after the
    parse's own inserts, on the same cursor/transaction, right before commit."""
    cur.execute("""
        INSERT INTO imported_files (file_hash, filename, file_type, tournament_id)
        VALUES (?, ?, ?, ?)
    """, (file_hash, filename, file_type, tournament_id))
    return cur.lastrowid


def get_or_create_tournament(name: str, type: str, year: int,
                              host_school: str, location: str = None) -> int:
    """Return tournament id, creating it if it doesn't exist."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id FROM tournaments WHERE name = ?", (name,))
    row = cur.fetchone()
    if row:
        conn.close()
        return row["id"]
    cur.execute("""
        INSERT INTO tournaments (name, type, year, host_school, location)
        VALUES (?, ?, ?, ?, ?)
    """, (name, type, year, host_school, location))
    tournament_id = cur.lastrowid
    conn.commit()
    conn.close()
    return tournament_id


def reset_db():
    """Drop and recreate the database — useful during development."""
    if os.path.exists(DATABASE_PATH):
        os.remove(DATABASE_PATH)
        print(f"[DB] Removed existing database '{DATABASE_PATH}'")
    init_db()


if __name__ == "__main__":
    init_db()
