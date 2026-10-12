"""Opt-in public-only snapshot fetch; never executed during offline authoring.

Adapts the original Notebook01 data.go.kr flow using Python standard library.
Captcha, missing links, HTML, unexpected headers and small responses fail closed.
"""
import argparse
import csv
import datetime
import hashlib
import http.cookiejar
import io
import json
import re
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = "https://www.data.go.kr"
DATASETS = {
    "15085042": {"name": "ZEB", "label": "20251231", "required": ["인증일자", "건축물명", "에너지자립률"]},
    "15003214": {"name": "GSEED", "label": "20251231", "required": ["인증일자"]},
    "15014781": {"name": "BF", "label": "20260630", "required": []},
    "15054156": {"name": "GreenTech", "label": "20260626", "required": []},
}


def parse_csv(raw, required):
    probe = raw.lstrip().lower()
    if not raw or probe.startswith((b"<", b"{", b"[", b"\x89", b"%pdf")):
        raise ValueError("Not CSV; HTML/captcha/JSON/image/PDF response rejected")
    for encoding in ("utf-8-sig", "cp949"):
        try:
            text = raw.decode(encoding)
            break
        except UnicodeDecodeError:
            continue
    else:
        raise ValueError("Unknown encoding")
    reader = csv.DictReader(io.StringIO(text))
    headers = reader.fieldnames or []
    if len(headers) < 2 or len(set(headers)) != len(headers) or not set(required) <= set(headers):
        raise ValueError("Unexpected/duplicate/missing CSV headers; inspect source change")
    rows = list(reader)
    if len(rows) < 100 or any(None in row for row in rows):
        raise ValueError("Small/malformed snapshot; do not substitute synthetic public data")
    return encoding, headers, rows


def download(dataset_id):
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
    def request(path, form=None, timeout=60):
        payload = urllib.parse.urlencode(form).encode() if form is not None else None
        req = urllib.request.Request(BASE + path, data=payload, headers={
            "User-Agent": "Mozilla/5.0", "Referer": BASE + f"/data/{dataset_id}/fileData.do",
            "X-Requested-With": "XMLHttpRequest"})
        with opener.open(req, timeout=timeout) as response:
            if urllib.parse.urlparse(response.url).hostname != "www.data.go.kr":
                raise ValueError("Unexpected download host; administrator review required")
            return response.read()
    page = request(f"/data/{dataset_id}/fileData.do").decode("utf-8")
    match = re.search(r"fn_fileDataDown\('(\d+)',\s*'([^']+)',\s*'([^']*)',\s*'(\d+)',\s*'(\d+)'\)", page)
    if not match:
        raise ValueError("Portal structure changed/download unavailable; stop")
    info = json.loads(request("/tcs/dss/selectFileDataDownload.do", {
        "publicDataDetailPk": match.group(2), "publicDataPk": dataset_id,
        "atchFileId": "", "fileDetailSn": match.group(4), "publicDataTyCode": "PR0051"}))
    if not info.get("status"):
        raise ValueError("Portal denied download; no policy bypass")
    file_id, sn = info["atchFileId"], info["fileDetailSn"]
    name = info["dataSetFileDetailInfo"]["dataNm"]
    limit = json.loads(request("/cmm/cmm/check-limit.json", {"atchFileId": file_id, "fileDetailSn": sn}))
    if limit.get("needCaptcha"):
        raise ValueError("Captcha/limit encountered; stop, do not automate bypass")
    query = urllib.parse.urlencode({"atchFileId": file_id, "fileDetailSn": sn, "dataNm": name})
    return request("/cmm/cmm/fileDownload.do?" + query, timeout=180), name, file_id


def fetch(dataset_id):
    cfg = DATASETS[dataset_id]
    raw, name, file_id = download(dataset_id)
    encoding, headers, rows = parse_csv(raw, cfg["required"])
    if cfg["label"] not in name:
        raise ValueError("Current portal file differs from approved snapshot label; rebaseline first")
    folder = ROOT / "data" / "public" / "staged" / dataset_id
    if folder.exists():
        raise ValueError("Snapshot directory exists; do not overwrite")
    folder.mkdir(parents=True)
    (folder / "source.csv").write_bytes(raw)
    manifest = {
        "status": "fetched_not_live_validated", "dataset_id": dataset_id,
        "portal_url": BASE + f"/data/{dataset_id}/fileData.do",
        "source_name": name, "source_file_id": file_id, "snapshot_label": cfg["label"],
        "retrieved_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "sha256": hashlib.sha256(raw).hexdigest(), "rows": len(rows),
        "encoding": encoding, "headers": headers,
        "license": "Check current portal terms and attribution before distributing; not relicensed by this kit",
    }
    (folder / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", choices=DATASETS, default="15085042")
    parser.add_argument("--fetch", action="store_true")
    parser.add_argument("--approved-public-source", action="store_true")
    args = parser.parse_args()
    if not (args.fetch and args.approved_public_source):
        print(json.dumps({"status": "unfetched", "dataset": DATASETS[args.dataset]}, ensure_ascii=False, indent=2))
    else:
        print(json.dumps(fetch(args.dataset), ensure_ascii=False, indent=2))
