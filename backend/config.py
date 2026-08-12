# config.py - Configurable HCASC categories and app settings
# Edit CATEGORIES to add/remove/rename subject areas without touching other code.

CATEGORIES = [
    "Science",
    "History",
    "Literature",
    "Math",
    "Pop Culture",
    "African American History",
    "Geography",
    "Arts & Music",
    "Religion",
    "Philosophy",
    "Sports",
]

# Minimum questions attempted before a category rating is considered reliable
MIN_SAMPLE_SIZE = 3

# Score threshold below which a team is considered to have a "gap" in a category (0.0 - 1.0)
GAP_THRESHOLD = 0.40

# Points structure
FO_POINTS = 10
BONUS_POINTS = 20
UC_POINTS_PER_QUESTION = 50
UC_MAX_QUESTIONS = 10
UC_MAX_POINTS = UC_POINTS_PER_QUESTION * UC_MAX_QUESTIONS  # 500

DATABASE_PATH = "hcasc.db"
