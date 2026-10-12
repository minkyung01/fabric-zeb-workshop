import hashlib
import base64
import json
import sys
import unittest
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from prepare_distribution import prepare


class AssetTests(unittest.TestCase):
    def test_hashes_and_csv_counts(self):
        import csv
        manifest = json.loads((ROOT / "data" / "synthetic" / "manifest.json").read_text(encoding="utf-8"))
        for file in manifest["files"]:
            path = ROOT / "data" / file["path"]
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), file["sha256"])
            with path.open(encoding="utf-8", newline="") as stream:
                self.assertEqual(len(list(csv.DictReader(stream))), file["rows"])

    def test_templates_unbound_and_syntax(self):
        import ast
        nbs = list((ROOT / "notebooks").glob("*.ipynb"))
        self.assertEqual(len(nbs), 8)
        for path in nbs:
            nb = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(nb["metadata"]["dependencies"], {})
            for cell in nb["cells"]:
                if cell["cell_type"] == "code":
                    ast.parse("".join(cell["source"]))
                    self.assertEqual(cell["outputs"], [])
                    self.assertIsNone(cell["execution_count"])
            source = path.with_suffix(".py").read_text(encoding="utf-8")
            self.assertIn("'approved_target': False", source)
            self.assertNotIn('mode("overwrite")', source)
            self.assertNotIn("DROP TABLE", source)
            self.assertLess(source.index("guard_target(TARGET"), source.find("spark.sql") if "spark.sql" in source else len(source))

    def test_distribution_example_fails_closed(self):
        with self.assertRaises(ValueError):
            prepare(ROOT / "config" / "targets.example.json")

    def test_public_summary_and_inventory_exclude_private_evidence(self):
        import copy
        from check_kit import public_files, validate_public_evidence
        summary = json.loads((ROOT / "validation" / "rehearsal-summary.json").read_text(encoding="utf-8"))
        status = json.loads((ROOT / "validation" / "status.json").read_text(encoding="utf-8"))
        validate_public_evidence(summary, status)
        paths = {p.relative_to(ROOT).as_posix() for p in public_files()}
        self.assertIn("validation/rehearsal-summary.json", paths)
        self.assertNotIn("validation/rehearsal-p01.json", paths)
        self.assertNotIn("config/targets.json", paths)
        for prefix in ("deployment/prepared/", "data/public/staged/", "assets/private-captures/"):
            self.assertFalse(any(p.startswith(prefix) for p in paths))
        for update in ({"public_redacted": False}, {"completed_cloud_notebook_jobs": 9},
                       {"capacity_end_state": "Active"}, {"decision_notebook_jobs": 1},
                       {"agent_should_run_at_end": True},
                       {"counts": {}},
                       {"workspace_id": str(uuid.UUID(int=1000))}):
            changed = copy.deepcopy(summary)
            changed.update(update)
            with self.assertRaises(ValueError):
                validate_public_evidence(changed, status)

    def test_preview_twelve_targets_no_cloud(self):
        # Project-local test file only, cleaned even on failure.
        path = ROOT / "config" / "test-targets.json"
        targets = []
        for i in range(1, 13):
            p = f"p{i:02}"
            targets.append({"participant_id": p, "scenario_id": "HS-D-VE-20260930",
                            "workspace_name": "ws_zeb_" + p, "lakehouse_name": "lh_zeb_" + p,
                            "workspace_id": str(uuid.UUID(int=i)),
                            "lakehouse_id": str(uuid.UUID(int=i+100)), "approved_target": True,
                            "protected_workspace_ids": [str(uuid.UUID(int=1000))],
                            "protected_lakehouse_ids": [str(uuid.UUID(int=1001))],
                            "binding_verified": True, "binding_evidence_ref": "LOCAL_TEST_NOT_REAL_BINDING",
                            "serialized_writer_attested": False})
        try:
            path.write_text(json.dumps({"targets": targets}), encoding="utf-8")
            manifest = prepare(path)
            self.assertEqual(len(manifest["participants"]), 12)
            self.assertFalse(manifest["cloud_provisioned"])
            self.assertTrue(all(len(p["notebooks"]) == 8 for p in manifest["participants"]))
            self.assertIn(manifest["required_public_zeb"], (
                "blocked_unfetched", "retained_hash_checked_admin_review_required"))
            self.assertFalse(manifest["live_workshop_ready"])
            self.assertTrue(all(len(p["files_to_upload"]) == 3 for p in manifest["participants"]))
            targets[1]["workspace_id"] = targets[0]["workspace_id"]
            path.write_text(json.dumps({"targets": targets}), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "duplicate"):
                prepare(path)
        finally:
            path.unlink(missing_ok=True)

    def test_excalidraw_text_dimensions_and_assets(self):
        scene = json.loads((ROOT / "assets" / "architecture.excalidraw").read_text(encoding="utf-8"))
        self.assertEqual(scene["type"], "excalidraw")
        for e in scene["elements"]:
            if e["type"] == "text":
                self.assertGreater(e["width"], 0)
                self.assertGreater(e["height"], 0)
                self.assertEqual(e["strokeColor"], "#000000")
        self.assertTrue((ROOT / "assets" / "architecture.svg").exists())
        self.assertEqual((ROOT / "assets" / "architecture.png").read_bytes()[:8], b"\x89PNG\r\n\x1a\n")

    def test_architecture_shared_scene_icons_and_scope(self):
        import base64
        import struct
        import xml.etree.ElementTree as ET
        scene = json.loads((ROOT / "assets" / "architecture.scene.json").read_text(encoding="utf-8"))
        editable = json.loads((ROOT / "assets" / "architecture.excalidraw").read_text(encoding="utf-8"))
        self.assertEqual(scene["elements"], editable["elements"])
        self.assertEqual(scene["files"], editable["files"])
        svg = ET.parse(ROOT / "assets" / "architecture.svg")
        images = svg.findall("{http://www.w3.org/2000/svg}image")
        icon_elements = [e for e in scene["elements"] if e["type"] == "image"]
        self.assertEqual(len(images), len(icon_elements))
        products = {e["customData"]["productIcon"] for e in icon_elements}
        self.assertEqual(products, {
            "fabric", "lakehouse", "onelake", "notebook", "ontology",
            "semantic-model", "power-bi", "eventhouse", "operations-agent",
            "teams", "foundry",
        })
        for e, image in zip(icon_elements, images):
            data = scene["files"][e["fileId"]]
            self.assertEqual(image.attrib["href"], data["dataURL"])
            self.assertEqual(base64.b64decode(data["dataURL"].split(",", 1)[1]),
                             (ROOT / "assets" / "icons" / (e["customData"]["productIcon"]+".svg")).read_bytes())
        png = (ROOT / "assets" / "architecture.png").read_bytes()
        self.assertEqual(struct.unpack(">II", png[16:24]), (scene["width"], scene["height"]))
        text = "\n".join(e["text"] for e in scene["elements"] if e["type"] == "text")
        for expected in ("건설 ZEB 워크숍 | Microsoft Fabric", "명시적 수집",
                         "Foundry | 선택", "결정 기록만 저장", "설계·발주 변경 없음",
                         "제안·담당자 승인", "근거 질의", "현황·보완안"):
            self.assertIn(expected, text)
        for stale in ("Capacity remains paused", "No cloud deployment", "Databricks", "Genie",
                      "메달리온을 읽는 법", "메달리온 읽는 법", "01_bronze", "gold.site_status",
                      "9,760", "63행", "SS ≥", "운영에 적용할 때", "① 현황 계산"):
            self.assertNotIn(stale, text)
        cards = {c["id"]: c for c in scene["cards"]}
        self.assertLess(cards["audit"]["x"] + cards["audit"]["width"], cards["teams"]["x"])
        self.assertLess(cards["model"]["x"] + cards["model"]["width"], cards["foundry"]["x"])
        for card in cards.values():
            for e in scene["elements"]:
                if (e["type"] == "text" and card["x"] < e["x"] < card["x"]+card["width"]
                        and card["y"] < e["y"] < card["y"]+card["height"]):
                    self.assertLessEqual(e["y"]+e["height"], card["y"]+card["height"]-4,
                                         f'Text clips card {card["id"]}: {e["text"]}')

    def test_architecture_routes_are_orthogonal_and_clear_of_cards(self):
        scene = json.loads((ROOT / "assets" / "architecture.scene.json").read_text(encoding="utf-8"))
        for route in scene["routes"]:
            for (x1, y1), (x2, y2) in zip(route["points"], route["points"][1:]):
                self.assertTrue(x1 == x2 or y1 == y2, f'Diagonal route: {route["id"]}')
                for c in scene["cards"]:
                    left, top = c["x"], c["y"]
                    right, bottom = left+c["width"], top+c["height"]
                    if x1 == x2:
                        overlap = left < x1 < right and max(min(y1, y2), top) < min(max(y1, y2), bottom)
                    else:
                        overlap = top < y1 < bottom and max(min(x1, x2), left) < min(max(x1, x2), right)
                    self.assertFalse(overlap, f'Route {route["id"]} crosses card {c["id"]}')

    def test_medallion_layers_and_gold_consumption_contract(self):
        import ast
        import build_notebooks
        from reference import fixtures
        scene = json.loads((ROOT / "assets" / "architecture.scene.json").read_text(encoding="utf-8"))
        cards = {c["id"]: c for c in scene["cards"]}
        layers = [c for c in scene["cards"] if c.get("role") == "medallion"]
        self.assertEqual([c["schema"] for c in layers], ["bronze", "silver", "gold"])
        self.assertEqual(len({c["y"] for c in layers}), 1)
        self.assertLess(cards["bronze"]["x"], cards["silver"]["x"])
        self.assertLess(cards["silver"]["x"], cards["gold"]["x"])
        self.assertGreater(cards["audit"]["y"], cards["gold"]["y"] + cards["gold"]["height"])
        routes = {r["id"]: r for r in scene["routes"]}
        gold = cards["gold"]
        for route_id, target in (("gold-to-ontology", "ontology"),
                                 ("gold-to-directlake", "model"),
                                 ("gold-to-snapshot", "eventhouse")):
            start, end = routes[route_id]["points"][0], routes[route_id]["points"][-1]
            self.assertEqual(start[0], gold["x"] + gold["width"])
            self.assertTrue(gold["y"] <= start[1] <= gold["y"] + gold["height"])
            self.assertEqual(end[1], cards[target]["y"])
            self.assertTrue(cards[target]["x"] <= end[0] <= cards[target]["x"] + cards[target]["width"])
        text = "\n".join(e["text"] for e in scene["elements"] if e["type"] == "text")
        for label in ("BRONZE", "SILVER", "GOLD", "원천 보존", "정제·연결",
                      "업무지표·판단근거", "OneLake | 공통 저장소", "schema-enabled Lakehouse"):
            self.assertIn(label, text)
        self.assertEqual((scene["width"], scene["height"]), (1600, 1100))
        for e in scene["elements"]:
            if e["type"] == "text":
                self.assertGreaterEqual(e["fontSize"], 20)
                self.assertGreaterEqual(e["x"], 0)
                self.assertGreaterEqual(e["y"], 0)
                self.assertLessEqual(e["x"] + e["width"], scene["width"])
                self.assertLessEqual(e["y"] + e["height"], scene["height"])
        data = fixtures()
        self.assertEqual(len(data), 16)
        tree = ast.parse(build_notebooks.GOLD)
        mapping = next(ast.literal_eval(n.value) for n in tree.body if isinstance(n, ast.Assign)
                       and any(isinstance(t, ast.Name) and t.id == "mapping" for t in n.targets))
        self.assertEqual(len(mapping), 12)
        self.assertTrue(set(mapping).issubset(data))
        self.assertEqual(len(data["bim_design_version"]["rows"]), 18)

    def test_action_parameter_discovery_and_contract(self):
        import ast
        nb = json.loads((ROOT / "notebooks" / "05_decision_log.ipynb").read_text(encoding="utf-8"))
        parameter_cells = [c for c in nb["cells"] if "parameters" in c["metadata"].get("tags", [])]
        self.assertEqual(len(parameter_cells), 1)
        tree = ast.parse("".join(parameter_cells[0]["source"]))
        params = [node.targets[0].id for node in tree.body if isinstance(node, ast.Assign)]
        contract = json.loads((ROOT / "operations" / "action-contract.json").read_text(encoding="utf-8"))
        self.assertEqual(params, [p["name"] for p in contract["parameters"]])
        self.assertNotIn("TARGET", params)
        self.assertNotIn("human_approved", params)
        self.assertEqual(contract["writes"], ["audit.decision_log only"])

    def test_tmdl_measures_contract_and_mandatory_copilot(self):
        import re
        script = (ROOT / "semantic_model" / "apply-model.tmdl").read_text(encoding="utf-8")
        dax = (ROOT / "semantic_model" / "measures.dax").read_text(encoding="utf-8")
        measures = re.findall(r"measure '([^']+)' = (.+)", script)
        self.assertEqual(len(measures), 10)
        self.assertEqual(len(re.findall(r"\trelationship ", script)), 3)
        for name, expression in measures:
            pattern = re.compile(re.escape(name) + r"\s*=\s*(.+?)(?=\n[A-Za-z][A-Za-z %]*\s*=|\Z)", re.S)
            match = pattern.search(dax)
            self.assertIsNotNone(match, name)
            self.assertEqual(" ".join(match.group(1).split()), " ".join(expression.split()))
        doc = (ROOT / "docs" / "07-powerbi.md").read_text(encoding="utf-8")
        self.assertIn("Copilot 인사이트 요약을 반드시 요청", doc)
        self.assertIn("TMDL View (Preview)", doc)
        self.assertIn("Summarize three decision insights", doc)

    def test_ic_b_training_reason_is_case_specific_and_provenanced(self):
        script = (ROOT / "semantic_model" / "ic-b-grade-basis.tmdl").read_text(encoding="utf-8")
        self.assertIn("ref table SiteStatus", script)
        self.assertEqual(script.count("\t\tmeasure "), 1)
        self.assertNotIn("partition ", script)
        self.assertNotIn("\trelationship ", script)
        self.assertIn('_site <> "IC-B" || ISBLANK(_ss) || ISBLANK(_pe)', script)
        for column in ("site_code", "selfsuff_pct", "primary_energy_kwh_m2y", "grade_rank"):
            self.assertIn(f"SELECTEDVALUE('SiteStatus'[{column}])", script)
        for expression in ("_ss >= 60 || _pe < 50", "_ss >= 40 || _pe < 70"):
            self.assertIn(expression, script)
        self.assertNotIn("_pe <= 70", script)
        self.assertIn("retained synthetic ref_zeb_grade_criteria + erp_project.main_use", script)
        self.assertIn("실제 법적 인증 미검증", script)
        contract = json.loads((ROOT / "semantic_model" / "model-contract.json").read_text(encoding="utf-8"))
        extension = contract["educational_extensions"][0]
        self.assertEqual(extension["measure"], "IC-B Grade Basis (Training)")
        self.assertEqual(extension["script"], "semantic_model/ic-b-grade-basis.tmdl")
        self.assertFalse(extension["dynamic_criterion_table_binding"])
        self.assertFalse(extension["legal_certification_verified"])
        doc = (ROOT / "docs" / "07-powerbi.md").read_text(encoding="utf-8")
        self.assertIn('group only by site_code', doc)
        self.assertIn("동적 criterion", doc)

    def test_required_public_not_completed_by_internal_only(self):
        doc = (ROOT / "docs" / "02-bronze.md").read_text(encoding="utf-8")
        self.assertIn("필수 segment", doc)
        self.assertIn("blocked/미완료", doc)
        source = (ROOT / "notebooks" / "06_public_zeb.py").read_text(encoding="utf-8")
        self.assertIn("Required public snapshot missing/unapproved", source)

    def test_snapshot_exact_schema_action_evidence_and_stale_block(self):
        import copy
        from build_notebooks import SNAPSHOT
        from reference import fixtures, baseline, candidates, canonical, digest
        data = fixtures()
        status = baseline(data)
        captured = {}
        class Row:
            def __init__(self, values):
                self.values = values
            def asDict(self):
                return self.values
        class Table:
            def filter(self, _condition):
                return self
            def collect(self):
                return [Row(r) for r in status if r["risk"] != "normal"]
        class Spark:
            def table(self, _name):
                return Table()
        class FS:
            def exists(self, _path):
                return False
            def put(self, path, content, overwrite):
                self.assert_no_overwrite = not overwrite
                captured[path] = content
        class Utils:
            fs = FS()
        env = {"spark": Spark(), "data": data, "candidates": candidates, "canonical": canonical,
               "digest": digest, "notebookutils": Utils(), "print": lambda *_args: None,
               "TARGET": {"participant_id": "p01", "scenario_id": "HS-D-VE-20260930"}}
        exec(SNAPSHOT, env)
        rows = [json.loads(line) for line in captured["Files/workshop/operations_snapshot.jsonl"].splitlines()]
        contract = json.loads((ROOT / "operations" / "snapshot-contract.json").read_text(encoding="utf-8"))
        self.assertEqual(len(rows), 4)
        self.assertTrue(all(set(row) == set(contract["fields"]) for row in rows))
        self.assertEqual(sum(bool(r["recommended_option_set_id"]) for r in rows), 1)
        hs = next(r for r in rows if r["site_code"] == "HS-D")
        option = next(r for r in candidates(data) if r["option_set_id"] == "OPT-D5+OPT-D6")
        self.assertEqual(hs["result_hash"], digest(option))
        status = copy.deepcopy(status)
        next(r for r in status if r["site_code"] == "HS-D")["baseline_hash"] = "stale"
        with self.assertRaisesRegex(ValueError, "mixed/stale"):
            exec(SNAPSHOT, env)

    def test_persisted_offline_definition_binding(self):
        import shutil
        path = ROOT / "config" / "test-package-target.json"
        folder = ROOT / "tests" / "generated-package-check"
        self.assertFalse(folder.exists())
        target = {"participant_id": "p01", "scenario_id": "HS-D-VE-20260930",
                  "workspace_name": "ws_zeb_p01", "lakehouse_name": "lh_zeb_p01",
                  "workspace_id": str(uuid.UUID(int=1)), "lakehouse_id": str(uuid.UUID(int=2)),
                  "protected_workspace_ids": [str(uuid.UUID(int=1000))],
                  "protected_lakehouse_ids": [str(uuid.UUID(int=1001))],
                  "binding_verified": True, "binding_evidence_ref": "LOCAL_TEST_NOT_REAL_BINDING",
                  "approved_target": True, "serialized_writer_attested": False}
        try:
            path.write_text(json.dumps({"targets": [target]}), encoding="utf-8")
            prepare(path, write=True, output_folder=folder)
            self.assertTrue((folder / "manifest.json").exists())
            for definition_path in (folder / "p01").glob("*.definition.json"):
                definition = json.loads(definition_path.read_text(encoding="utf-8"))
                payload = base64.b64decode(definition["definition"]["parts"][0]["payload"])
                nb = json.loads(payload)
                binding = nb["metadata"]["dependencies"]["lakehouse"]
                self.assertEqual(binding["default_lakehouse"], target["lakehouse_id"])
                self.assertEqual(binding["default_lakehouse_workspace_id"], target["workspace_id"])
                ns = {}
                exec("".join(nb["cells"][1]["source"]), ns)
                self.assertEqual(ns["TARGET"]["workspace_id"], binding["default_lakehouse_workspace_id"])
                self.assertEqual(ns["TARGET"]["protected_workspace_ids"], target["protected_workspace_ids"])
                self.assertEqual(ns["TARGET"]["protected_lakehouse_ids"], target["protected_lakehouse_ids"])
                self.assertEqual(ns["TARGET"]["fixture_sha256"],
                                 hashlib.sha256((ROOT / "data" / "synthetic" / "fixtures.json").read_bytes()).hexdigest())
                self.assertEqual(payload, (folder / "p01" / (definition_path.name.replace(".definition.json", ".ipynb"))).read_bytes())
        finally:
            path.unlink(missing_ok=True)
            if folder.exists():
                shutil.rmtree(folder)

    def test_public_review_flag_requires_evidence(self):
        path = ROOT / "config" / "test-public-review.json"
        target = {"participant_id": "p01", "scenario_id": "HS-D-VE-20260930",
                  "workspace_name": "ws_zeb_p01", "lakehouse_name": "lh_zeb_p01",
                  "workspace_id": str(uuid.UUID(int=1)), "lakehouse_id": str(uuid.UUID(int=2)),
                  "protected_workspace_ids": [str(uuid.UUID(int=1000))],
                  "protected_lakehouse_ids": [str(uuid.UUID(int=1001))],
                  "binding_verified": True, "binding_evidence_ref": "LOCAL_TEST_NOT_REAL_BINDING",
                  "approved_target": True, "serialized_writer_attested": False,
                  "public_snapshot_reviewed": True, "public_review_evidence_ref": ""}
        try:
            path.write_text(json.dumps({"targets": [target]}), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "public license review evidence"):
                prepare(path)
        finally:
            path.unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
