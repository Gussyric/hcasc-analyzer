# utils/team_names.py
# Normalizes HCASC team name variants to canonical short names.
# Scoresheets use short names; summary PDFs use full university names.
# This mapping ensures both map to the same DB record.

CANONICAL_NAMES = {
    # Alabama State
    "alabama state univ.": "Alabama State",
    "alabama state university": "Alabama State",
    "alabama state": "Alabama State",
    # Alabama State B
    "alabama state univ. - b": "Alabama State-B",
    "alabama state univ.-b": "Alabama State-B",
    "alabama state university - b": "Alabama State-B",
    "alabama state-b": "Alabama State-B",
    "alabama state univ b": "Alabama State-B",
    # Grambling
    "grambling state univ.": "Grambling",
    "grambling state university": "Grambling",
    "grambling": "Grambling",
    # Harris-Stowe
    "harris-stowe state univ.": "Harris-Stowe",
    "harris-stowe state university": "Harris-Stowe",
    "harris-stowe": "Harris-Stowe",
    # Oakwood
    "oakwood univ.": "Oakwood",
    "oakwood university": "Oakwood",
    "oakwood": "Oakwood",
    # Paine
    "paine college": "Paine",
    "paine": "Paine",
    # Stillman
    "stillman college": "Stillman",
    "stillman": "Stillman",
    # Tennessee State
    "tennessee state univ.": "Tennessee State",
    "tennessee state university": "Tennessee State",
    "tennessee state": "Tennessee State",
    # Tennessee State B
    "tennessee state univ. - b": "Tennessee State-B",
    "tennessee state univ.-b": "Tennessee State-B",
    "tennessee state university - b": "Tennessee State-B",
    "tennessee state-b": "Tennessee State-B",
    "tennessee state univ b": "Tennessee State-B",
    # Tuskegee
    "tuskegee univ.": "Tuskegee",
    "tuskegee university": "Tuskegee",
    "tuskegee": "Tuskegee",
}


def normalize_team_name(name: str) -> str:
    """Return the canonical team name, or the original if no mapping found."""
    return CANONICAL_NAMES.get(name.strip().lower(), name.strip())
