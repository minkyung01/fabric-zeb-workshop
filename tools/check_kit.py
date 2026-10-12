"""Docs, notebook parity and evidence-backed local/live status checks."""
import ast
import hashlib
import json
import re
from pathlib import Path
from reference import ROOT


def public_files():
    folders = {"admin", "assets", "config", "data", "deployment", "docs", "notebooks",
               "ontology", "operations", "semantic_model", "sql", "tests", "tools", "validation"}
    excluded = (ROOT / "deployment" / "prepared", ROOT / "data" / "public" / "staged",
                ROOT / "assets" / "private-captures")
    private = {ROOT / "config" / "targets.json", ROOT / "validation" / "rehearsal-p01.json"}
    return [p for p in sorted(ROOT.rglob("*")) if p.is_file()
            and (p.relative_to(ROOT).parts[0] in folders
                 or p.relative_to(ROOT).as_posix() in {".gitattributes", ".gitignore", "README.md"})
            and p not in private and p.suffix != ".pyc" and "__pycache__" not in p.parts
            and not any(p.is_relative_to(folder) for folder in excluded)]


def validate_public_evidence(evidence, status):
    if evidence.get("public_redacted") is not True:
        raise ValueError("Public live evidence must explicitly declare redaction")
    target = evidence.get("target_readback", {})
    if target.get("http_status") != 200 or target.get("owned_target_verified") is not True:
        raise ValueError("Live target ownership readback missing")
    completed = [r for r in evidence.get("runs", []) if r.get("status") == "Completed"]
    if (len(completed) != evidence.get("completed_cloud_notebook_jobs")
            or len(completed) != status["completed_cloud_notebook_jobs"]):
        raise ValueError("Completed stage count differs from persisted live status")
    required = {"00_preflight", "01_bronze", "02_silver", "03_gold", "04_snapshot",
                "06_public_zeb", "07_verify_readonly"}
    if not required.issubset({r.get("stage") for r in completed}):
        raise ValueError("Required completed rehearsal stage missing")
    if status["capacity"] == "paused" and evidence.get("capacity_end_state") != "Paused":
        raise ValueError("Paused status requires capacity end-state readback")
    if evidence.get("decision_notebook_jobs") != status["decision_notebook_jobs"]:
        raise ValueError("Decision writer count differs from persisted live status")
    if evidence.get("agent_should_run_at_end") != status["current_agent_shouldRun"]:
        raise ValueError("Agent end-state differs from persisted live status")
    expected_counts = {
        "public_zeb_bronze": 9760, "public_zeb_silver": 9760,
        "gold_sites": 8, "gold_option_sets": 63, "gold_purchase_orders": 25,
        "installation_breaches": 0, "risk_sites": 4, "danger_sites": 1,
        "ontology_entities": 10, "ontology_relationships": 10,
        "direct_lake_tables": 4, "direct_lake_partitions": 4, "model_relationships": 3,
        "initial_model_measures": 10, "final_model_measures": 11, "saved_report_pages": 2,
        "eventhouse_latest_rows": 4, "eventhouse_append_history_rows": 16,
        "eventhouse_schema_columns": 11, "action_string_parameters": 5,
    }
    if evidence.get("counts") != expected_counts:
        raise ValueError("Public summary counts differ from retained rehearsal checkpoint")
    if (evidence.get("stages", {}).get("human_proceed_confirm") != "not_performed"
            or evidence["stages"].get("creator_delegated_decision_action") != "not_run"
            or status["actual_human_Proceed_Confirm"] is not False):
        raise ValueError("Summary must not imply unperformed human approval or action")
    if re.search(r"[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}|[0-9a-f]{64}|https?://|@",
                 json.dumps(evidence), re.I):
        raise ValueError("Public summary contains an identifier, hash, URL or account")


def verify_private_evidence_if_present(summary):
    path = ROOT / "validation" / "rehearsal-p01.json"
    if not path.exists():
        return
    raw = json.loads(path.read_text(encoding="utf-8"))
    notification = raw["notification_phase_20261012"]
    initial = [r for r in raw["runs"] if r.get("status") == "Completed" and r.get("job_id")]
    refreshes = [notification["refresh_notebook"]["status"], notification["second_refresh"]["status"],
                 notification["third_refresh_and_mapping_repair"]["job_status"]]
    outcome = notification["bounded_monitoring_outcome"]
    if (len(initial) + refreshes.count("Completed") != summary["completed_cloud_notebook_jobs"]
            or raw["capacity_end_state"] != summary["capacity_end_state"]
            or outcome["decision_notebook_job_history"] != summary["decision_notebook_jobs"]
            or outcome["stop_public_shouldRun"] != summary["agent_should_run_at_end"]
            or outcome["human_Proceed_Confirm"] is not False
            or outcome["p01_proposal_card_observed"] is not False):
        raise ValueError("Public summary differs from optional retained private readbacks")


def check():
    errors = []
    headings = ["업무 목적", "시작 전 준비", "실행 순서", "확인할 결과", "완료 기준", "다음 단계"]
    chapters = sorted(p for p in (ROOT / "docs").glob("*.md") if re.match(r"\d\d-", p.name))
    if len(chapters) != 12:
        errors.append("Expected 12 learner chapters")
    files = public_files()
    for path in (p for p in files if p.suffix == ".md"):
        text = path.read_text(encoding="utf-8")
        if path in chapters:
            actual = re.findall(r"^## (.+)$", text, re.M)
            if actual != headings:
                errors.append(f"{path.name}: learner flow headings differ")
        for target in re.findall(r"\]\(([^)]+)\)", text):
            if target.startswith(("https://", "http://", "#")):
                continue
            target = target.split("#")[0]
            resolved = (path.parent / target).resolve()
            generated_inventory = ROOT / "validation" / "artifacts.json"
            if target and resolved != generated_inventory and resolved not in files:
                errors.append(f"{path.relative_to(ROOT)}: broken local link {target}")
    for path in (ROOT / "notebooks").glob("*.ipynb"):
        nb = json.loads(path.read_text(encoding="utf-8"))
        code = ["".join(c["source"]) for c in nb["cells"] if c["cell_type"] == "code"]
        py = path.with_suffix(".py").read_text(encoding="utf-8")
        expected = "# Fabric notebook source; built from tools/build_notebooks.py\n\n" + "\n\n# CELL\n".join(code)
        if py != expected:
            errors.append(f"{path.name}: .py/.ipynb parity failure")
        ast.parse(py)
        if nb["metadata"].get("dependencies") != {}:
            errors.append(f"{path.name}: template must be unbound")
    status = json.loads((ROOT / "validation" / "status.json").read_text(encoding="utf-8"))
    if status["phase"] == "offline_kit_authoring":
        if status["screenshots"] or status["cloud_notebooks_run"] or status["cloud_items_created"]:
            errors.append("Offline status falsely claims live evidence")
    else:
        evidence_path = ROOT / "validation" / "rehearsal-summary.json"
        if not evidence_path.exists():
            errors.append("Live status requires persisted public redacted rehearsal summary")
        else:
            evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
            try:
                validate_public_evidence(evidence, status)
                verify_private_evidence_if_present(evidence)
            except ValueError as exc:
                errors.append(str(exc))
        for capture in status["screenshots"]:
            if not (ROOT / capture).is_file() or not capture.startswith("assets/screenshots/"):
                errors.append("Missing genuine rehearsal screenshot: " + capture)
    if status["source_workspace_modified"] or status["permissions_changed"]:
        errors.append("Protected source or permissions changed")
    if status["foundry"] != "optional_not_run":
        errors.append("Optional Foundry state drift")
    for path in (p for p in files if p.suffix == ".json"):
        json.loads(path.read_text(encoding="utf-8"))
    if errors:
        raise SystemExit("\n".join(errors))
    inventory = ROOT / "validation" / "artifacts.json"
    files = [p for p in files if p != inventory]
    inventory.write_text(json.dumps({
        "kind": "public_kit_and_redacted_evidence_inventory",
        "file_count_excluding_this_inventory": len(files),
        "files": [{"path": p.relative_to(ROOT).as_posix(), "bytes": p.stat().st_size,
                   "sha256": hashlib.sha256(p.read_bytes()).hexdigest()} for p in files]
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"PASS: {len(chapters)} chapter flows, local links/images, 8 notebook parity/syntax, JSON and evidence-backed status.")


if __name__ == "__main__":
    check()
