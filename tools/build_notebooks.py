"""Build unbound native Fabric notebooks from reviewed code; never deploy/run."""
import ast
import hashlib
import json
from pathlib import Path
from reference import ROOT

CONFIG = {
    "participant_id": "CHANGE_ME", "scenario_id": "HS-D-VE-20260930",
    "workspace_id": None, "lakehouse_id": None, "approved_target": False,
    "protected_workspace_ids": [], "protected_lakehouse_ids": [],
    "fixture_sha256": None, "serialized_writer_attested": False,
    "platform_approval_binding_verified": False, "configured_creator_actor_id": None,
    "action_binding_evidence_ref": "",
}

PARAMETERS = 'TARGET = ' + repr(CONFIG) + '\n'

GUARD = """# Read-only preflight: no schema/table/File writes before this passes.
import notebookutils
runtime = notebookutils.runtime.context
guard_target(TARGET, runtime.get("currentWorkspaceId"), runtime.get("defaultLakehouseId"))
print("Approved target context matched:", TARGET["participant_id"], TARGET["scenario_id"])
"""

LOAD = """raw = notebookutils.fs.head("Files/workshop/fixtures.json", 1048576)
if hashlib.sha256(raw.encode("utf-8")).hexdigest() != TARGET["fixture_sha256"]:
    raise ValueError("Fixture byte hash mismatch: stop and ask administrator")
data = json.loads(raw)
validate(data)
"""

WRITE = """from pyspark.sql import functions as F
def write_new(df, table):
    # An existing table is an explicit stop, never an automatic reset/overwrite.
    if spark.catalog.tableExists(table):
        raise ValueError("Existing table: inspect it; no implicit reset: " + table)
    df.write.format("delta").mode("errorifexists").saveAsTable(table)
    print(table, spark.table(table).count())
"""

BRONZE = """spark.sql("CREATE SCHEMA IF NOT EXISTS bronze")
for name, fixture in sorted(data.items()):
    columns = [c[0] for c in fixture["schema"]]
    rows = [tuple(None if row[c] is None else
                  ("true" if row[c] is True else "false" if row[c] is False else str(row[c]))
                  for c in columns) for row in fixture["rows"]]
    df = spark.createDataFrame(rows, ", ".join(c + " string" for c in columns))
    df = df.withColumn("_source_kind", F.lit("SYNTHETIC")) \
           .withColumn("_source_sha256", F.lit(TARGET["fixture_sha256"]))
    write_new(df, "bronze." + name)
"""

SILVER = """spark.sql("CREATE SCHEMA IF NOT EXISTS silver")
for name, fixture in sorted(data.items()):
    source = spark.table("bronze." + name)
    columns = []
    for col, dtype in fixture["schema"]:
        cleaned = F.trim(F.col(col))
        expr = F.to_date(cleaned, "yyyy-MM-dd") if dtype == "date" else cleaned.cast(dtype)
        if source.filter(F.col(col).isNotNull() & expr.isNull()).limit(1).count():
            raise ValueError("Quarantine required for invalid cast: " + name + "." + col)
        columns.append(expr.alias(col))
    df = source.select(*columns, "_source_kind", "_source_sha256")
    write_new(df, "silver." + name)
typed = {name: {"schema": fixture["schema"], "rows": [
    {col: (str(row[col]) if dtype == "date" and row[col] is not None else row[col])
     for col, dtype in fixture["schema"]}
    for row in spark.table("silver." + name).collect()]}
    for name, fixture in data.items()}
validate(typed)
assert len(typed["pms_site"]["rows"]) == 8
print("Typed identity checks passed; no intentional dirty source records added.")
"""

GOLD = """spark.sql("CREATE SCHEMA IF NOT EXISTS gold")
typed = {name: {"schema": fixture["schema"], "rows": [
    {col: (str(row[col]) if dtype == "date" and row[col] is not None else row[col])
     for col, dtype in fixture["schema"]}
    for row in spark.table("silver." + name).collect()]}
    for name, fixture in data.items()}
validate(typed)
mapping = {
    "erp_project": "project", "pms_site": "site", "mdm_site_xref": "mdm_site_xref",
    "bim_design_version": "design_version", "pms_cert_target": "cert_target",
    "pms_certificate": "site_certificate", "pms_cert_milestone": "cert_milestone",
    "pms_equipment_plan": "equipment", "scm_vendor": "vendor",
    "scm_purchase_order": "purchase_order", "sim_improvement_option": "improvement_option",
    "ref_zeb_grade_criteria": "grade_criteria",
}
for source, target in mapping.items():
    cols = [c[0] for c in data[source]["schema"]]
    df = spark.table("silver." + source).select(*cols)
    if source == "erp_project":
        alias_rows = []
        for region in typed["ref_region"]["rows"]:
            for alias in set(region["aliases"].split("|") + [region["sido"], region["sido_full"]]):
                alias_rows.append((alias.strip(), region["sido"]))
        alias_df = spark.createDataFrame(alias_rows, "region_alias string, sido string")
        if alias_df.groupBy("region_alias").agg(F.countDistinct("sido").alias("n")).filter("n > 1").count():
            raise ValueError("Ambiguous region aliases")
        df = df.join(alias_df.dropDuplicates(["region_alias"]),
                     F.trim(df.sido_raw) == alias_df.region_alias, "left").drop("region_alias")
        if df.filter(F.col("sido").isNull()).limit(1).count():
            raise ValueError("Unmapped project region")
    write_new(df, "gold." + target)
status = baseline(typed)
status_ddl = (
    "site_code string, project_no string, bim_model_id string, current_version_id string, "
    "design_date string, selfsuff_pct double, primary_energy_kwh_m2y double, current_pv_kw double, "
    "grade_rank int, target_rank int, cert_no string, submitted_version_id string, bems_planned boolean, "
    "bf_gap boolean, risk string, progress_as_of string, criteria_status string, baseline_hash string, event_id string")
status_cols = [x.strip().split()[0] for x in status_ddl.split(",")]
write_new(spark.createDataFrame([tuple(r[c] for c in status_cols) for r in status], status_ddl), "gold.site_status")
options = candidates(typed)
option_ddl = (
    "option_set_id string, site_code string, selfsuff_pct string, primary_energy_kwh_m2y string, grade_rank int, "
    "cost_krw long, parallel_lead_days int, energy_feasible boolean, decision_feasible boolean, "
    "block_reason string, baseline_hash string, event_id string")
cols = [x.strip().split()[0] for x in option_ddl.split(",")]
option_df = spark.createDataFrame([tuple(r[c] for c in cols) for r in options], option_ddl) \
    .withColumn("selfsuff_pct", F.col("selfsuff_pct").cast("decimal(12,4)")) \
    .withColumn("primary_energy_kwh_m2y", F.col("primary_energy_kwh_m2y").cast("decimal(12,4)"))
write_new(option_df, "gold.option_eval")
po = purchase_status(typed)
ddl = "po_no string, site_code string, effective_eta string, installation_deadline string, deadline_breach boolean"
cols = [x.strip().split()[0] for x in ddl.split(",")]
write_new(spark.createDataFrame([tuple(r[c] for c in cols) for r in po], ddl), "gold.po_status")
assert sum(r["deadline_breach"] for r in po) == 0
assert len(status) == 8 and len(options) == 63
display(spark.table("gold.site_status"))
display(spark.table("gold.option_eval").filter("energy_feasible = true").orderBy("cost_krw").limit(5))
"""

SNAPSHOT = """# Explicit manual snapshot, not a streaming/table-sync connection.
# File creation is first-run only; inspect existing file rather than overwriting it.
rows = [r.asDict() for r in spark.table("gold.site_status").filter("risk <> 'normal'").collect()]
option_data = next(r for r in candidates(data) if r["option_set_id"] == "OPT-D5+OPT-D6")
gold_hs_d = [r for r in rows if r["site_code"] == "HS-D"]
if len(gold_hs_d) != 1 or gold_hs_d[0]["baseline_hash"] != option_data["baseline_hash"]:
    raise ValueError("Gold baseline differs from fixture evidence: do not transmit a mixed/stale proposal")
from datetime import datetime, timezone
status_time = datetime.now(timezone.utc).isoformat()
snapshot = "\\n".join(canonical({
    "event_id": r["event_id"], "participant_id": TARGET["participant_id"],
    "scenario_id": TARGET["scenario_id"], "site_code": r["site_code"],
    "baseline_hash": r["baseline_hash"], "risk": r["risk"],
    "progress_as_of": r["progress_as_of"], "event_state": "open", "status_time": status_time,
    "recommended_option_set_id": option_data["option_set_id"] if r["site_code"] == "HS-D" else "",
    "result_hash": digest(option_data) if r["site_code"] == "HS-D" else ""
}) for r in rows) + "\\n"
path = "Files/workshop/operations_snapshot.jsonl"
if notebookutils.fs.exists(path):
    raise ValueError("Snapshot already exists; compare/deduplicate; do not silently replace")
notebookutils.fs.put(path, snapshot, False)
print(snapshot)  # copy exact participant rows into the approved explicit KQL ingestion step
print("Snapshot file only. Eventhouse ingestion and agent start have NOT been performed.")
"""

DECISION_PARAMS = """# Fabric parameter cell: discovered by Operations Add action > Parameters.
# These are evidence identifiers, NOT authorization or approver identity assertions.
event_id = ""
option_set_id = ""
baseline_hash = ""
result_hash = ""
approval_evidence_ref = ""
"""

DECISION = """# Operations Notebook action runs only after Teams Proceed -> Confirm.
# Do NOT execute manually as a substitute for the approved platform flow.
# Notebook parameter strings cannot prove Teams approval or a human approver identity.
if TARGET.get("serialized_writer_attested") is not True:
    raise ValueError("Administrator must establish a single serialized audit writer first")
REQUEST = {
    "participant_id": TARGET["participant_id"], "scenario_id": TARGET["scenario_id"],
    "site_code": "HS-D", "event_id": event_id, "option_set_id": option_set_id,
    "baseline_hash": baseline_hash, "result_hash": result_hash,
    "decision": "record_for_engineering_review", "approval_evidence_ref": approval_evidence_ref
}
typed = {name: {"schema": fixture["schema"], "rows": [
    {col: (str(row[col]) if dtype == "date" and row[col] is not None else row[col])
     for col, dtype in fixture["schema"]}
    for row in spark.table("silver." + name).collect()]}
    for name, fixture in data.items()}
record = decision_record(REQUEST, TARGET, typed)
current = spark.table("gold.site_status").filter(F.col("site_code") == REQUEST["site_code"]).collect()
if len(current) != 1 or current[0]["baseline_hash"] != record["baseline_hash"]:
    raise ValueError("Gold baseline differs from reviewed Silver evidence")
selected = spark.table("gold.option_eval").filter(F.col("option_set_id") == REQUEST["option_set_id"]).collect()
expected = next(r for r in candidates(typed) if r["option_set_id"] == REQUEST["option_set_id"])
if len(selected) != 1:
    raise ValueError("Gold option set missing/ambiguous")
actual_option = selected[0].asDict()
for key, value in expected.items():
    if key in ("selfsuff_pct", "primary_energy_kwh_m2y"):
        if Decimal(str(actual_option[key])) != Decimal(value):
            raise ValueError("Gold result mismatch")
    elif actual_option.get(key) != value:
        raise ValueError("Gold result mismatch: " + key)
spark.sql("CREATE SCHEMA IF NOT EXISTS audit")
ddl = ", ".join(k + " string" for k in record) + ", recorded_at timestamp"
empty = spark.createDataFrame([], ddl)
if not spark.catalog.tableExists("audit.decision_log"):
    empty.write.format("delta").mode("errorifexists").saveAsTable("audit.decision_log")
from delta.tables import DeltaTable
log = DeltaTable.forName(spark, "audit.decision_log")
existing = [r.asDict() for r in spark.table("audit.decision_log")
            .filter(F.col("decision_id") == record["decision_id"]).collect()]
if len(existing) > 1:
    raise ValueError("Duplicate decision key: stop, investigate; no automatic cleanup")
idempotent(existing, record)
incoming = spark.createDataFrame([tuple(record.values())], ", ".join(k + " string" for k in record)) \
    .withColumn("recorded_at", F.current_timestamp())
log.alias("t").merge(incoming.alias("s"), "t.decision_id = s.decision_id") \
    .whenNotMatchedInsertAll().execute()
verified = [r.asDict() for r in spark.table("audit.decision_log")
            .filter(F.col("decision_id") == record["decision_id"]).collect()]
if len(verified) != 1 or verified[0]["payload_hash"] != record["payload_hash"]:
    raise ValueError("Audit readback failed; stop agent and investigate")
display(spark.table("audit.decision_log"))
print("Creator-delegated action invocation recorded; human identity not verified by notebook.")
print("Decision only: design/PO/risk unchanged. Verify audit and Stop the Operations agent.")
"""

PUBLIC = """# REQUIRED public-source segment: run only after genuine bytes + manifest are provisioned.
PUBLIC_SNAPSHOT_APPROVED = False  # set only after administrator snapshot/license review
if PUBLIC_SNAPSHOT_APPROVED is not True:
    raise ValueError("Required public snapshot missing/unapproved: Bronze chapter is incomplete")
import csv, io
with open("/lakehouse/default/Files/workshop/public/15085042/source.csv", "rb") as stream:
    raw_csv = stream.read()
manifest = json.loads(notebookutils.fs.head("Files/workshop/public/15085042/manifest.json", 1048576))
if manifest["dataset_id"] != "15085042" or manifest["snapshot_label"] != "20251231":
    raise ValueError("Unexpected public source/snapshot; rebaseline required")
if hashlib.sha256(raw_csv).hexdigest() != manifest["sha256"] or raw_csv.lstrip().startswith(b"<"):
    raise ValueError("Public source hash/CSV mismatch")
mapping = {
    "인증구분": "cert_stage", "건물용도": "building_use_group", "건물주용도": "building_main_use",
    "에너지자립률": "energy_self_sufficiency", "지역": "region", "건축물명": "building_name",
    "업체명": "applicant_name", "제로에너지건축물 인증등급(ZEB)": "zeb_grade", "인증일자": "cert_date"
}
reader = csv.DictReader(io.StringIO(raw_csv.decode(manifest["encoding"])))
if set(reader.fieldnames) != set(mapping):
    raise ValueError("Public CSV fields changed; inspect and approve mapping, do not guess")
rows = list(reader)
if len(rows) != manifest["rows"]:
    raise ValueError("Public row count differs from retained manifest")
columns = ["source_row_num", *mapping.values(), "_source_dataset_id", "_source_file_sha256"]
records = [tuple([str(i), *[r[c] for c in mapping], "15085042", manifest["sha256"]])
           for i, r in enumerate(rows, 1)]
spark.sql("CREATE SCHEMA IF NOT EXISTS bronze")
write_new(spark.createDataFrame(records, ", ".join(c + " string" for c in columns)), "bronze.pub_zeb_cert")
df = spark.table("bronze.pub_zeb_cert")
date_col = F.to_date(F.regexp_replace(F.trim(F.col("cert_date")), r"[./]", "-"), "yyyy-MM-dd")
if df.filter(date_col.isNull()).limit(1).count():
    raise ValueError("Public date parse error: quarantine before Silver")
spark.sql("CREATE SCHEMA IF NOT EXISTS silver")
write_new(df.withColumn("cert_date", date_col).withColumn("region", F.trim("region")), "silver.pub_zeb_cert")
print("Public ZEB context only: do not join public buildings to synthetic sites by name.")
"""

VERIFY = """# Read-only pre/post-approval verification; NEVER execute the action Notebook manually.
typed = {name: {"schema": fixture["schema"], "rows": [
    {col: (str(row[col]) if dtype == "date" and row[col] is not None else row[col])
     for col, dtype in fixture["schema"]}
    for row in spark.table("silver." + name).collect()]}
    for name, fixture in data.items()}
validate(typed)
reviewed = next(r for r in candidates(typed) if r["option_set_id"] == "OPT-D5+OPT-D6")
print("event_id:", reviewed["event_id"])
print("option_set_id:", reviewed["option_set_id"])
print("baseline_hash:", reviewed["baseline_hash"])
print("result_hash:", digest(reviewed))
display(spark.table("gold.site_status").filter("site_code = 'HS-D'"))
if spark.catalog.tableExists("audit.decision_log"):
    display(spark.table("audit.decision_log"))
else:
    print("No decision log yet: before Teams approval this is expected; after submitted action it is incomplete.")
"""


def library():
    tree = ast.parse((ROOT / "tools" / "reference.py").read_text(encoding="utf-8"))
    nodes = []
    for node in tree.body:
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            nodes.append(node)
        elif isinstance(node, ast.FunctionDef) and node.name != "fixtures":
            nodes.append(node)
        elif isinstance(node, ast.Assign) and all(
                isinstance(t, ast.Name) and t.id != "ROOT" for t in node.targets):
            nodes.append(node)
    return ast.unparse(ast.Module(body=nodes, type_ignores=[])) + "\n"


def build():
    folder = ROOT / "notebooks"
    folder.mkdir(exist_ok=True)
    shared = library()
    stages = [
        ("00_preflight", "Read-only context inspection", []),
        ("01_bronze", "Retained synthetic source → string Bronze", [LOAD, WRITE, BRONZE]),
        ("02_silver", "Type and key mapping; stop on invalid data", [LOAD, WRITE, SILVER]),
        ("03_gold", "Independent provisional training calculations", [LOAD, WRITE, GOLD]),
        ("04_snapshot", "Explicit Operations snapshot only", [LOAD, SNAPSHOT]),
        ("05_decision_log", "Teams-approved Operations action → decision log only", [DECISION_PARAMS, LOAD, WRITE, DECISION]),
        ("06_public_zeb", "Required genuine retained public ZEB snapshot → Bronze/Silver", [WRITE, PUBLIC]),
        ("07_verify_readonly", "Read-only pre/post-approval evidence verification", [LOAD, VERIFY]),
    ]
    for name, title, codes in stages:
        code = [PARAMETERS, shared, GUARD, *codes]
        cells = [{"cell_type": "markdown", "metadata": {}, "source": [
            f"# {title}\n", "UNBOUND TEMPLATE. Administrator must inject a separately approved participant target.\n",
            "No source workspace writes. No legal/engineering certification. No cloud run has been validated.\n"]}]
        for i, value in enumerate(code):
            cells.append({"cell_type": "code", "metadata": {"tags": ["parameters"]} if value == DECISION_PARAMS else {},
                          "source": value.splitlines(keepends=True), "execution_count": None, "outputs": []})
        nb = {"nbformat": 4, "nbformat_minor": 5, "cells": cells,
              "metadata": {"kernel_info": {"name": "synapse_pyspark"},
                           "kernelspec": {"name": "synapse_pyspark", "display_name": "Synapse PySpark", "language": "Python"},
                           "language_info": {"name": "python"},
                           "microsoft": {"language": "python", "language_group": "synapse_pyspark"},
                           "dependencies": {}}}
        (folder / (name + ".ipynb")).write_text(json.dumps(nb, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        (folder / (name + ".py")).write_text("# Fabric notebook source; built from tools/build_notebooks.py\n\n" +
                                            "\n\n# CELL\n".join(code), encoding="utf-8")
    print("8 unbound native PySpark notebook templates; no deployment/run.")


if __name__ == "__main__":
    build()
