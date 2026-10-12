"""Offline target preview and definition packaging. No network/provisioning API."""
import argparse
import base64
import hashlib
import json
from pathlib import Path
from reference import ROOT, SCENARIO, guard_target


def prepare(path, write=False, output_folder=None):
    targets = json.loads(Path(path).read_text(encoding="utf-8"))["targets"]
    participants, workspaces, lakehouses = set(), set(), set()
    manifest = {"mode": "offline_prepare_only", "cloud_provisioned": False, "participants": []}
    public_dir = ROOT / "data" / "public" / "staged" / "15085042"
    public_ready = (public_dir / "source.csv").is_file() and (public_dir / "manifest.json").is_file()
    if public_ready:
        public_manifest = json.loads((public_dir / "manifest.json").read_text(encoding="utf-8"))
        public_ready = (public_manifest.get("dataset_id") == "15085042"
                        and public_manifest.get("snapshot_label") == "20251231"
                        and public_manifest.get("sha256") == hashlib.sha256((public_dir / "source.csv").read_bytes()).hexdigest())
    manifest["required_public_zeb"] = "retained_hash_checked_admin_review_required" if public_ready else "blocked_unfetched"
    manifest["live_workshop_ready"] = False
    output_folder = Path(output_folder) if output_folder else ROOT / "deployment" / "prepared"
    if not output_folder.resolve().is_relative_to(ROOT):
        raise ValueError("Offline package output must stay inside this repository")
    for target in targets:
        guard_target(target, target.get("workspace_id"), target.get("lakehouse_id"))
        p = target["participant_id"]
        if target.get("binding_verified") is not True or not target.get("binding_evidence_ref"):
            raise ValueError("Administrator readback evidence of workspace/Lakehouse ownership required")
        if target.get("workspace_name") != f"ws_zeb_{p}" or target.get("lakehouse_name") != f"lh_zeb_{p}":
            raise ValueError("Participant item names do not match")
        for value, seen in ((p, participants), (target["workspace_id"], workspaces),
                            (target["lakehouse_id"], lakehouses)):
            if value in seen:
                raise ValueError("Shared/duplicate participant target prohibited")
            seen.add(value)
        config = {k: target[k] for k in ("participant_id", "scenario_id", "workspace_id", "lakehouse_id",
                                        "approved_target", "serialized_writer_attested",
                                        "protected_workspace_ids", "protected_lakehouse_ids")}
        config.update({k: target.get(k, default) for k, default in (
            ("platform_approval_binding_verified", False), ("configured_creator_actor_id", None),
            ("action_binding_evidence_ref", ""))})
        fixture_path = ROOT / "data" / "synthetic" / "fixtures.json"
        config["fixture_sha256"] = hashlib.sha256(fixture_path.read_bytes()).hexdigest()
        entry = {"participant_id": p, "workspace_id": target["workspace_id"], "lakehouse_id": target["lakehouse_id"],
                 "item_names": [f"ont_zeb_{p}", f"sm_zeb_{p}", f"rpt_zeb_{p}", f"eh_zeb_{p}", f"ops_zeb_{p}"],
                 "files_to_upload": [
                     {"local": "data/synthetic/fixtures.json", "target": "Files/workshop/fixtures.json", "required": True, "status": "packaged"},
                     {"local": "data/public/staged/15085042/source.csv", "target": "Files/workshop/public/15085042/source.csv",
                      "required": True, "status": "retained" if public_ready else "blocked_unfetched"},
                     {"local": "data/public/staged/15085042/manifest.json", "target": "Files/workshop/public/15085042/manifest.json",
                      "required": True, "status": "retained" if public_ready else "blocked_unfetched"}],
                 "notebooks": []}
        for source in sorted((ROOT / "notebooks").glob("*.ipynb")):
            nb = json.loads(source.read_text(encoding="utf-8"))
            nb["cells"][1]["source"] = ("TARGET = " + repr(config) + "\n").splitlines(keepends=True)
            nb["metadata"]["dependencies"] = {"lakehouse": {
                "default_lakehouse": target["lakehouse_id"], "default_lakehouse_name": target["lakehouse_name"],
                "default_lakehouse_workspace_id": target["workspace_id"]}}
            if source.stem == "06_public_zeb" and target.get("public_snapshot_reviewed") is True:
                if not public_ready or not target.get("public_review_evidence_ref"):
                    raise ValueError("Retained hash and explicit public license review evidence required")
                for cell in nb["cells"]:
                    cell["source"] = [
                        line.replace("PUBLIC_SNAPSHOT_APPROVED = False", "PUBLIC_SNAPSHOT_APPROVED = True")
                        for line in cell["source"]]
            payload = (json.dumps(nb, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
            entry["notebooks"].append({"display_name": source.stem + "_" + p,
                                      "sha256": hashlib.sha256(payload).hexdigest()})
            if write:
                destination = output_folder / p
                destination.mkdir(parents=True, exist_ok=True)
                (destination / source.name).write_bytes(payload)
                definition = {"displayName": source.stem + "_" + p, "type": "Notebook",
                              "definition": {"format": "ipynb", "parts": [
                                  {"path": "notebook-content.ipynb", "payloadType": "InlineBase64",
                                   "payload": base64.b64encode(payload).decode("ascii")}]}}
                (destination / (source.stem + ".definition.json")).write_text(
                    json.dumps(definition, indent=2) + "\n", encoding="utf-8")
        manifest["participants"].append(entry)
    if write:
        folder = output_folder
        folder.mkdir(parents=True, exist_ok=True)
        (folder / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("targets")
    parser.add_argument("--prepare", action="store_true")
    parser.add_argument("--approved-offline-bindings", action="store_true")
    args = parser.parse_args()
    if args.prepare and not args.approved_offline_bindings:
        parser.error("Packaging requires explicit --approved-offline-bindings; this never deploys")
    print(json.dumps(prepare(args.targets, args.prepare), indent=2))
