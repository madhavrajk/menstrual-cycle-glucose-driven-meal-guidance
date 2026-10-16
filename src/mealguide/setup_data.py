"""Put a PhysioNet mcPHASES download where the code expects it.

    make data SRC=~/Downloads/mcphases-...-1.0.0        # extracted folder
    make data SRC=~/Downloads/mcphases-...-1.0.0.zip    # or the ZIP

The script checks every file against PhysioNet's SHA256SUMS.txt and writes
$MCPHASES_HOME/data/raw/mcphases-1.0.0.zip. Ava's Step 1 scripts read that zip, and so
does the Step 2 code. After it succeeds, you can delete the original download.
"""

import argparse
import hashlib
import shutil
import sys
import zipfile
from pathlib import Path

from mealguide import paths

TARGET_NAME = "mcphases-1.0.0.zip"
REQUIRED = ["hormones_and_selfreport.csv", "glucose.csv", "heart_rate.csv", "steps.csv",
            "sleep.csv", "resting_heart_rate.csv"]
CLOUD_MARKERS = ("CloudStorage", "OneDrive", "Mobile Documents", "Dropbox", "Google Drive")


def _sha256(f) -> str:
    h = hashlib.sha256()
    for block in iter(lambda: f.read(1 << 20), b""):
        h.update(block)
    return h.hexdigest()


def _expected(sums_text: str) -> dict[str, str]:
    pairs = (line.split(maxsplit=1) for line in sums_text.splitlines() if line.strip())
    return {name.strip().lstrip("*"): digest for digest, name in pairs}


def verify_folder(folder: Path) -> int:
    sums = folder / "SHA256SUMS.txt"
    if not sums.exists():
        print("  ! no SHA256SUMS.txt; skipping checksum verification")
        return 0
    bad = []
    for name, digest in _expected(sums.read_text()).items():
        path = folder / name
        if not path.exists():
            bad.append(f"{name} (missing)")
            continue
        with open(path, "rb") as f:
            if _sha256(f) != digest:
                bad.append(name)
    if bad:
        sys.exit(f"Checksum failed for: {', '.join(bad)}. Re-download from PhysioNet.")
    return len(_expected(sums.read_text()))


def verify_zip(zip_path: Path) -> int:
    with zipfile.ZipFile(zip_path) as z:
        names = z.namelist()
        sums_name = next((n for n in names if n.endswith("SHA256SUMS.txt")), None)
        if not sums_name:
            print("  ! no SHA256SUMS.txt in zip; skipping checksum verification")
            return 0
        prefix = sums_name[: -len("SHA256SUMS.txt")]
        expected = _expected(z.read(sums_name).decode())
        bad = []
        for name, digest in expected.items():
            if prefix + name not in names:
                bad.append(f"{name} (missing)")
                continue
            with z.open(prefix + name) as f:
                if _sha256(f) != digest:
                    bad.append(name)
    if bad:
        sys.exit(f"Checksum failed for: {', '.join(bad)}. Re-download from PhysioNet.")
    return len(expected)


def find_data_folder(src: Path) -> Path:
    hits = sorted(src.rglob("hormones_and_selfreport.csv"))
    if not hits:
        sys.exit(f"{src} doesn't look like mcPHASES (no hormones_and_selfreport.csv).")
    folder = hits[0].parent
    missing = [n for n in REQUIRED if not (folder / n).exists()]
    if missing:
        sys.exit(f"Download is incomplete; missing {missing}.")
    return folder


def main():
    parser = argparse.ArgumentParser(description="Install the mcPHASES download for this repo")
    parser.add_argument("src", type=Path, help="PhysioNet download: ZIP file or extracted folder")
    parser.add_argument("--force", action="store_true", help="replace an existing zip")
    args = parser.parse_args()

    src = args.src.expanduser().resolve()
    target = paths.RAW / TARGET_NAME
    print(f"MCPHASES_HOME = {paths.HOME}")
    if any(m in str(paths.RAW) for m in CLOUD_MARKERS):
        print("  ! WARNING: this location is synced to the cloud. The data use agreement "
              "forbids sharing; set MCPHASES_HOME=~/mcphases in .env.")
    if target.exists() and not args.force:
        sys.exit(f"{target} already exists. Use --force to replace it.")
    paths.RAW.mkdir(parents=True, exist_ok=True)

    if src.is_file() and src.suffix == ".zip":
        print(f"Verifying {src.name} ...")
        n = verify_zip(src)
        shutil.copy2(src, target)
    elif src.is_dir():
        folder = find_data_folder(src)
        print(f"Verifying {folder.name}/ ...")
        n = verify_folder(folder)
        print("Zipping (a few minutes for ~3.4 GB) ...")
        tmp = target.with_suffix(".zip.partial")
        with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as z:
            for f in sorted(folder.iterdir()):
                if f.is_file():
                    z.write(f, f"mcphases-1.0.0/{f.name}")
        tmp.rename(target)
    else:
        sys.exit(f"{src} is not a .zip file or a folder.")

    print(f"OK: {n} files verified; data at {target}")
    print("Next: make step1 && make baselines. You can now delete the original download.")


if __name__ == "__main__":
    main()
