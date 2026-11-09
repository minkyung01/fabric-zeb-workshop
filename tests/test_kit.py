"""Offline consistency checks for the workshop kit. Run: python -m unittest discover -s tests -v"""
import importlib.util
import io
import json
import re
import subprocess
import sys
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

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
    def test_no_visible_bold_markers(self):
        marker = "*" * 2
        for path in ROOT.rglob("*.md"):
            self.assertNotIn(marker, path.read_text(encoding="utf-8"), str(path.relative_to(ROOT)))
        for name in NOTEBOOKS:
            for cell in notebook(name)["cells"]:
                if cell["cell_type"] == "markdown":
                    self.assertNotIn(marker, "".join(cell["source"]), name)

    def test_workshop_missions_and_participant_naming(self):
        for doc in DOCS:
            text = doc.read_text(encoding="utf-8")
            self.assertTrue("미션" in text, doc.name)
            instructions = re.sub(r"<img[^>]+>", "", text)
            instructions = re.sub(r"캡처[^\n]+", "", instructions)
            self.assertNotIn("zeb-p001", instructions, doc.name)
            self.assertNotIn("ws-p001", instructions, doc.name)
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn("`ws-p011`", readme)
        admin = (ROOT / "admin" / "README.md").read_text(encoding="utf-8")
        self.assertIn("`p011`부터", admin)
        self.assertIn("--participants p011-p022", admin)
        for path in [ROOT / "README.md", *DOCS]:
            self.assertNotIn("실습자 계정은", path.read_text(encoding="utf-8"), path.name)

    def test_read_only_question_flow_matches_approval_followup(self):
        for name in ("README.md", "docs/00-scenario.md", "docs/06-ontology.md",
                     "docs/07-data-agent.md", "docs/10-operations-agent.md", "docs/11-finish.md"):
            text = (ROOT / name).read_text(encoding="utf-8")
            self.assertIn("Plan", text, name)
        questions = (ROOT / "docs" / "07-data-agent.md").read_text(encoding="utf-8")
        self.assertIn("Data agent 직접 비교는", questions)
        self.assertIn("미확인", questions)
        self.assertIn("원본 데이터·Ontology", questions)
        approval = (ROOT / "docs" / "10-operations-agent.md").read_text(encoding="utf-8")
        self.assertIn('status becomes "open"', approval)
        self.assertIn("Execute the action only after", approval)
        self.assertIn("Crosses above 0.5", approval)
        self.assertNotIn("기본 매개 변수로 Run all", approval)

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


class Provisioning(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        spec = importlib.util.spec_from_file_location("zeb_provision", ROOT / "admin" / "provision.py")
        cls.module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.module)

    def test_participant_range_starts_at_p011(self):
        self.assertEqual(self.module.participants("p011-p022"),
                         [f"p{n:03d}" for n in range(11, 23)])
        self.assertEqual(self.module.participants("p011,p015-p017"),
                         ["p011", "p015", "p016", "p017"])

    def test_default_workspace_prefix_and_custom_override(self):
        for extra, prefix in (([], "ws-"), (["--prefix", "custom-"], "custom-")):
            with self.subTest(prefix=prefix):
                output = io.StringIO()
                args = ["provision.py", "--capacity", "test-capacity",
                        "--participants", "p011-p012", "--dry-run", *extra]
                with patch.object(sys, "argv", args), \
                        patch.object(self.module.Fabric, "get_all", return_value=[]), \
                        patch.object(self.module, "token", side_effect=AssertionError("No live authentication")), \
                        redirect_stdout(output):
                    self.module.main()
                self.assertIn(f"p011: {prefix}p011", output.getvalue())
                self.assertIn(f"p012: {prefix}p012", output.getvalue())
                self.assertNotIn("zeb-p", output.getvalue())


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
