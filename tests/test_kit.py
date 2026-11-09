"""Offline consistency checks for the workshop kit. Run: python -m unittest discover -s tests -v"""
import base64
import importlib.util
import io
import json
import re
import subprocess
import sys
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

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
    def test_ontology_prompt_uses_reference_names(self):
        text = (ROOT / "docs" / "06-ontology.md").read_text(encoding="utf-8")
        prompts = "\n".join(re.findall(r"``` text\n(.*?)```", text, re.S))
        reference = ROOT / "fabric" / "ont_zeb_reference"
        for kind in ("EntityTypes", "RelationshipTypes"):
            for path in (reference / kind).glob("*/definition.json"):
                name = json.loads(path.read_text(encoding="utf-8-sig"))["name"]
                self.assertIn(name + "(", prompts, name)
        self.assertNotIn("아래 교재 이름 기준", prompts)
        self.assertIn("`grade_code` = `grade_code`", text)

    def test_run_all_guidance_for_participant_notebooks(self):
        for chapter in ("01-workspace.md", "02-bronze-public.md", "03-bronze-contoso.md",
                        "04-silver.md", "05-gold.md", "07-data-agent.md",
                        "10-operations-agent.md"):
            text = (ROOT / "docs" / chapter).read_text(encoding="utf-8")
            self.assertIn("Run all", text, chapter)
            self.assertNotIn("한 셀씩 실행", text, chapter)
        for name in NOTEBOOKS:
            if name == "nb_apply_decision":
                continue
            markdown = "\n".join("".join(cell["source"]) for cell in notebook(name)["cells"]
                                 if cell["cell_type"] == "markdown")
            self.assertIn("Run all", markdown, name)
            self.assertNotIn("한 셀씩 실행", markdown, name)

    def test_no_duplicate_list_numbers(self):
        for path in [ROOT / "README.md", *DOCS, *sorted((ROOT / "admin").glob("*.md"))]:
            text = path.read_text(encoding="utf-8")
            self.assertIsNone(
                re.search(r"^\s*\d+\.\s+(?:\d+|[ivxlcdm]+)\.\s", text, re.M | re.I),
                path.name,
            )

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
        self.assertIn("본인 작업 영역", readme)
        admin = (ROOT / "admin" / "README.md").read_text(encoding="utf-8")
        self.assertIn("`p011`부터", admin)
        self.assertIn("--participants p011-p022", admin)
        for path in [ROOT / "README.md", *DOCS]:
            text = path.read_text(encoding="utf-8")
            self.assertNotIn("실습자 계정은", text, path.name)
            instructions = re.sub(r"<img[^>]+>", "", text)
            self.assertIsNone(re.search(r"\b(?:ws-|zeb-|fdy-zeb-|rg-zeb-)?p\d{3}\b",
                                       instructions), path.name)

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

    def test_question_checks_are_in_answer_table(self):
        questions = (ROOT / "docs" / "07-data-agent.md").read_text(encoding="utf-8")
        self.assertIn("| 번호 | 유형 | 질문 | 확인할 정답 | 눈여겨볼 점 |", questions)
        rows = [line for line in questions.splitlines()
                if re.match(r"^\| Q[1-8] \|", line)]
        self.assertEqual(len(rows), 8)
        for row in rows:
            self.assertEqual(len(row.split("|")[1:-1]), 5)
        self.assertIn("'확인할 정답'의 대상·핵심 수치·판정 근거·결론은 답변에 포함되어야", questions)
        self.assertNotIn("모두 맞히는 것이 목표가 아니라", questions)
        self.assertNotIn("## 5.", questions)
        self.assertNotIn("## 6.", questions)

    def test_power_bi_focuses_on_site_control_tower(self):
        report = (ROOT / "docs" / "08-power-bi.md").read_text(encoding="utf-8")
        main, optional = report.split("## (선택) 공공 인증 현황", 1)
        completion = optional.split("## 이 장의 완료 기준", 1)[1]
        self.assertIn("보고서 한 페이지", main)
        self.assertIn("## 3. Copilot으로 현장 컨트롤 타워 만들기", main)
        self.assertIn("## 4. D단지 위험을 질문으로 확인", main)
        self.assertIn("`rpt_zeb`로 저장", main)
        creation = main.split("## 3. Copilot으로 현장 컨트롤 타워 만들기", 1)[1]
        self.assertIn("2.  (선택) 보고서 테마를 적용합니다", creation)
        self.assertIn("../fabric/zeb-theme.json", creation)
        self.assertIn("Custom theme name 옆 … → Import", creation)
        self.assertNotIn("zeb-theme.json", optional)
        self.assertNotIn("Horizontal", report)
        self.assertNotIn("ZEB 인증 현황", completion)
        operations = (ROOT / "docs" / "10-operations-agent.md").read_text(encoding="utf-8")
        self.assertIn("(선택 08장 완료 시)", operations)

    def test_power_bi_is_optional_before_instructor_demo(self):
        report = (ROOT / "docs" / "08-power-bi.md").read_text(encoding="utf-8")
        self.assertTrue(report.startswith("# 08. Power BI (선택)"))
        questions = (ROOT / "docs" / "07-data-agent.md").read_text(encoding="utf-8")
        self.assertIn("다음: [10. Operations agent]", questions)
        operations = (ROOT / "docs" / "10-operations-agent.md").read_text(encoding="utf-8")
        self.assertIn("08장을 건너뛰었다면 이 단계는 생략", operations)
        completion = operations.split("## 이 장의 완료 기준", 1)[1].split("## Troubleshooting", 1)[0]
        self.assertNotIn("보고서의 위험 현장이", completion)
        self.assertIn("11단계 SQL 결과로 반영을 확인", completion)
        finish = (ROOT / "docs" / "11-finish.md").read_text(encoding="utf-8")
        self.assertIn("이 장까지 완료하면 참가자 실습은 끝", finish)
        self.assertIn("강사가 웹 대시보드", finish)
        self.assertIn("로컬 앱을 설치하거나 실행할 필요가 없습니다", finish)

    def test_power_bi_license_activation_precedes_model_creation(self):
        report = (ROOT / "docs" / "08-power-bi.md").read_text(encoding="utf-8")
        self.assertLess(report.index("### Semantic model을 만들기 전에: Power BI 체험판 활성화"),
                        report.index("## 1. Semantic model 만들기"))
        self.assertIn("이미 유효한 Pro·PPU 또는 체험판", report)
        self.assertIn("작업 영역의 기존 유료 용량을 변경하는 단계가 아닙니다", report)
        self.assertIn("d08-lakehouse-new-model.png", report)

    def test_foundry_is_instructor_demo_only(self):
        foundry = (ROOT / "docs" / "09-foundry-agent.md").read_text(encoding="utf-8")
        self.assertTrue(foundry.startswith("# 09. Foundry agent (강사 시연)"))
        self.assertIn("참가자는 따라 만들지 않습니다", foundry)
        self.assertIn("승인 전 상태(D단지 V3·위험)", foundry)
        self.assertIn("참가자 작업 영역을 시연용으로 초기화하지 않습니다", foundry)
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        participant, demo = readme.split("### 실습 종료 후 강사 시연", 1)
        self.assertNotIn("docs/09-foundry-agent.md", participant)
        self.assertIn("docs/09-foundry-agent.md", demo)
        for chapter in ("07-data-agent.md", "08-power-bi.md"):
            text = (ROOT / "docs" / chapter).read_text(encoding="utf-8")
            self.assertIn("다음: [10. Operations agent]", text)
        finish = (ROOT / "docs" / "11-finish.md").read_text(encoding="utf-8")
        participant, demo = finish.split("## 다음 단계", 1)
        self.assertNotIn("fa-zeb", participant)
        self.assertIn("09-foundry-agent.md", demo)
        admin = (ROOT / "admin" / "README.md").read_text(encoding="utf-8")
        self.assertIn("참가자별 Foundry 환경은 준비하지 않습니다", admin)
        self.assertIn("시연 계정으로 미리 질문 1개", admin)

    def test_power_bi_prompt_limits_columns_and_specifies_layout(self):
        report = (ROOT / "docs" / "08-power-bi.md").read_text(encoding="utf-8")
        creation = report.split("## 3. Copilot으로 현장 컨트롤 타워 만들기", 1)[1]
        prompt = re.findall(r"``` text\n(.*?)```", creation, re.S)[0]
        self.assertIn("같은 크기의 카드 영역으로 한 줄", prompt)
        self.assertIn("두 표는 좌우로 나누지 말고 각각 페이지 전체 폭", prompt)
        self.assertIn("실제 모델 필드에 연결", prompt)
        site_table = prompt.split("중단 현장 상태:", 1)[1].split("하단 인증 일정:", 1)[0]
        columns = site_table.split("site_status의 ", 1)[1].split("만 이 순서로", 1)[0]
        self.assertEqual(columns.split(", "),
                         ["site_name", "current_version_code", "selfsuff_pct",
                          "primary_energy_kwh_m2y", "forecast_zeb_label",
                          "prelim_zeb_grade", "risk_level", "risk_reason"])
        prompts = re.findall(r"``` text\n(.*?)```", creation.split("## 4.", 1)[0], re.S)
        self.assertEqual(len(prompts), 1)
        self.assertNotIn("개체를 직접 선택해 크기·위치를 조정", creation)
        self.assertNotIn("d08-page2.png", creation)
        boxes = [tuple(map(int, match)) for match in
                 re.findall(r"X=(\d+), Y=(\d+), 너비=(\d+), 높이=(\d+)", prompt)]
        self.assertEqual(len(boxes), 8)
        for index, (x, y, width, height) in enumerate(boxes):
            self.assertGreater(width, 0)
            self.assertGreater(height, 0)
            self.assertTrue(0 <= x < x + width <= 1280)
            self.assertTrue(0 <= y < y + height <= 720)
            for other_x, other_y, other_width, other_height in boxes[index + 1:]:
                self.assertTrue(x + width <= other_x or other_x + other_width <= x
                                or y + height <= other_y or other_y + other_height <= y)
        cards = boxes[1:6]
        self.assertEqual({(y, width, height) for _, y, width, height in cards},
                         {(76, 236, 100)})

    def test_chapters_linked_from_readme(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        for doc in DOCS:
            self.assertIn(f"docs/{doc.name}", readme)

    def test_participant_creates_lakehouse_and_downloads_report_files(self):
        setup = (ROOT / "docs" / "01-workspace.md").read_text(encoding="utf-8")
        self.assertIn("## 3. Lakehouse 직접 만들기", setup)
        self.assertIn("Lakehouse schemas / 스키마 사용을 켠 뒤 Create", setup)
        self.assertNotIn("Notebook 7개 모두", setup)
        self.assertIn("나머지 Notebook 6개는 해당 장에서 사용하기 전에", setup)
        self.assertIn("예상 결과: `01_bronze_public_ingest`에", setup)
        for chapter in ("03-bronze-contoso.md", "04-silver.md", "05-gold.md",
                        "07-data-agent.md", "10-operations-agent.md"):
            text = (ROOT / "docs" / chapter).read_text(encoding="utf-8")
            self.assertIn("본인 `lh_zeb`를 기본 Lakehouse로 연결", text, chapter)
        operations = (ROOT / "docs" / "10-operations-agent.md").read_text(encoding="utf-8")
        self.assertIn("기본 Lakehouse로 연결한 뒤 Run all", operations)
        for path in (ROOT / "README.md", ROOT / "admin" / "README.md",
                     ROOT / "docs" / "01-workspace.md", ROOT / "docs" / "08-power-bi.md"):
            self.assertNotIn("Files/workshop", path.read_text(encoding="utf-8"), path.name)
        report = (ROOT / "docs" / "08-power-bi.md").read_text(encoding="utf-8")
        self.assertIn("../fabric/sm_zeb.tmdl", report)
        self.assertIn("../fabric/zeb-theme.json", report)

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

    def test_imports_only_unbound_notebooks(self):
        for existing_lakehouse in (False, True):
            with self.subTest(existing_lakehouse=existing_lakehouse):
                fab = Mock(dry_run=False)
                items = ([{"type": "Lakehouse", "displayName": "lh_zeb", "id": "lakehouse-id"}]
                         if existing_lakehouse else [])
                fab.get_all.side_effect = [[{"displayName": "ws-p011", "id": "workspace-id"}], items]
                args = SimpleNamespace(prefix="ws-", reference_ontology=False, update_notebooks=False)
                with redirect_stdout(io.StringIO()):
                    self.module.provision(fab, "p011", args, {})
                self.assertEqual(fab.change.call_count, len(NOTEBOOKS))
                for call in fab.change.call_args_list:
                    label, method, url, body = call.args
                    self.assertTrue(label.startswith("import notebook "))
                    self.assertEqual(method, "POST")
                    self.assertEqual(url, "/workspaces/workspace-id/notebooks")
                    payload = body["definition"]["parts"][0]["payload"]
                    imported = json.loads(base64.b64decode(payload))
                    self.assertNotIn("dependencies", imported["metadata"])
                    self.assertNotIn("default_lakehouse", json.dumps(imported))
                fab.call.assert_not_called()

    def test_reference_ontology_requires_participant_lakehouse(self):
        fab = Mock(dry_run=False)
        fab.get_all.side_effect = [[{"displayName": "ws-p011", "id": "workspace-id"}], []]
        args = SimpleNamespace(prefix="ws-", reference_ontology=True, update_notebooks=False)
        with redirect_stdout(io.StringIO()), self.assertRaisesRegex(RuntimeError, "participant-created lh_zeb"):
            self.module.provision(fab, "p011", args, {})
        fab.change.assert_not_called()
        fab.call.assert_not_called()

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
                self.assertEqual(output.getvalue().count("import notebook "), 2 * len(NOTEBOOKS))
                self.assertNotIn("create lakehouse", output.getvalue())


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
