"""Where data lives.

Real mcPHASES data sits under MCPHASES_HOME (set in .env), which should be outside
OneDrive. It has the same layout Ava's Step 1 scripts expect:

    $MCPHASES_HOME/data/raw/<mcPHASES zip>
    $MCPHASES_HOME/data/processed/daily_master_labeled.csv

If MCPHASES_HOME is unset, this repo's own data/ folder is used.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(REPO_ROOT / ".env")

HOME = Path(os.path.expanduser(os.environ.get("MCPHASES_HOME") or REPO_ROOT))
RAW = HOME / "data" / "raw"
PROCESSED = HOME / "data" / "processed"

SYNTHETIC = REPO_ROOT / "data" / "synthetic"
RESULTS = REPO_ROOT / "results"


def raw_source() -> Path:
    """The mcPHASES zip in data/raw/, or else an extracted folder inside data/raw/."""
    zips = sorted(RAW.glob("*.zip"))
    if zips:
        return zips[0]
    marker = next(iter(sorted(RAW.rglob("hormones_and_selfreport.csv"))), None)
    if marker:
        return marker.parent
    raise FileNotFoundError(
        f"No mcPHASES data in {RAW}.\n"
        f"  Run: make data SRC=<path to your PhysioNet download (zip or folder)>\n"
        f"  Data location comes from MCPHASES_HOME in .env (currently {HOME}).")
