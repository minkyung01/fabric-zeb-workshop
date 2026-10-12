"""One-time offline extraction of the already retrieved synthetic Notebook02.

No Spark code, imports or original notebook definitions are published.
Only the original deterministic fixture expressions are evaluated.
"""
import ast
import datetime
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def extract(path):
    text = Path(path).read_text(encoding="utf-8-sig")
    section = text.split("NOTEBOOK ")[2].split("NOTEBOOK ")[0]
    cells = re.findall(r"CELL code\n(.*?)(?=\nCELL |\Z)", section, re.S)
    collected = {}

    def save(rows, table, ddl, source=None):
        columns = [part.strip().split() for part in ddl.split(",")]
        collected[table.split(".")[1]] = {
            "schema": columns,
            "rows": [dict(zip([c[0] for c in columns], row)) for row in rows],
            "provenance": "SYNTHETIC: original Notebook02 deterministic fixtures; not ERP/PMS exports",
        }

    env = {
        "date": datetime.date,
        "timedelta": datetime.timedelta,
        "d": lambda s: datetime.date.fromisoformat(s) if s else None,
        "AS_OF": datetime.date(2026, 9, 30),
        "save": save,
    }
    for code in cells:
        tree = ast.parse(code)
        safe = []
        for node in tree.body:
            # Skip original setup/reset and diagnostic Spark expressions entirely.
            if isinstance(node, (ast.Import, ast.ImportFrom, ast.FunctionDef)):
                continue
            rendered = ast.unparse(node)
            if any(token in rendered for token in ("spark.", "display(", "print(", "SOURCE")):
                continue
            if isinstance(node, ast.For) and "DROP TABLE" in rendered:
                continue
            safe.append(node)
        exec(compile(ast.Module(body=safe, type_ignores=[]), "<fixture-extraction>", "exec"), env)
    out = ROOT / "data" / "synthetic" / "fixtures.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(collected, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")
    print({name: len(table["rows"]) for name, table in collected.items()})


if __name__ == "__main__":
    extract(sys.argv[1])
