"""Central settings. This is the ONLY file you should ever need to edit."""
import os

SEED = 20260801

HERE     = os.path.dirname(os.path.abspath(__file__))
ROOT     = os.path.abspath(os.path.join(HERE, ".."))
DATA     = os.path.join(ROOT, "data")
PRIMARY  = os.path.join(DATA, "primary")
EXTERNAL = os.path.join(ROOT, "external_data")
OUTPUTS  = os.path.join(ROOT, "outputs")
FIGURES  = os.path.join(OUTPUTS, "figures")
TABLES   = os.path.join(OUTPUTS, "tables")

# ---------------------------------------------------------------------------
# ONLY TOUCH THIS IF run_all.py TELLS YOU COLUMN DETECTION FAILED.
# Put the exact column name from the real CSV on the right of the colon.
# Leave as None to let the script auto-detect.
# ---------------------------------------------------------------------------
MANUAL_OVERRIDES = {
    "year":     None,   # e.g. "Year"
    "grade":    None,   # e.g. "Grade"
    "division": None,
    "district": None,
    "block":    None,
    "cluster":  None,
    "gp":       None,   # Gram Panchayat
    "gender":   None,
    "score":    None,
}
# If auto-detection of the 20 question columns fails, list them here explicitly.
MANUAL_ITEM_COLUMNS = None      # e.g. ["Q1","Q2", ... ,"Q20"]

# Optional: real competency mapping. Drop a CSV in external_data/ with columns
# item, competency_code, competency_label  and name it here.
COMPETENCY_MAP_FILE = "competency_map.csv"     # falls back to inference if absent

# Division is deliberately EXCLUDED: it maps 1:1 from district and is too coarse to act on.
GEO_LEVELS = ["district", "block", "cluster", "gp"]

# Speed valve. Leave as None. If the real file turns out to be millions of rows and the
# run is slow, set this to 0.25 for a fast first pass, then put it back to None.
SAMPLE_FRACTION = None

# Per the organisers, the 20 items CHANGE each year. Cross-year score changes are
# therefore partly instrument change. Leave False unless SMEs confirm anchoring.
ITEMS_COMPARABLE_ACROSS_YEARS = False
CROSS_YEAR_CAVEAT = ("CAVEAT: items differ across years but map to a constant competency framework. "
                     "Item-level year comparisons mix learning and instrument change; competency-level "
                     "comparisons are more defensible (still assume similar difficulty within competency). "
                     "Prefer rankings and competency-level statements across years.")

# Analysis knobs
MIN_STUDENTS_PER_GP    = 15    # GPs below this are excluded from GP-level rankings
MIN_STUDENTS_PER_BLOCK = 60
FLOOR_PERCENTILE       = 10    # the "Floor Index"
TOP_N_REPORT           = 15

# Charting: green = socially preferable, white at benchmark, red = worse.
DIVERGING = ["#B2182B", "#EF8A62", "#FDDBC7", "#FFFFFF", "#D9F0D3", "#7FBF7B", "#1B7837"]
GREEN, RED, GREY, INK = "#1B7837", "#B2182B", "#9E9E9E", "#222222"
