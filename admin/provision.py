"""Prepare participant workspaces for the ZEB workshop (admin only).

For each participant pNNN this creates (or reuses) workspace zeb-pNNN on the given capacity,
a schema-enabled Lakehouse lh_zeb, the 7 notebooks bound to that Lakehouse, and uploads
fabric/sm_zeb.tmdl and fabric/zeb-theme.json to Files/workshop. Existing items are reused;
notebooks are only overwritten with --update-notebooks.

Uses the Azure CLI login (az login [--tenant ...]); no secrets are stored.

Examples
    python admin/provision.py --capacity <capacity-id> --participants p001-p012 --users users.csv
    python admin/provision.py --capacity <capacity-id> --participants p001 --reference-ontology
    python admin/provision.py --capacity <capacity-id> --participants p001-p003 --dry-run

users.csv (optional): participant,upn   e.g.  p001,p001@contoso.com
"""
import argparse
import base64
import csv
import json
import shutil
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
API = "https://api.fabric.microsoft.com/v1"
ONELAKE = "https://onelake.dfs.fabric.microsoft.com"
NOTEBOOKS = ["01_bronze_public_ingest", "02_bronze_contoso_generate", "03_silver_conform", "04_gold_model",
             "05_answers", "06_risk_event", "nb_apply_decision"]
FILES = ["sm_zeb.tmdl", "zeb-theme.json"]
_tokens = {}


def token(resource, tenant):
    if resource not in _tokens or _tokens[resource][1] < time.time() + 300:
        az = shutil.which("az") or "az"
        cmd = [az, "account", "get-access-token", "--resource", resource, "-o", "json"]
        if tenant:
            cmd += ["--tenant", tenant]
        out = json.loads(subprocess.check_output(cmd, shell=False))
        _tokens[resource] = (out["accessToken"], out.get("expires_on") or time.time() + 3000)
    return _tokens[resource][0]


class Fabric:
    def __init__(self, tenant, dry_run):
        self.tenant, self.dry_run = tenant, dry_run

    def call(self, method, url, body=None, raw=None, resource="https://api.fabric.microsoft.com", ctype="application/json"):
        url = url if url.startswith("http") else API + url
        data = raw if raw is not None else (json.dumps(body).encode() if body is not None else None)
        for _ in range(8):
            req = urllib.request.Request(url, method=method, data=data, headers={
                "Authorization": "Bearer " + token(resource, self.tenant), "Content-Type": ctype})
            try:
                with urllib.request.urlopen(req) as r:
                    return r.status, dict(r.headers), r.read()
            except urllib.error.HTTPError as e:
                if e.code == 429:
                    time.sleep(int(e.headers.get("Retry-After", 10)))
                    continue
                return e.code, dict(e.headers), e.read()
        raise RuntimeError(f"Throttled: {method} {url}")

    def lro(self, method, url, body=None):
        status, headers, payload = self.call(method, url, body)
        if status != 202:
            return status, json.loads(payload) if payload else {}
        location = headers.get("Location")
        while True:
            time.sleep(min(int(headers.get("Retry-After", 3) or 3), 10))
            status, headers, payload = self.call("GET", location)
            state = json.loads(payload or b"{}")
            if state.get("status") in ("Succeeded", "Failed", "Undefined", "Cancelled"):
                if state["status"] != "Succeeded":
                    return 500, state
                status, _, payload = self.call("GET", location.rstrip("/") + "/result")
                return 200, json.loads(payload) if payload else state

    def get_all(self, url):
        items = []
        while url:
            status, _, payload = self.call("GET", url)
            data = json.loads(payload)
            if status >= 300:
                raise RuntimeError(f"{status} {data}")
            items += data.get("value", [])
            url = data.get("continuationUri")
        return items

    def change(self, label, method, url, body=None):
        if self.dry_run:
            print(f"  [dry-run] {label}")
            return 200, {"id": "00000000-0000-0000-0000-000000000000"}
        status, result = self.lro(method, url, body)
        if status >= 300:
            raise RuntimeError(f"{label} failed: {status} {json.dumps(result, ensure_ascii=False)[:600]}")
        print(f"  {label}")
        return status, result


def participants(spec):
    result = []
    for part in spec.split(","):
        part = part.strip()
        if "-" in part:
            first, last = part.split("-")
            width = len(first) - 1
            result += [f"p{n:0{width}d}" for n in range(int(first[1:]), int(last[1:]) + 1)]
        elif part:
            result.append(part)
    return result


def definition_parts(folder, replacements):
    parts = []
    for path in sorted(folder.rglob("*")):
        if path.is_file():
            text = path.read_text(encoding="utf-8")
            for key, value in replacements.items():
                text = text.replace(key, value)
            parts.append({"path": path.relative_to(folder).as_posix(),
                          "payload": base64.b64encode(text.encode("utf-8")).decode(), "payloadType": "InlineBase64"})
    return parts


def provision(fab, pid, args, users):
    name = f"{args.prefix}{pid}"
    print(f"{pid}: {name}")
    workspaces = {w["displayName"]: w["id"] for w in fab.get_all("/workspaces")}
    ws = workspaces.get(name)
    if not ws:
        _, created = fab.change("create workspace", "POST", "/workspaces",
                                {"displayName": name, "capacityId": args.capacity, "description": "ZEB hands-on workshop"})
        ws = created["id"]
    else:
        print("  workspace exists")
    if fab.dry_run and ws.startswith("0000"):
        print("  [dry-run] lakehouse lh_zeb, notebooks, files" + (", reference ontology" if args.reference_ontology else ""))
        return

    if pid in users:
        upn = users[pid]
        az = shutil.which("az") or "az"
        oid = subprocess.check_output([az, "ad", "user", "show", "--id", upn, "--query", "id", "-o", "tsv"]).decode().strip()
        roles = fab.get_all(f"/workspaces/{ws}/roleAssignments")
        if not any(r["principal"]["id"] == oid for r in roles):
            fab.change(f"assign {args.role} to {upn}", "POST", f"/workspaces/{ws}/roleAssignments",
                       {"principal": {"id": oid, "type": "User"}, "role": args.role})

    items = {(i["type"], i["displayName"]): i["id"] for i in fab.get_all(f"/workspaces/{ws}/items")}
    lh = items.get(("Lakehouse", "lh_zeb"))
    if not lh:
        _, created = fab.change("create lakehouse lh_zeb (schemas)", "POST", f"/workspaces/{ws}/lakehouses",
                                {"displayName": "lh_zeb", "creationPayload": {"enableSchemas": True}})
        lh = created["id"]

    for nb_name in NOTEBOOKS:
        exists = ("Notebook", nb_name) in items
        if exists and not args.update_notebooks:
            continue
        notebook = json.loads((ROOT / "notebooks" / f"{nb_name}.ipynb").read_text(encoding="utf-8"))
        notebook["metadata"]["dependencies"] = {"lakehouse": {
            "default_lakehouse": lh, "default_lakehouse_name": "lh_zeb", "default_lakehouse_workspace_id": ws}}
        payload = base64.b64encode(json.dumps(notebook, ensure_ascii=False).encode("utf-8")).decode()
        definition = {"format": "ipynb", "parts": [
            {"path": "notebook-content.ipynb", "payload": payload, "payloadType": "InlineBase64"}]}
        if exists:
            fab.change(f"update notebook {nb_name}", "POST",
                       f"/workspaces/{ws}/items/{items[('Notebook', nb_name)]}/updateDefinition", {"definition": definition})
        else:
            fab.change(f"import notebook {nb_name}", "POST", f"/workspaces/{ws}/notebooks",
                       {"displayName": nb_name, "definition": definition})

    storage = "https://storage.azure.com"
    base = f"{ONELAKE}/{ws}/{lh}/Files/workshop"
    if not fab.dry_run:
        fab.call("PUT", base + "?resource=directory", raw=b"", resource=storage)
        for file_name in FILES:
            data = (ROOT / "fabric" / file_name).read_bytes()
            url = f"{base}/{urllib.parse.quote(file_name)}"
            for method, suffix, body, ctype in (("PUT", "?resource=file&overwrite=true", b"", "application/json"),
                                                ("PATCH", "?action=append&position=0", data, "application/octet-stream"),
                                                ("PATCH", f"?action=flush&position={len(data)}", b"", "application/json")):
                status, _, payload = fab.call(method, url + suffix, raw=body, resource=storage, ctype=ctype)
                if status >= 300:
                    raise RuntimeError(f"upload {file_name}: {status} {payload[:300]}")
        print(f"  upload Files/workshop/{', '.join(FILES)}")

    if args.reference_ontology:
        if ("Ontology", "ont_zeb") in items:
            print("  ont_zeb exists; reference ontology not deployed")
        else:
            parts = definition_parts(ROOT / "fabric" / "ont_zeb_reference", {"{{WORKSPACE_ID}}": ws, "{{LAKEHOUSE_ID}}": lh})
            fab.change("deploy reference ontology ont_zeb", "POST", f"/workspaces/{ws}/items",
                       {"displayName": "ont_zeb", "type": "Ontology", "definition": {"parts": parts}})


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--capacity", required=True, help="Fabric capacity ID for new workspaces")
    parser.add_argument("--participants", required=True, help="e.g. p001-p012 or p001,p005")
    parser.add_argument("--users", help="CSV with participant,upn to grant workspace access")
    parser.add_argument("--role", default="Contributor", choices=["Admin", "Member", "Contributor"])
    parser.add_argument("--prefix", default="zeb-", help="workspace name prefix (default zeb-)")
    parser.add_argument("--tenant", help="tenant for az get-access-token")
    parser.add_argument("--update-notebooks", action="store_true", help="overwrite existing notebooks")
    parser.add_argument("--reference-ontology", action="store_true",
                        help="deploy the reference ontology as ont_zeb (fallback for chapter 06)")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    users = {}
    if args.users:
        with open(args.users, encoding="utf-8-sig") as f:
            users = {row["participant"].strip(): row["upn"].strip() for row in csv.DictReader(f)}
    fab = Fabric(args.tenant, args.dry_run)
    for pid in participants(args.participants):
        provision(fab, pid, args, users)


if __name__ == "__main__":
    main()
