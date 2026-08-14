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
from database import get_connection, hash_file, get_imported_file, record_file_import
from utils.team_names import normalize_team_name
from config import UC_MAX_POINTS, UC_POINTS_PER_QUESTION, FO_POINTS


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
    cur.execute("INSERT INTO teams (name) VALUES (?)", (name,))
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


def _resolve_round_roster(rest: str, row_left_names: list, row_right_names: list) -> tuple:
    """
    Split a round-header line like "Guscott, Omario Parejo Cano, Santiago"
    into (name1, name2) for the two players declared for that round.

    The line is always two "Last, First" groups concatenated with a space,
    but when a surname is itself multi-word ("Parejo Cano", "Nti Anokye")
    the boundary between the groups is ambiguous from the roster line
    alone — naively walking back one word from the final comma silently
    misattributes the extra surname word to the wrong player.

    Per-row names (even when truncated by a narrow table column) reliably
    show which words belong to which side, so they're used to pick the
    correct split point among candidates (1-word, 2-word, ... walk-back);
    the roster line then supplies the complete, untruncated name for
    whichever split satisfies both sides' row evidence. Falls back to the
    simplest one-word-surname split when no row evidence is available
    (e.g. a player who never attempted a face-off that round).
    """
    comma_positions = [i for i, c in enumerate(rest) if c == ","]
    if len(comma_positions) < 2:
        parts = re.split(r"\s{2,}", rest)
        if len(parts) >= 2:
            return parts[0].strip(), parts[1].strip()
        return rest, ""

    left_hint = max((n for n in row_left_names if n), key=len, default="")
    right_hint = max((n for n in row_right_names if n), key=len, default="")

    def matches(candidate: str, hint: str) -> bool:
        if not hint:
            return True  # no row evidence for this side — don't block on it
        return candidate.startswith(hint) or hint.startswith(candidate)

    last_comma = comma_positions[-1]
    first_comma = comma_positions[0]
    candidates = []
    pos = last_comma
    while True:
        word_start = pos
        while word_start > 0 and rest[word_start - 1] not in (" ", "\t"):
            word_start -= 1
        if word_start <= first_comma:
            break
        candidates.append(word_start)
        pos = word_start - 1
        if len(candidates) >= 4:  # sane upper bound on compound-surname length
            break

    for word_start in candidates:
        name1 = rest[:word_start].strip()
        name2 = rest[word_start:].strip()
        if matches(name1, left_hint) and matches(name2, right_hint):
            return name1, name2

    # No candidate satisfied both hints — fall back to the simplest split.
    word_start = candidates[0] if candidates else last_comma
    return rest[:word_start].strip(), rest[word_start:].strip()


# ---------------------------------------------------------------------------
# Main parse function
# ---------------------------------------------------------------------------

def parse_scoresheet(filepath: str, tournament_id: int = None, force: bool = False) -> dict:
    """
    Parse a single scoresheet PDF.
    Returns a summary dict with game metadata and row counts.
    Inserts all data into the SQLite database.

    Skips (no-op) if this exact file's contents were already imported,
    unless force=True.
    """
    file_hash = hash_file(filepath)
    conn = get_connection()
    cur = conn.cursor()

    if not force:
        existing = get_imported_file(cur, file_hash)
        if existing:
            conn.close()
            return {
                "file": os.path.basename(filepath),
                "skipped": True,
                "reason": f"already imported at {existing['imported_at']}",
            }

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
    # 2. Parse face-off event rows (needed first — see step 3 below)
    # -------------------------------------------------------------------------
    # Split full text into sections by round headers and UC section
    sections = _split_into_sections(lines)

    # -------------------------------------------------------------------------
    # 3. Extract per-round player rosters
    #    Lines like: "Round 1  Nti Anokye, John  Trayvick, Jeremia"
    # -------------------------------------------------------------------------
    round_rosters = {}  # round_number -> (team1_player_name, team2_player_name)
    for line in lines:
        m = re.match(r"^Round\s+(\d)\s+(.+)$", line)
        if m:
            rnd = int(m.group(1))
            rest = m.group(2).strip()
            rows = sections.get(rnd, [])
            left_hints = [row.get("left_player", "") for row in rows]
            right_hints = [row.get("right_player", "") for row in rows]
            round_rosters[rnd] = _resolve_round_roster(rest, left_hints, right_hints)

    # -------------------------------------------------------------------------
    # 4. Parse Ultimate Challenge
    # -------------------------------------------------------------------------
    uc_data = _parse_uc_section(lines)

    # -------------------------------------------------------------------------
    # 5. Database writes  (conn/cur opened above for the dedup check)
    # -------------------------------------------------------------------------
    team1_id = _get_or_create_team(cur, team1_name, room)
    team2_id = _get_or_create_team(cur, team2_name, room)

    # Final scores come from UC section or last running scores
    team1_final = uc_data.get("team1_final_score", 0)
    team2_final = uc_data.get("team2_final_score", 0)

    cur.execute("""
        INSERT INTO games
            (tournament_id, match_number, game_number, room, team1_id, team2_id,
             team1_score, team2_score, source_file)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (tournament_id, match_number, game_number, room, team1_id, team2_id,
          team1_final, team2_final, os.path.basename(filepath)))
    game_id = cur.lastrowid

    event_count = 0
    for rnd, event_rows in sections.items():
        # A round has exactly one player per side; round_rosters already
        # resolved the correct, complete name for each using row evidence
        # (see _resolve_round_roster), so every row in the round shares it —
        # a row's own name field is often just a truncated/garbled render of
        # the same person (narrow table column, or a stray bonus token).
        t1_name, t2_name = round_rosters.get(rnd, ("", ""))

        t1_player_id = _get_or_create_player(cur, team1_id, t1_name)
        t2_player_id = _get_or_create_player(cur, team2_id, t2_name)

        for row in event_rows:
            # Determine which side answered the FO
            t1_fo = row.get("left_fo", 0)
            t2_fo = row.get("right_fo", 0)
            t1_bonus = row.get("left_bonus", 0)
            t2_bonus = row.get("right_bonus", 0)
            t1_correct = 1 if t1_fo > 0 else 0
            t2_correct = 1 if t2_fo > 0 else 0

            pid1 = t1_player_id
            pid2 = t2_player_id

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

    record_file_import(cur, file_hash, os.path.basename(filepath), "scoresheet", tournament_id)

    conn.commit()
    conn.close()

    return {
        "file": os.path.basename(filepath),
        "skipped": False,
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


_YEAR_RE = re.compile(r'^(19|20)\d{2}$')


def _parse_event_line(line: str) -> dict | None:
    """
    Parse a single face-off data row using single-space token splitting.
    Layout: RunScore [LeftPlayer] LeftFO [LeftBonus] Q# CATEGORY RightFO [RightBonus] [RightPlayer] RunScore

    A category can itself contain a bare year, leading ("2025 EMMY AWARDS")
    or trailing ("DATELINE: 1926") — normally any all-digit token ends the
    category / marks where the Q# is, so a category-embedded year is
    allowed exactly once as an exception to that rule.
    """
    tokens = line.split()
    if len(tokens) < 4:
        return None
    if not tokens[0].isdigit() or not tokens[-1].isdigit():
        return None

    # Find Q# index: integer whose next token starts with an uppercase
    # letter, OR whose next token is a year immediately followed by an
    # uppercase-starting token (a leading-year category).
    q_idx = None
    for i in range(1, len(tokens) - 1):
        if tokens[i].isdigit():
            nxt = tokens[i + 1]
            nxt2 = tokens[i + 2] if i + 2 < len(tokens) else ""
            if re.search(r'[A-Z]', nxt) or (_YEAR_RE.match(nxt) and re.search(r'[A-Z]', nxt2)):
                q_idx = i
                break

    if q_idx is None:
        return None

    q_num = int(tokens[q_idx])

    # Category: all tokens from q_idx+1 until we hit a numeric/bonus token,
    # allowing exactly one embedded year to pass through un-ended.
    cat_end = q_idx + 1
    year_consumed = False
    while cat_end < len(tokens) - 1:
        t = tokens[cat_end]
        if not year_consumed and _YEAR_RE.match(t):
            year_consumed = True
            cat_end += 1
            continue
        if t.isdigit() or re.match(r'\d+(?:/\d+)+=\d+', t) or re.match(r'\d+(?:/\d+)+$', t):
            break
        cat_end += 1
    category = " ".join(tokens[q_idx + 1:cat_end])

    left_tokens = tokens[1:q_idx]
    right_tokens = tokens[cat_end:-1]

    left_player, left_fo, left_bonus = _parse_side(left_tokens)
    right_player, right_fo, right_bonus = _parse_side(right_tokens)

    # FO points are a fixed game constant (0 or FO_POINTS) — anything else
    # means the row's tokens got misaligned (e.g. a bare-numeric category
    # like "1998" with no letter to anchor on) and the row is unreliable.
    if left_fo not in (0, FO_POINTS) or right_fo not in (0, FO_POINTS):
        return None

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
    """
    Extract (player_name, fo_points, bonus_points) from one side's tokens.

    Bonus is usually a fraction-format token ("10/0=10"), but sometimes
    shows up as a second bare number instead (e.g. "10 20" or "10 5") —
    the first bare digit token is always FO points, and a second one (if
    any) is the bonus, rather than the second silently overwriting the
    first.
    """
    player_parts = []
    fo = 0
    bonus = 0
    seen_plain_digit = False
    for tok in tokens:
        if re.match(r'\d+(?:/\d+)+=\d+', tok) or re.match(r'\d+(?:/\d+)+$', tok):
            m = re.search(r'=(\d+)', tok)
            bonus = int(m.group(1)) if m else 0
        elif tok == "0":
            continue
        elif tok.lstrip('-').isdigit():
            if not seen_plain_digit:
                fo = int(tok)
                seen_plain_digit = True
            else:
                bonus = int(tok)
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

    The "1 /2 /6 / 1 /3 /5 /" line has no reliable whitespace boundary
    between the two sides' number lists in the extracted text (pdfplumber
    collapses the gap to the same single space used between numbers within
    a side), and can even drop digits entirely. So it's used only to
    populate the display string of which questions were answered
    correctly, on a best-effort basis — the authoritative correct-answer
    COUNT is derived from points_scored, since UC is flat
    UC_POINTS_PER_QUESTION points per correct answer.
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
            q_numbers = re.findall(r"(\d+)\s*/", line)
            continue

        # Category + scores line: "CAT1 score1 score2 CAT2". A category
        # name can itself contain a number (e.g. "WORLD CUP 2026"), so the
        # first adjacent-number pair isn't necessarily the real scores —
        # only a pair that are both valid UC point totals is trusted.
        if not cat1 and re.search(r"[A-Z]", line):
            matches = list(re.finditer(r"\b(\d+)\b", line))
            for i in range(len(matches) - 1):
                m1, m2 = matches[i], matches[i + 1]
                between = line[m1.end():m2.start()].strip()
                v1, v2 = int(m1.group(1)), int(m2.group(1))
                valid = (0 <= v1 <= UC_MAX_POINTS and v1 % UC_POINTS_PER_QUESTION == 0
                         and 0 <= v2 <= UC_MAX_POINTS and v2 % UC_POINTS_PER_QUESTION == 0)
                if between == "" and valid:
                    cat1 = line[:m1.start()].strip()
                    score1, score2 = v1, v2
                    cat2 = line[m2.end():].strip()
                    break

    # Correct-answer counts come from points, not the fragile q-numbers
    # line (see docstring) — points are cleanly parsed and always a
    # multiple of UC_POINTS_PER_QUESTION.
    count1 = score1 // UC_POINTS_PER_QUESTION
    count2 = score2 // UC_POINTS_PER_QUESTION

    # Best-effort split of the raw question-number list using those counts.
    left_q_numbers = q_numbers[:count1]
    right_q_numbers = q_numbers[count1:count1 + count2]

    uc_events = [
        {
            "side": "left",
            "category": cat1,
            "points": score1,
            "questions_correct": count1,
            "correct_q_numbers": ",".join(left_q_numbers),
        },
        {
            "side": "right",
            "category": cat2,
            "points": score2,
            "questions_correct": count2,
            "correct_q_numbers": ",".join(right_q_numbers),
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

def parse_all_scoresheets(directory: str, tournament_id: int = None) -> list:
    """Parse every PDF in the given directory and return a list of result dicts."""
    results = []
    for fname in sorted(os.listdir(directory)):
        if not fname.lower().endswith(".pdf"):
            continue
        path = os.path.join(directory, fname)
        try:
            result = parse_scoresheet(path, tournament_id=tournament_id)
            results.append(result)
            if result.get("skipped"):
                print(f"[SKIP] {fname} -> {result['reason']}")
            else:
                print(f"[OK] {fname} -> {result['team1']} {result['team1_score']} - "
                      f"{result['team2']} {result['team2_score']}")
        except Exception as e:
            print(f"[ERR] {fname}: {e}")
            results.append({"file": fname, "error": str(e)})
    return results
