"""Offline consistency checks for the workshop kit. Run: python -m unittest discover -s tests -v"""
import json
import re
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = sorted((ROOT / "docs").glob("*.md"))
NOTEBOOKS = ["01_bronze_public_ingest", "02_bronze_contoso_generate", "03_silver_conform", "04_gold_model",
             "05_answers", "06_risk_event", "nb_apply_decision"]
MODEL_TABLES = {"pub_zeb_certification", "ref_region", "ref_zeb_grade_criteria", "ref_building_use", "scm_vendor",
                "ref_equipment_category", "site_status", "milestone_forecast", "po_status"}


def notebook(name):
    return json.loads((ROOT / "notebooks" / f"{name}.ipynb").read_text(encoding="utf-8"))


def code(name):
    return "\n".join("".join(c["source"]) for c in notebook(name)["cells"] if c["cell_type"] == "code")


class Notebooks(unittest.TestCase):
    def test_built_from_sources(self):
        result = subprocess.run([sys.executable, str(ROOT / "tools" / "build_notebooks.py"), "--check"],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)

    def test_expected_set(self):
        self.assertEqual(sorted(p.stem for p in (ROOT / "notebooks").glob("*.ipynb")), sorted(NOTEBOOKS))

    def test_code_compiles_and_has_one_parameter_cell(self):
        for name in NOTEBOOKS:
            with self.subTest(name):
                cells = notebook(name)["cells"]
                params = [c for c in cells if "parameters" in c["metadata"].get("tags", [])]
                self.assertEqual(len(params), 1)
                for cell in cells:
                    if cell["cell_type"] == "code":
                        compile("".join(cell["source"]), name, "exec")

    def test_no_bound_lakehouse_or_tenant_ids(self):
        for name in NOTEBOOKS:
            text = (ROOT / "notebooks" / f"{name}.ipynb").read_text(encoding="utf-8")
            self.assertNotIn("default_lakehouse", text, name)
            self.assertIsNone(re.search(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", text), name)

    def test_apply_decision_runs_existing_notebooks(self):
        for target in re.findall(r'notebook\.run\("([^"]+)"', code("nb_apply_decision")):
            self.assertIn(target, NOTEBOOKS)

    def test_eventhouse_columns_match_docs(self):
        doc = (ROOT / "docs" / "10-operations-agent.md").read_text(encoding="utf-8")
        table = re.search(r"\.create-merge table ZebRiskEvent \((.*?)\)\n", doc, re.S).group(1)
        columns = [line.strip().split(":")[0] for line in table.strip().splitlines()]
        for name in ("06_risk_event", "nb_apply_decision"):
            command = re.search(r"\.set-or-append ZebRiskEvent <\|\nprint (.*?)\"\"\"", code(name), re.S).group(1)
            sent = re.findall(r"(\w+) = ", command)
            self.assertEqual(sent, columns, name)


class Docs(unittest.TestCase):
    def test_chapters_linked_from_readme(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        for doc in DOCS:
            self.assertIn(f"docs/{doc.name}", readme)

    def test_relative_links_resolve(self):
        for md in [ROOT / "README.md", *DOCS, *sorted((ROOT / "admin").glob("*.md")), ROOT / "assets" / "icon-attribution.md"]:
            text = md.read_text(encoding="utf-8")
            for target in re.findall(r'\]\(([^)]+)\)|src="([^"]+)"', text):
                link = next(t for t in target if t)
                if link.startswith(("http", "#", "mailto:")):
                    continue
                path = (md.parent / link.split("#")[0]).resolve()
                self.assertTrue(path.exists(), f"{md.name}: {link}")

    def test_chapter_navigation(self):
        for doc in DOCS:
            lines = doc.read_text(encoding="utf-8").splitlines()
            self.assertTrue(lines[0].startswith(f"# {doc.name[:2]}."), doc.name)
            self.assertIn("[목차](../README.md)", lines[2], doc.name)

    def test_notebook_names_in_docs_exist(self):
        for doc in DOCS:
            for name in re.findall(r"`(\d\d_[a-z_]+|nb_[a-z_]+)`", doc.read_text(encoding="utf-8")):
                self.assertIn(name, NOTEBOOKS, f"{doc.name}: {name}")


class FabricAssets(unittest.TestCase):
    def test_tmdl_script(self):
        text = (ROOT / "fabric" / "sm_zeb.tmdl").read_text(encoding="utf-8")
        self.assertTrue(text.startswith("createOrReplace"))
        tables = set(re.findall(r"(?:fromColumn|toColumn): (\w+)\.", text)) | set(re.findall(r"ref table (\w+)", text))
        self.assertLessEqual(tables, MODEL_TABLES)
        self.assertEqual(len(re.findall(r"^\trelationship ", text, re.M)), 7)
        self.assertEqual(len(re.findall(r"^\t\tmeasure ", text, re.M)), 20)

    def test_theme_is_json(self):
        self.assertEqual(json.loads((ROOT / "fabric" / "zeb-theme.json").read_text(encoding="utf-8"))["name"], "ZEB Control Tower")

    def test_reference_ontology_has_placeholders_only(self):
        folder = ROOT / "fabric" / "ont_zeb_reference"
        entities = list(folder.glob("EntityTypes/*/definition.json"))
        self.assertEqual(len(entities), 22)
        for path in folder.rglob("*.json"):
            text = path.read_text(encoding="utf-8")
            for key in ("workspaceId", "itemId"):
                for value in re.findall(rf'"{key}": "([^"]+)"', text):
                    self.assertIn(value, ("{{WORKSPACE_ID}}", "{{LAKEHOUSE_ID}}"), path)

    def test_architecture_scene(self):
        scene = json.loads((ROOT / "assets" / "architecture.scene.json").read_text(encoding="utf-8"))
        cards = {c["id"] for c in scene["cards"]}
        self.assertLessEqual({"source", "bronze", "silver", "gold", "ontology", "dataagent", "model", "powerbi",
                              "eventhouse", "operations", "teams", "apply", "foundry"}, cards)


if __name__ == "__main__":
    unittest.main()
