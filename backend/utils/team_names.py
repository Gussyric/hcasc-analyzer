# utils/team_names.py
# Normalizes HCASC team name variants to canonical short names.
# Covers all 5 NQT 2026 sites: ASU, WSSU, VSU, UDC, PVAM

CANONICAL_NAMES = {
    # Alabama State
    "alabama state univ.":              "Alabama State",
    "alabama state university":         "Alabama State",
    "alabama state":                    "Alabama State",
    # Alabama State B
    "alabama state univ. - b":          "Alabama State-B",
    "alabama state univ.-b":            "Alabama State-B",
    "alabama state university - b":     "Alabama State-B",
    "alabama state-b":                  "Alabama State-B",
    # Allen
    "allen univ.":                      "Allen",
    "allen university":                 "Allen",
    "allen":                            "Allen",
    # Benedict
    "benedict college":                 "Benedict",
    "benedict":                         "Benedict",
    # Bowie State
    "bowie state univ.":                "Bowie State",
    "bowie state university":           "Bowie State",
    "bowie state":                      "Bowie State",
    "bowie":                            "Bowie State",
    # Bowie State B
    "bowie state univ. - b":            "Bowie State-B",
    "bowie state univ.-b":              "Bowie State-B",
    # Central State
    "central state univ.":              "Central State",
    "central state university":         "Central State",
    "central state":                    "Central State",
    # Cheyney
    "cheyney univ.-pennsylvania":       "Cheyney",
    "cheyney university":               "Cheyney",
    "cheyney":                          "Cheyney",
    # Chicago State
    "chicago state univ.":              "Chicago State",
    "chicago state university":         "Chicago State",
    "chicago state":                    "Chicago State",
    # District of Columbia
    "univ.-district of columbia":       "District of Columbia",
    "university of the district of columbia": "District of Columbia",
    "district of columbia":             "District of Columbia",
    # Edward Waters
    "edward waters univ.":              "Edward Waters",
    "edward waters university":         "Edward Waters",
    "edward waters":                    "Edward Waters",
    # Elizabeth City State
    "elizabeth city state univ.":       "Elizabeth City",
    "elizabeth city state university":  "Elizabeth City",
    "elizabeth city":                   "Elizabeth City",
    # Fisk
    "fisk univ.":                       "Fisk",
    "fisk university":                  "Fisk",
    "fisk":                             "Fisk",
    # Florida A&M
    "florida a&m univ.":                "Florida A&M",
    "florida a&m university":           "Florida A&M",
    "florida a & m":                    "Florida A&M",
    "florida a&m":                      "Florida A&M",
    # Grambling
    "grambling state univ.":            "Grambling",
    "grambling state university":       "Grambling",
    "grambling":                        "Grambling",
    # Hampton
    "hampton univ.":                    "Hampton",
    "hampton university":               "Hampton",
    "hampton":                          "Hampton",
    # Harris-Stowe
    "harris-stowe state univ.":         "Harris-Stowe",
    "harris-stowe state university":    "Harris-Stowe",
    "harris-stowe":                     "Harris-Stowe",
    # Howard
    "howard univ.":                     "Howard",
    "howard university":                "Howard",
    "howard":                           "Howard",
    # Kentucky State
    "kentucky state univ.":             "Kentucky State",
    "kentucky state university":        "Kentucky State",
    "kentucky state":                   "Kentucky State",
    # Langston
    "langston univ.":                   "Langston",
    "langston university":              "Langston",
    "langston":                         "Langston",
    # Lincoln University (Pennsylvania)
    "lincoln univ.-pennsylvania":       "Lincoln-Pennsylvania",
    "lincoln university-pennsylvania":  "Lincoln-Pennsylvania",
    "lincoln-pennsylvania":             "Lincoln-Pennsylvania",
    # Livingstone
    "livingstone college":              "Livingstone",
    "livingstone":                      "Livingstone",
    # Maryland Eastern Shore
    "univ. of maryland eastern shore":  "Maryland Eastern Shore",
    "univ. of maryland eastern shor":   "Maryland Eastern Shore",
    "maryland east. shore":             "Maryland Eastern Shore",
    "maryland eastern shore":           "Maryland Eastern Shore",
    # Maryland Eastern Shore B
    "univ. of maryland eastern shore-b":   "Maryland Eastern Shore-B",
    "univ. of maryland eastern shore - b": "Maryland Eastern Shore-B",
    "maryland east. shore-b":              "Maryland Eastern Shore-B",
    "maryland eastern shore-b":            "Maryland Eastern Shore-B",
    # Mississippi Valley State
    "mississippi valley state univ.":   "Mississippi Valley",
    "mississippi valley state":         "Mississippi Valley",
    "mississippi valley":               "Mississippi Valley",
    # Morehouse
    "morehouse college":                "Morehouse",
    "morehouse":                        "Morehouse",
    # Morgan State
    "morgan state univ.":               "Morgan State",
    "morgan state university":          "Morgan State",
    "morgan state":                     "Morgan State",
    # NC Central / North Carolina Central
    "north carolina central univ.":     "NC Central",
    "north carolina central university":"NC Central",
    "north carolina central":           "NC Central",
    "nc central":                       "NC Central",
    # NC Central B
    "north carolina central univ. - b": "NC Central-B",
    "north carolina central univ.-b":   "NC Central-B",
    "nc central-b":                     "NC Central-B",
    # NC A&T / North Carolina A&T
    "north carolina a&t state univ.":   "NC A&T",
    "north carolina a&t state u":       "NC A&T",
    "north carolina a&t state univ. -": "NC A&T",
    "north carolina a&t state univ.-":  "NC A&T",
    "north carolina a & t":             "NC A&T",
    "north carolina a&t":               "NC A&T",
    "nc a&t":                           "NC A&T",
    # NC A&T B
    "north carolina a&t state univ. - b": "NC A&T-B",
    "north carolina a&t state univ.-b":   "NC A&T-B",
    "north carolina a & t-b":             "NC A&T-B",
    "nc a&t-b":                           "NC A&T-B",
    # Norfolk State
    "norfolk state univ.":              "Norfolk State",
    "norfolk state university":         "Norfolk State",
    "norfolk state":                    "Norfolk State",
    # Oakwood
    "oakwood univ.":                    "Oakwood",
    "oakwood university":               "Oakwood",
    "oakwood":                          "Oakwood",
    # Paine
    "paine college":                    "Paine",
    "paine":                            "Paine",
    # Paul Quinn
    "paul quinn college":               "Paul Quinn",
    "paul quinn":                       "Paul Quinn",
    # Prairie View A&M
    "prairie view a&m univ.":           "Prairie View",
    "prairie view a&m university":      "Prairie View",
    "prairie view":                     "Prairie View",
    # Prairie View B
    "prairie view a&m univ. - b":       "Prairie View-B",
    "prairie view - b":                 "Prairie View-B",
    "prairie view-b":                   "Prairie View-B",
    # Shaw
    "shaw univ.":                       "Shaw",
    "shaw university":                  "Shaw",
    "shaw":                             "Shaw",
    # Southern University Baton Rouge
    "southern univ.-baton rouge":       "Southern",
    "southern university-baton rouge":  "Southern",
    "southern-baton rouge":             "Southern",
    "southern":                         "Southern",
    # Southern B
    "southern univ.-baton rouge - b":   "Southern-B",
    "southern univ.-baton rouge-b":     "Southern-B",
    "southern-b":                       "Southern-B",
    # Stillman
    "stillman college":                 "Stillman",
    "stillman":                         "Stillman",
    # Tennessee State
    "tennessee state univ.":            "Tennessee State",
    "tennessee state university":       "Tennessee State",
    "tennessee state":                  "Tennessee State",
    # Tennessee State B
    "tennessee state univ. - b":        "Tennessee State-B",
    "tennessee state univ.-b":          "Tennessee State-B",
    "tennessee state-b":                "Tennessee State-B",
    # Texas College
    "texas college":                    "Texas College",
    # Tuskegee
    "tuskegee univ.":                   "Tuskegee",
    "tuskegee university":              "Tuskegee",
    "tuskegee":                         "Tuskegee",
    # Virginia State
    "virginia state univ.":             "Virginia State",
    "virginia state university":        "Virginia State",
    "virginia state":                   "Virginia State",
    # Voorhees
    "voorhees univ.":                   "Voorhees",
    "voorhees university":              "Voorhees",
    "voorhees":                         "Voorhees",
    # Winston-Salem State
    "winston-salem state univ.":        "Winston-Salem",
    "winston-salem state university":   "Winston-Salem",
    "winston-salem":                    "Winston-Salem",
    # York
    "york college":                     "York",
    "york":                             "York",
}


def normalize_team_name(name: str) -> str:
    """Return the canonical team name, or the original if no mapping found."""
    return CANONICAL_NAMES.get(name.strip().lower(), name.strip())
