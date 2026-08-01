"""Central path configuration for the SIA coverage-reconciliation pipeline.
All scripts import paths from here instead of hardcoding them, so the whole
pipeline is portable: clone the repo anywhere, `pip install -r
requirements.txt`, drop the supplied data pack into data/, and run
`bash run_pipeline.sh` (or `make all`).
"""
from pathlib import Path
REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = REPO_ROOT / "data"

# The assessment pack must not be renamed or restructured, so paths point
# into it as issued rather than into a rearranged copy.
PACK_DIR      = DATA_DIR / "Part1_Q1_Campaign_Tracking"
REFERENCE_DIR = PACK_DIR
TRACKS_DIR    = PACK_DIR / "tracks"

OUTPUT_DIR = REPO_ROOT / "output"
DOCS_DIR = REPO_ROOT / "docs"
DB_PATH = OUTPUT_DIR / "campaign.sqlite"
MASTERLIST_CSV = REFERENCE_DIR / "settlement_masterlist.csv"
ETALLY_CSV = REFERENCE_DIR / "etally_daily.csv"
INACCESSIBLE_CSV = REFERENCE_DIR / "inaccessible_settlements.csv"
BOUNDARIES_GPKG = REFERENCE_DIR / "boundaries.gpkg"
OUTPUT_DIR.mkdir(exist_ok=True)
