"""Reproduce source files from the explicitly synthetic fixture package."""
import csv
import hashlib
import json
from pathlib import Path
from reference import fixtures, ROOT


def build():
    data = fixtures()
    files = []
    for name, table in sorted(data.items()):
        path = ROOT / "data" / "synthetic" / f"{name}.csv"
        with path.open("w", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=[c[0] for c in table["schema"]])
            writer.writeheader()
            writer.writerows(table["rows"])
        files.append({"path": f"synthetic/{path.name}", "rows": len(table["rows"]),
                      "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                      "source_kind": "SYNTHETIC", "schema": table["schema"]})
    manifest = {"as_of_date": "2026-09-30", "source": "Original Notebook02 literal deterministic generator",
                "not_customer_exports": True, "files": files,
                "fixtures_sha256": hashlib.sha256((ROOT / "data" / "synthetic" / "fixtures.json").read_bytes()).hexdigest()}
    (ROOT / "data" / "synthetic" / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"{len(files)} reproducible synthetic CSVs; original source code is not included.")


if __name__ == "__main__":
    build()
