"""Generate a scoped browser deployment script; no tokens or network operations."""
import argparse
import json
from pathlib import Path

from reference import ROOT, guard_target


def build(names):
    target = json.loads((ROOT / "config" / "targets.json").read_text(encoding="utf-8"))["targets"]
    if len(target) != 1 or target[0]["participant_id"] != "p01":
        raise ValueError("This rehearsal helper accepts only the approved p01 target")
    guard_target(target[0], target[0]["workspace_id"], target[0]["lakehouse_id"])
    if target[0].get("binding_verified") is not True or not target[0].get("binding_evidence_ref"):
        raise ValueError("Persisted target readback is required")
    workspace = target[0]["workspace_id"]
    definitions = [
        json.loads((ROOT / "deployment" / "prepared" / "p01" / (name + ".definition.json")).read_text(encoding="utf-8"))
        for name in names
    ]
    script = """async (page) => {
const definitions = __DEFINITIONS__;
const ws = __WORKSPACE__;
const pending = page.waitForRequest(r => r.url().includes('analysis.windows.net') && !!r.headers()['authorization'], {timeout:30000});
await page.reload();
const headers = {Authorization:(await pending).headers()['authorization'], 'x-ms-fabric-skill':'spark-cli'};
const base = 'https://api.fabric.microsoft.com/v1/workspaces/' + ws;
const inventory = await page.request.get(base + '/items', {headers});
if (!inventory.ok()) return {error:'inventory',status:inventory.status()};
const items = (await inventory.json()).value;
const results = [];
for (const definition of definitions) {
  const existing = items.filter(i => i.displayName === definition.displayName && i.type === 'Notebook');
  if (existing.length) { results.push({name:definition.displayName,state:'existing_not_updated',id:existing[0].id}); continue; }
  const r = await page.request.post(base + '/items', {headers,data:definition});
  const body = await r.text();
  results.push({name:definition.displayName,status:r.status(),location:r.headers()['location'],body:body ? JSON.parse(body) : null});
  if (![201,202].includes(r.status())) break;
}
return results;
}"""
    script = script.replace("__DEFINITIONS__", json.dumps(definitions)).replace("__WORKSPACE__", json.dumps(workspace))
    output = ROOT / "deployment" / "prepared" / "browser-deploy.js"
    output.write_text(script, encoding="utf-8")
    print(f"Prepared {len(definitions)} definitions in {output.relative_to(ROOT)}; no cloud calls made.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("names", nargs="+", choices=[
        "00_preflight", "01_bronze", "02_silver", "03_gold", "04_snapshot",
        "05_decision_log", "06_public_zeb", "07_verify_readonly"])
    build(parser.parse_args().names)
