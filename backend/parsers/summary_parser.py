# parsers/summary_parser.py
# Parses the four HCASC NQT summary PDFs:
#   - ASUPlayerStats.pdf
#   - ASUResultsByTeam.pdf
#   - ASURoundRobinResults.pdf
#   - ASUPlayoffResults.pdf

import re
import pdfplumber
from database import get_connection
from utils.team_names import normalize_team_name


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_or_create_team(cur, name: str, room: str = None) -> int:
    name = normalize_team_name(name.strip())
    cur.execute("SELECT id FROM teams WHERE name = ?", (name,))
    row = cur.fetchone()
    if row:
        return row["id"]
    cur.execute("INSERT INTO teams (name, room) VALUES (?, ?)", (name, room))
    return cur.lastrowid


def _get_or_create_player(cur, team_id: int, name: str) -> int | None:
    name = name.strip()
    if not name:
        return None
    cur.execute("SELECT id FROM players WHERE team_id = ? AND name = ?", (team_id, name))
    row = cur.fetchone()
    if row:
        return row["id"]
    cur.execute("INSERT INTO players (team_id, name) VALUES (?, ?)", (team_id, name))
    return cur.lastrowid


def _extract_text(filepath: str) -> str:
    with pdfplumber.open(filepath) as pdf:
        return "\n".join(page.extract_text() or "" for page in pdf.pages)


# ---------------------------------------------------------------------------
# 1. ASUPlayerStats.pdf
# ---------------------------------------------------------------------------
# Layout per player block:
#   <TeamName>              (section header, may repeat across pages)
#   <PlayerName, LastFirst>
#   "Match  Questions  Buzzed  Answered"
#   "Number  Category  Heard  In  Correctly"
#   <Rm X - Gm Y>  <CATEGORY>  <heard>  <buzzed>  <correct>  <pct%>
#   ...
#   "Totals  <heard>  <buzzed>  <correct>  <pct%>"

def parse_player_stats(filepath: str) -> int:
    """Parse ASUPlayerStats.pdf. Returns number of stat rows inserted."""
    text = _extract_text(filepath)
    lines = [l.strip() for l in text.splitlines() if l.strip()]

    conn = get_connection()
    cur = conn.cursor()

    current_team_id = None
    current_player_id = None
    rows_inserted = 0

    # Known team names (will also match dynamically)
    HEADER_SKIP = {"Player Statistics", "Match Questions Buzzed Answered",
                   "Number Category Heard In Correctly",
                   "HCASC NQT", "Alabama State Univ."}

    i = 0
    while i < len(lines):
        line = lines[i]

        # Skip known headers
        if line in HEADER_SKIP:
            i += 1
            continue

        # Match line — "Rm X - Gm Y  CATEGORY  N  N  N  N%"
        m = re.match(
            r"^(Rm\s+\d+\s+-\s+Gm\s+\d+)\s+(.+?)\s+(\d+)\s+(\d+)\s+(\d+)\s+([\d.]+)%$",
            line
        )
        if m and current_player_id:
            match_label = m.group(1).strip()
            category = m.group(2).strip()
            heard = int(m.group(3))
            buzzed = int(m.group(4))
            correct = int(m.group(5))
            accuracy = float(m.group(6))

            # Deduplicate: skip if already exists
            cur.execute("""
                SELECT id FROM player_stats
                WHERE player_id=? AND match_label=? AND category=?
            """, (current_player_id, match_label, category))
            if not cur.fetchone():
                cur.execute("""
                    INSERT INTO player_stats
                        (player_id, match_label, category,
                         questions_heard, buzzed_in, answered_correctly, accuracy_pct)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (current_player_id, match_label, category,
                      heard, buzzed, correct, accuracy))
                rows_inserted += 1
            i += 1
            continue

        # Totals line — skip
        if line.startswith("Totals"):
            i += 1
            continue

        # Player name: "LastName, FirstName" pattern  (comma present, no digits)
        if "," in line and not re.search(r"\d", line) and current_team_id:
            current_player_id = _get_or_create_player(cur, current_team_id, line)
            i += 1
            continue

        # Team name block — lines that are plain team names (no comma, no digits, not a header)
        # Strategy: if it doesn't match anything above and looks like a team name, treat as team
        if (not re.search(r"\d", line)
                and line not in HEADER_SKIP
                and not line.startswith("Rm ")
                and len(line) > 3):
            # Could be team section header
            # Try to find this name as an existing team first
            cur.execute("SELECT id FROM teams WHERE name = ?", (line,))
            row = cur.fetchone()
            if row:
                current_team_id = row["id"]
                current_player_id = None
            else:
                # New team from this summary doc
                current_team_id = _get_or_create_team(cur, line)
                current_player_id = None

        i += 1

    conn.commit()
    conn.close()
    return rows_inserted


# ---------------------------------------------------------------------------
# 2. ASUResultsByTeam.pdf
# ---------------------------------------------------------------------------
# Layout:
#   "Room # 1"
#   <TeamName>
#   <Points>  vs. <OpponentName>  <OppPoints>  <W>  <L>
#   ...

def parse_results_by_team(filepath: str) -> int:
    text = _extract_text(filepath)
    lines = [l.strip() for l in text.splitlines() if l.strip()]

    conn = get_connection()
    cur = conn.cursor()

    current_room = None
    current_team_id = None
    rows_inserted = 0

    SKIP = {"Results By Team", "Points For Opp Points W L",
            "HCASC National Qualifying Tournament", "Alabama State Univ."}

    for line in lines:
        if line in SKIP:
            continue

        # Room header
        m = re.match(r"^Room\s*#\s*(\d+)", line)
        if m:
            current_room = m.group(1)
            continue

        # Game result line: "320 vs. Grambling State Univ. 300 1 0"
        m = re.match(r"^(\d+)\s+vs\.\s+(.+?)\s+(\d+)\s+(\d)\s+(\d)$", line)
        if m and current_team_id:
            pts_for = int(m.group(1))
            opp_name = m.group(2).strip()
            pts_against = int(m.group(3))
            win = int(m.group(4))

            opp_id = _get_or_create_team(cur, opp_name, current_room)

            cur.execute("""
                INSERT INTO team_game_results
                    (team_id, opponent_id, points_for, points_against, win, room)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (current_team_id, opp_id, pts_for, pts_against, win, current_room))
            rows_inserted += 1
            continue

        # Team name header (no digits, not a skip line)
        if not re.search(r"\d", line) and line not in SKIP and len(line) > 2:
            current_team_id = _get_or_create_team(cur, line, current_room)

    conn.commit()
    conn.close()
    return rows_inserted


# ---------------------------------------------------------------------------
# 3. ASURoundRobinResults.pdf
# ---------------------------------------------------------------------------
# Layout:
#   "Room # 1"
#   "Team  Wins  Losses  TotalPoints  TotalOppPts"
#   <TeamName>  <W>  <L>  <TotalPts>  <TotalOppPts>

def parse_round_robin(filepath: str) -> int:
    text = _extract_text(filepath)
    lines = [l.strip() for l in text.splitlines() if l.strip()]

    conn = get_connection()
    cur = conn.cursor()

    current_room = None
    rows_inserted = 0

    SKIP = {"Round Robin Results", "Team Wins Losses TotalPoints TotalOppPts",
            "HCASC National Qualifying Tournament", "Alabama State Univ."}

    for line in lines:
        if line in SKIP:
            continue

        m = re.match(r"^Room\s*#\s*(\d+)", line)
        if m:
            current_room = m.group(1)
            continue

        # Standing line: "Stillman 4 0 1845 1010"
        m = re.match(r"^(.+?)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)$", line)
        if m:
            team_name = m.group(1).strip()
            wins = int(m.group(2))
            losses = int(m.group(3))
            total_pts = int(m.group(4))
            total_opp = int(m.group(5))

            team_id = _get_or_create_team(cur, team_name, current_room)

            # Deduplicate
            cur.execute("""
                SELECT id FROM standings WHERE team_id=? AND room=?
            """, (team_id, current_room))
            if not cur.fetchone():
                cur.execute("""
                    INSERT INTO standings
                        (team_id, room, wins, losses, total_points, total_opp_pts)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (team_id, current_room, wins, losses, total_pts, total_opp))
                rows_inserted += 1

    conn.commit()
    conn.close()
    return rows_inserted


# ---------------------------------------------------------------------------
# 4. ASUPlayoffResults.pdf
# ---------------------------------------------------------------------------
# Layout:
#   "11 11 Stillman 350 Alabama State Univ. 385"
#   "12 12 Tuskegee 650 Paine College 10"
#   "13 13 Alabama State 300 Tuskegee Univ. 470"

def parse_playoff_results(filepath: str) -> int:
    text = _extract_text(filepath)
    lines = [l.strip() for l in text.splitlines() if l.strip()]

    conn = get_connection()
    cur = conn.cursor()
    rows_inserted = 0

    SKIP = {"Playoff Results", "HCASC National Qualifying Tournament",
            "Alabama State Univ.", "TimePer Game #"}

    for line in lines:
        if line in SKIP or not line:
            continue

        # "11 11 Stillman 350 Alabama State Univ. 385"
        # Format: <num> <num> <Team1 words> <score1> <Team2 words> <score2>
        m = re.match(
            r"^\d+\s+(\d+)\s+(.+?)\s+(\d+)\s+(.+?)\s+(\d+)$", line
        )
        if m:
            game_num = int(m.group(1))
            t1_name = m.group(2).strip()
            t1_score = int(m.group(3))
            t2_name = m.group(4).strip()
            t2_score = int(m.group(5))

            t1_id = _get_or_create_team(cur, t1_name)
            t2_id = _get_or_create_team(cur, t2_name)

            cur.execute("""
                INSERT INTO playoff_results
                    (game_number, team1_id, team1_score, team2_id, team2_score)
                VALUES (?, ?, ?, ?, ?)
            """, (game_num, t1_id, t1_score, t2_id, t2_score))
            rows_inserted += 1

    conn.commit()
    conn.close()
    return rows_inserted


# ---------------------------------------------------------------------------
# Convenience: parse all four summary PDFs at once
# ---------------------------------------------------------------------------

def parse_all_summaries(results_dir: str) -> dict:
    import os
    files = {
        "player_stats": "ASUPlayerStats.pdf",
        "results_by_team": "ASUResultsByTeam.pdf",
        "round_robin": "ASURoundRobinResults.pdf",
        "playoff": "ASUPlayoffResults.pdf",
    }
    counts = {}
    for key, fname in files.items():
        path = os.path.join(results_dir, fname)
        if not os.path.exists(path):
            print(f"[SKIP] {fname} not found")
            continue
        try:
            if key == "player_stats":
                n = parse_player_stats(path)
            elif key == "results_by_team":
                n = parse_results_by_team(path)
            elif key == "round_robin":
                n = parse_round_robin(path)
            elif key == "playoff":
                n = parse_playoff_results(path)
            counts[key] = n
            print(f"[OK] {fname} -> {n} rows inserted")
        except Exception as e:
            print(f"[ERR] {fname}: {e}")
            counts[key] = f"error: {e}"
    return counts
