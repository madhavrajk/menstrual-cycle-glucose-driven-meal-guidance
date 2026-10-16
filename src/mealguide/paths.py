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


def raw_zip() -> Path:
    zips = sorted(RAW.glob("*.zip"))
    if not zips:
        raise FileNotFoundError(f"No mcPHASES zip in {RAW}. Set MCPHASES_HOME in .env.")
    return zips[0]
