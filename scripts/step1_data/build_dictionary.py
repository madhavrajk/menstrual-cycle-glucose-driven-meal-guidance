
from pathlib import Path
import zipfile
import csv
import io

zip_path = next(Path("data/raw").glob("*.zip"))
output = Path("docs/data_dictionary.md")
output.parent.mkdir(parents=True, exist_ok=True)

results = []

with zipfile.ZipFile(zip_path) as archive:
    files = sorted(
        n for n in archive.namelist()
        if n.lower().endswith(".csv")
    )

    for filename in files:
        print("Processing:", Path(filename).name, flush=True)

        with archive.open(filename) as raw:
            reader = csv.DictReader(
                io.TextIOWrapper(raw, encoding="utf-8-sig")
            )

            columns = reader.fieldnames or []
            count = 0
            participants = set()
            intervals = set()
            min_day = None
            max_day = None

            for row in reader:
                count += 1

                if "id" in columns and row.get("id"):
                    participants.add(row["id"])

                if "study_interval" in columns:
                    value = row.get("study_interval")
                    if value:
                        intervals.add(value)

                if "day_in_study" in columns:
                    try:
                        day = int(row["day_in_study"])
                        min_day = day if min_day is None else min(min_day, day)
                        max_day = day if max_day is None else max(max_day, day)
                    except (ValueError, TypeError):
                        pass

            results.append({
                "table": Path(filename).name,
                "columns": columns,
                "rows": count,
                "participants": len(participants)
                    if "id" in columns else "N/A",
                "intervals": ", ".join(sorted(intervals))
                    if "study_interval" in columns else "N/A",
                "days": f"{min_day}–{max_day}"
                    if min_day is not None else "N/A",
            })

lines = [
    "# MCPHAS​ES Data Dictionary",
    "",
    "## Table Inventory",
    "",
    "| Table | Rows | Participants | Intervals | Study days |",
    "|---|---:|---:|---|---|",
]

for r in results:
    lines.append(
        f"| {r['table']} | {r['rows']:,} | "
        f"{r['participants']} | {r['intervals']} | "
        f"{r['days']} |"
    )

lines.extend(["", "## Column Inventory", ""])

for r in results:
    lines.extend([
        f"### {r['table']}",
        "",
        "**Columns:** " + ", ".join(
            f"`{c}`" for c in r["columns"]
        ),
        "",
        "**Grain:** To be verified.",
        "",
        "**Unique key:** To be verified.",
        "",
    ])

output.write_text("\n".join(lines), encoding="utf-8")

print(f"\nSaved {output}")
print(f"Tables found: {len(results)}")