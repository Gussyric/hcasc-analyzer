# parsers/scoresheet_parser.py
# Parses HCASC NQT scoresheet PDFs into structured data.
#
# Scoresheet layout:
#   Header: "Match # 621 / Game # 1 / Team1 vs. Team2"
#   Roster lines: "Round N  Player1  Player2"  (3 lines, one per round)
#   Three Face-Off rounds, each with a table:
#     RunningScore | PlayerName | FO | Bonus | Q# | Category | FO | Bonus | PlayerName | RunningScore
#   Ultimate Challenge section:
#     Category         Category
#     POINTS  POINTS
#     1 /2 /6 /         1 /3 /4 /
#     FINAL_SCORE  Final Score:  OTHER_SCORE

import re
import os
import pdfplumber
from database import get_connection
from utils.team_names import normalize_team_name


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_bonus(raw: str) -> int:
    """Parse bonus string like '10/5=15' or '0/0=0' -> return the sum value."""
    if not raw or raw.strip() in ("", "0"):
        return 0
    # Format A: "10/5=15" -> take the last number after "="
    m = re.search(r"=\s*(\d+)", raw)
    if m:
        return int(m.group(1))
    # Format B: plain number
    m = re.search(r"(\d+)", raw)
    if m:
        return int(m.group(1))
    return 0


def _get_or_create_team(cur, name: str, room: str = None) -> int:
    """Return team id, creating the team row if it doesn't exist."""
    name = normalize_team_name(name.strip())
    cur.execute("SELECT id FROM teams WHERE name = ?", (name,))
    row = cur.fetchone()
    if row:
        return row["id"]
    cur.execute("INSERT INTO teams (name, room) VALUES (?, ?)", (name, room))
    return cur.lastrowid


def _get_or_create_player(cur, team_id: int, name: str) -> int:
    """Return player id, creating if needed. Skips empty/placeholder names."""
    name = name.strip()
    if not name or name in ("No Answer", "0"):
        return None
    cur.execute("SELECT id FROM players WHERE team_id = ? AND name = ?", (team_id, name))
    row = cur.fetchone()
    if row:
        return row["id"]
    cur.execute("INSERT INTO players (team_id, name) VALUES (?, ?)", (team_id, name))
    return cur.lastrowid


# ---------------------------------------------------------------------------
# Main parse function
# ---------------------------------------------------------------------------

def parse_scoresheet(filepath: str) -> dict:
    """
    Parse a single scoresheet PDF.
    Returns a summary dict with game metadata and row counts.
    Inserts all data into the SQLite database.
    """
    with pdfplumber.open(filepath) as pdf:
        full_text = "\n".join(
            page.extract_text() or "" for page in pdf.pages
        )

    lines = [l.strip() for l in full_text.splitlines() if l.strip()]

    # -------------------------------------------------------------------------
    # 1. Extract header metadata
    # -------------------------------------------------------------------------
    match_number = None
    game_number = None
    team1_name = None
    team2_name = None
    room = None

    # Infer room from filename  e.g. "...Rm1_Gm3..."
    fn = os.path.basename(filepath)
    room_match = re.search(r"Rm(\d+)", fn, re.IGNORECASE)
    if room_match:
        room = room_match.group(1)

    for line in lines:
        if m := re.search(r"Match\s*#\s*(\d+)", line):
            match_number = int(m.group(1))
        if m := re.search(r"Game\s*#\s*(\d+)", line):
            game_number = int(m.group(1))
        if m := re.match(r"^(.+?)\s+vs\.\s+(.+)$", line):
            team1_name = m.group(1).strip()
            team2_name = m.group(2).strip()

    # -------------------------------------------------------------------------
    # 2. Extract per-round player rosters
    #    Lines like: "Round 1  Nti Anokye, John  Trayvick, Jeremia"
    # -------------------------------------------------------------------------
    round_rosters = {}  # round_number -> (team1_player_name, team2_player_name)
    for line in lines:
        m = re.match(r"^Round\s+(\d)\s+(.+)$", line)
        if m:
            rnd = int(m.group(1))
            rest = m.group(2).strip()
            # Split the two player names. Both are typically "Lastname, Firstname".
            # Find the second name by locating the space before the second comma-group.
            comma_positions = [i for i, c in enumerate(rest) if c == ","]
            name1, name2 = rest, ""
            if len(comma_positions) >= 2:
                for cp in comma_positions[1:]:
                    word_start = cp
                    while word_start > 0 and rest[word_start - 1] not in (" ", "\t"):
                        word_start -= 1
                    if word_start > 0:
                        name1 = rest[:word_start].strip()
                        name2 = rest[word_start:].strip()
                        break
            else:
                parts = re.split(r"\s{2,}", rest)
                if len(parts) >= 2:
                    name1, name2 = parts[0].strip(), parts[1].strip()
            round_rosters[rnd] = (name1, name2)

    # -------------------------------------------------------------------------
    # 3. Parse face-off event rows
    # -------------------------------------------------------------------------
    # Split full text into sections by round headers and UC section
    sections = _split_into_sections(lines)

    # -------------------------------------------------------------------------
    # 4. Parse Ultimate Challenge
    # -------------------------------------------------------------------------
    uc_data = _parse_uc_section(lines)

    # -------------------------------------------------------------------------
    # 5. Database writes
    # -------------------------------------------------------------------------
    conn = get_connection()
    cur = conn.cursor()

    team1_id = _get_or_create_team(cur, team1_name, room)
    team2_id = _get_or_create_team(cur, team2_name, room)

    # Final scores come from UC section or last running scores
    team1_final = uc_data.get("team1_final_score", 0)
    team2_final = uc_data.get("team2_final_score", 0)

    cur.execute("""
        INSERT INTO games
            (match_number, game_number, room, team1_id, team2_id,
             team1_score, team2_score, source_file)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (match_number, game_number, room, team1_id, team2_id,
          team1_final, team2_final, os.path.basename(filepath)))
    game_id = cur.lastrowid

    event_count = 0
    for rnd, event_rows in sections.items():
        t1_player_name, t2_player_name = round_rosters.get(rnd, ("", ""))
        t1_player_id = _get_or_create_player(cur, team1_id, t1_player_name)
        t2_player_id = _get_or_create_player(cur, team2_id, t2_player_name)

        for row in event_rows:
            # Determine which side answered the FO
            t1_fo = row.get("left_fo", 0)
            t2_fo = row.get("right_fo", 0)
            t1_bonus = row.get("left_bonus", 0)
            t2_bonus = row.get("right_bonus", 0)
            t1_correct = 1 if t1_fo > 0 else 0
            t2_correct = 1 if t2_fo > 0 else 0

            # Use the player who actually answered if named, else round default
            left_name = row.get("left_player", "")
            right_name = row.get("right_player", "")
            pid1 = _get_or_create_player(cur, team1_id, left_name) if left_name else t1_player_id
            pid2 = _get_or_create_player(cur, team2_id, right_name) if right_name else t2_player_id

            cur.execute("""
                INSERT INTO game_events
                    (game_id, round_number, question_number, category,
                     team1_player_id, team1_fo_pts, team1_bonus_pts, team1_fo_correct,
                     team2_player_id, team2_fo_pts, team2_bonus_pts, team2_fo_correct)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (game_id, rnd, row.get("q_num"), row.get("category"),
                  pid1, t1_fo, t1_bonus, t1_correct,
                  pid2, t2_fo, t2_bonus, t2_correct))
            event_count += 1

    # UC events
    for uc in uc_data.get("uc_events", []):
        team_id = team1_id if uc["side"] == "left" else team2_id
        cur.execute("""
            INSERT INTO uc_events
                (game_id, team_id, category, points_scored,
                 questions_correct, questions_attempted, correct_q_numbers)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (game_id, team_id, uc["category"], uc["points"],
              uc["questions_correct"], 10, uc["correct_q_numbers"]))

    conn.commit()
    conn.close()

    return {
        "file": os.path.basename(filepath),
        "match": match_number,
        "game": game_number,
        "room": room,
        "team1": team1_name,
        "team2": team2_name,
        "team1_score": team1_final,
        "team2_score": team2_final,
        "events_inserted": event_count,
    }


# ---------------------------------------------------------------------------
# Section splitter — separates lines into Round 1/2/3 and UC groups
# ---------------------------------------------------------------------------

def _split_into_sections(lines: list) -> dict:
    """
    Walk lines and assign each face-off data row to its round.
    Returns {1: [row_dicts], 2: [row_dicts], 3: [row_dicts]}
    """
    sections = {1: [], 2: [], 3: []}
    current_round = None
    in_table = False

    for line in lines:
        # Detect round headers
        if re.match(r"^Round\s+1\s*$", line):
            current_round = 1
            in_table = False
            continue
        if re.match(r"^Round\s+2\s*$", line):
            current_round = 2
            in_table = False
            continue
        if re.match(r"^Round\s+3\s*$", line):
            current_round = 3
            in_table = False
            continue
        if re.match(r"^Ultimate\s+Challenge", line, re.IGNORECASE):
            current_round = None
            continue
        # Skip the column header line
        if re.match(r"^Running\s+Running", line):
            in_table = False
            continue
        if re.match(r"^Score\s+Player", line):
            in_table = True
            continue

        if current_round and in_table:
            row = _parse_event_line(line)
            if row:
                sections[current_round].append(row)

    return sections


def _parse_event_line(line: str) -> dict | None:
    """
    Parse a single face-off data row using single-space token splitting.
    Layout: RunScore [LeftPlayer] LeftFO [LeftBonus] Q# CATEGORY RightFO [RightBonus] [RightPlayer] RunScore
    """
    tokens = line.split()
    if len(tokens) < 4:
        return None
    if not tokens[0].isdigit() or not tokens[-1].isdigit():
        return None

    # Find Q# index: integer whose next token starts with an uppercase letter
    q_idx = None
    for i in range(1, len(tokens) - 1):
        if tokens[i].isdigit():
            if i + 1 < len(tokens) and re.search(r'[A-Z]', tokens[i + 1]):
                q_idx = i
                break

    if q_idx is None:
        return None

    q_num = int(tokens[q_idx])

    # Category: all tokens from q_idx+1 until we hit a numeric/bonus token
    cat_end = q_idx + 1
    while cat_end < len(tokens) - 1:
        t = tokens[cat_end]
        if t.isdigit() or re.match(r'\d+/\d+=\d+', t) or re.match(r'\d+/\d+$', t):
            break
        cat_end += 1
    category = " ".join(tokens[q_idx + 1:cat_end])

    left_tokens = tokens[1:q_idx]
    right_tokens = tokens[cat_end:-1]

    left_player, left_fo, left_bonus = _parse_side(left_tokens)
    right_player, right_fo, right_bonus = _parse_side(right_tokens)

    return {
        "q_num": q_num,
        "category": category,
        "left_player": left_player,
        "left_fo": left_fo,
        "left_bonus": left_bonus,
        "right_player": right_player,
        "right_fo": right_fo,
        "right_bonus": right_bonus,
    }


def _parse_side(tokens: list) -> tuple:
    """Extract (player_name, fo_points, bonus_points) from one side's tokens."""
    player_parts = []
    fo = 0
    bonus = 0
    for tok in tokens:
        if re.match(r'\d+/\d+=\d+', tok) or re.match(r'\d+/\d+$', tok):
            m = re.search(r'=(\d+)', tok)
            bonus = int(m.group(1)) if m else 0
        elif tok == "0":
            continue
        elif tok.lstrip('-').isdigit():
            fo = int(tok)
        else:
            player_parts.append(tok)
    player = " ".join(player_parts).strip()
    if player in ("No Answer", "No"):
        player = ""
    return player, fo, bonus



# ---------------------------------------------------------------------------
# Ultimate Challenge parser
# ---------------------------------------------------------------------------

def _parse_uc_section(lines: list) -> dict:
    """
    Parse the Ultimate Challenge block.
    Line format: 'CAT1 score1 score2 CAT2'
    Then: '1 /2 /6 / 1 /3 /5 /'
    Then: 'SCORE_LEFT  Final Score:  SCORE_RIGHT'
    """
    uc_start = None
    for i, line in enumerate(lines):
        if re.match(r"^Ultimate\s+Challenge", line, re.IGNORECASE):
            uc_start = i
            break

    if uc_start is None:
        return {"uc_events": [], "team1_final_score": 0, "team2_final_score": 0}

    uc_lines = lines[uc_start + 1:]  # skip "Ultimate Challenge" header

    cat1, cat2 = "", ""
    score1, score2 = 0, 0
    q_numbers = []
    final_scores = []

    for line in uc_lines:
        # Skip "Category Category" header
        if re.match(r"^Category\s+Category", line, re.IGNORECASE):
            continue

        # Final score line
        if "Final Score:" in line:
            nums = re.findall(r"\d+", line)
            if len(nums) >= 2:
                final_scores = [int(nums[0]), int(nums[1])]
            continue

        # Question numbers line: contains slashes
        if "/" in line:
            # Split the line roughly in half to get left/right sides
            # Find the midpoint by looking for a gap after the first run of q-nums
            halves = re.split(r"\s{2,}", line)
            if len(halves) >= 2:
                q_numbers = [halves[0].strip(), halves[1].strip()]
            else:
                # Try to split by finding two runs of "N /" patterns
                left_q = re.findall(r"(\d+\s*/)", line)
                mid = len(left_q) // 2
                q_numbers = [
                    " ".join(left_q[:mid]),
                    " ".join(left_q[mid:]),
                ]
            continue

        # Category + scores line: "CAT1 score1 score2 CAT2"
        if not cat1 and re.search(r"[A-Z]", line):
            matches = list(re.finditer(r"\b(\d+)\b", line))
            if len(matches) >= 2:
                for i in range(len(matches) - 1):
                    m1, m2 = matches[i], matches[i + 1]
                    between = line[m1.end():m2.start()].strip()
                    if between == "":
                        cat1 = line[:m1.start()].strip()
                        score1 = int(m1.group(1))
                        score2 = int(m2.group(1))
                        cat2 = line[m2.end():].strip()
                        break

    # Build uc_events
    def q_list(q_str):
        return [x.strip() for x in re.split(r"[/\s]+", q_str) if x.strip().isdigit()]

    uc_events = [
        {
            "side": "left",
            "category": cat1,
            "points": score1,
            "questions_correct": len(q_list(q_numbers[0] if q_numbers else "")),
            "correct_q_numbers": ",".join(q_list(q_numbers[0] if q_numbers else "")),
        },
        {
            "side": "right",
            "category": cat2,
            "points": score2,
            "questions_correct": len(q_list(q_numbers[1] if len(q_numbers) > 1 else "")),
            "correct_q_numbers": ",".join(q_list(q_numbers[1] if len(q_numbers) > 1 else "")),
        },
    ]

    return {
        "uc_events": uc_events,
        "team1_final_score": final_scores[0] if len(final_scores) >= 1 else 0,
        "team2_final_score": final_scores[1] if len(final_scores) >= 2 else 0,
    }




# ---------------------------------------------------------------------------
# Batch import
# ---------------------------------------------------------------------------

def parse_all_scoresheets(directory: str) -> list:
    """Parse every PDF in the given directory and return a list of result dicts."""
    results = []
    for fname in sorted(os.listdir(directory)):
        if not fname.lower().endswith(".pdf"):
            continue
        path = os.path.join(directory, fname)
        try:
            result = parse_scoresheet(path)
            results.append(result)
            print(f"[OK] {fname} -> {result['team1']} {result['team1_score']} - "
                  f"{result['team2']} {result['team2_score']}")
        except Exception as e:
            print(f"[ERR] {fname}: {e}")
            results.append({"file": fname, "error": str(e)})
    return results
