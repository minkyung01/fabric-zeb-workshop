# Fabric notebook source; built from tools/build_notebooks.py

TARGET = {'participant_id': 'CHANGE_ME', 'scenario_id': 'HS-D-VE-20260930', 'workspace_id': None, 'lakehouse_id': None, 'approved_target': False, 'protected_workspace_ids': [], 'protected_lakehouse_ids': [], 'fixture_sha256': None, 'serialized_writer_attested': False, 'platform_approval_binding_verified': False, 'configured_creator_actor_id': None, 'action_binding_evidence_ref': ''}


# CELL
import hashlib
import itertools
import json
import re
import uuid
from decimal import Decimal
from pathlib import Path
AS_OF = '2026-09-30'
SCENARIO = 'HS-D-VE-20260930'

def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), default=str)

def digest(value):
    return hashlib.sha256(canonical(value).encode('utf-8')).hexdigest()

def guard_target(config, actual_workspace, actual_lakehouse):
    for name, protected_key, actual in (('workspace_id', 'protected_workspace_ids', actual_workspace), ('lakehouse_id', 'protected_lakehouse_ids', actual_lakehouse)):
        protected = config.get(protected_key)
        if not isinstance(protected, list) or not protected:
            raise ValueError(f'Missing administrator protected source list: {protected_key}')
        if any((not isinstance(value, str) for value in protected)):
            raise ValueError(f'Invalid protected source list: {protected_key}')
        forbidden = {str(uuid.UUID(value)) for value in protected}
        if str(uuid.UUID(int=0)) in forbidden:
            raise ValueError(f'Placeholder protected source list: {protected_key}')
        expected = config.get(name)
        if not isinstance(expected, str):
            raise ValueError(f'Missing resolved {name}')
        parsed = str(uuid.UUID(expected))
        if parsed in forbidden or parsed == str(uuid.UUID(int=0)):
            raise ValueError(f'Protected or placeholder {name}')
        if parsed != actual:
            raise ValueError(f'Runtime {name} does not match approved target')
    if not re.fullmatch('p(?:0[1-9]|1[0-2])', config.get('participant_id', '')):
        raise ValueError('Participant must be p01..p12')
    if config.get('scenario_id') != SCENARIO or config.get('approved_target') is not True:
        raise ValueError('Unapproved scenario/target')
    return True

def grade(ss, pe, residential, criteria):
    ss, pe = (Decimal(str(ss)), Decimal(str(pe)))
    if not ss.is_finite() or not pe.is_finite():
        raise ValueError('Nonfinite energy input')
    ranks = []
    key = 'primary_energy_limit_residential' if residential else 'primary_energy_limit_nonresidential'
    for row in criteria:
        rank = 0 if row['grade_code'] == '+' else int(row['grade_code'])
        if ss >= Decimal(str(row['selfsuff_min_pct'])) or pe < Decimal(str(row[key])):
            ranks.append(rank)
    return min(ranks, default=6)

def validate(data):
    keys = {'erp_project': 'project_no', 'pms_site': 'site_code', 'mdm_site_xref': 'site_code', 'bim_design_version': 'version_id', 'pms_cert_target': 'target_id', 'pms_certificate': 'cert_no', 'pms_cert_milestone': 'milestone_id', 'pms_equipment_plan': 'wbs_code', 'scm_vendor': 'vendor_code', 'scm_purchase_order': 'po_no', 'scm_po_event': 'event_id', 'sim_improvement_option': 'option_id'}
    for table, key in keys.items():
        values = [row[key] for row in data[table]['rows']]
        if any((not value for value in values)) or len(set(values)) != len(values):
            raise ValueError(f'Duplicate/null key: {table}.{key}')

    def link(child, field, parent, key):
        parents = {r[key] for r in data[parent]['rows']}
        if any((r[field] not in parents for r in data[child]['rows'])):
            raise ValueError(f'Orphan: {child}.{field}')
    for args in (('mdm_site_xref', 'project_no', 'erp_project', 'project_no'), ('mdm_site_xref', 'site_code', 'pms_site', 'site_code'), ('bim_design_version', 'bim_model_id', 'mdm_site_xref', 'bim_model_id'), ('pms_certificate', 'design_version_id', 'bim_design_version', 'version_id'), ('pms_equipment_plan', 'design_version_id', 'bim_design_version', 'version_id'), ('scm_purchase_order', 'wbs_element', 'pms_equipment_plan', 'wbs_code'), ('scm_purchase_order', 'vendor_code', 'scm_vendor', 'vendor_code'), ('scm_po_event', 'po_no', 'scm_purchase_order', 'po_no')):
        link(*args)
    for table in ('pms_cert_target', 'pms_certificate', 'pms_cert_milestone', 'pms_equipment_plan', 'sim_improvement_option'):
        link(table, 'site_code', 'pms_site', 'site_code')
    for field in ('site_code', 'project_no', 'bim_model_id'):
        vals = [r[field] for r in data['mdm_site_xref']['rows']]
        if len(set(vals)) != len(vals):
            raise ValueError('Ambiguous MDM identity')
    for m in data['mdm_site_xref']['rows']:
        current = [r for r in data['bim_design_version']['rows'] if r['bim_model_id'] == m['bim_model_id'] and r['version_status'] == '현행']
        if len(current) != 1:
            raise ValueError('Expected exactly one current design per site')
    designs = {r['version_id']: r for r in data['bim_design_version']['rows']}
    mdm = {r['site_code']: r['bim_model_id'] for r in data['mdm_site_xref']['rows']}
    for c in data['pms_certificate']['rows']:
        if designs[c['design_version_id']]['bim_model_id'] != mdm[c['site_code']]:
            raise ValueError("Certificate references another site's design")
    return True

def baseline(data):
    validate(data)
    projects = {r['project_no']: r for r in data['erp_project']['rows']}
    result = []
    criteria = data['ref_zeb_grade_criteria']['rows']
    for m in data['mdm_site_xref']['rows']:
        s = m['site_code']
        p = projects[m['project_no']]
        current = next((r for r in data['bim_design_version']['rows'] if r['bim_model_id'] == m['bim_model_id'] and r['version_status'] == '현행'))
        target = next((r for r in data['pms_cert_target']['rows'] if r['site_code'] == s and r['cert_type'] == 'ZEB'))
        rank = grade(current['selfsuff_pct'], current['primary_energy_kwh_m2y'], p['main_use'] == '공동주택', criteria)
        certs = [r for r in data['pms_certificate']['rows'] if r['site_code'] == s and r['cert_type'] == 'ZEB']
        cert = max(certs, key=lambda r: r['cert_date']) if certs else None
        bems = any((r['site_code'] == s and r['category_code'] == 'BEMS' for r in data['pms_equipment_plan']['rows']))
        bf_gap = any((t['site_code'] == s and t['cert_type'] == 'BF' and (t['target_grade'] == '최우수') and any((c['site_code'] == s and c['cert_type'] == 'BF' and (c['grade'] == '우수') for c in data['pms_certificate']['rows'])) for t in data['pms_cert_target']['rows']))
        risk = 'danger' if cert and rank > int(cert['grade']) else 'caution' if rank > int(target['target_grade']) or not bems or bf_gap else 'normal'
        row = {'site_code': s, 'project_no': p['project_no'], 'bim_model_id': m['bim_model_id'], 'current_version_id': current['version_id'], 'design_date': current['version_date'], 'selfsuff_pct': current['selfsuff_pct'], 'primary_energy_kwh_m2y': current['primary_energy_kwh_m2y'], 'current_pv_kw': current['pv_kw'], 'grade_rank': rank, 'target_rank': int(target['target_grade']), 'cert_no': cert['cert_no'] if cert else None, 'submitted_version_id': cert['design_version_id'] if cert else None, 'bems_planned': bems, 'bf_gap': bf_gap, 'risk': risk, 'progress_as_of': AS_OF, 'criteria_status': 'PROVISIONAL_TRAINING_NOT_LEGAL'}
        row['baseline_hash'] = digest(row)
        row['event_id'] = digest({'scenario': SCENARIO, 'site': s, 'baseline': row['baseline_hash']})
        result.append(row)
    return result

def candidates(data, site='HS-D'):
    b = next((r for r in baseline(data) if r['site_code'] == site))
    options = sorted([r for r in data['sim_improvement_option']['rows'] if r['site_code'] == site], key=lambda r: r['option_id'])
    residential = next((r for r in data['erp_project']['rows'] if r['project_no'] == b['project_no']))['main_use'] == '공동주택'
    result = []
    for size in range(1, len(options) + 1):
        for combo in itertools.combinations(options, size):
            ss = Decimal(str(b['selfsuff_pct'])) + sum((Decimal(str(r['selfsuff_gain_pp'])) for r in combo), Decimal(0))
            pe = Decimal(str(b['primary_energy_kwh_m2y'])) + sum((Decimal(str(r['primary_energy_delta'])) for r in combo), Decimal(0))
            rank = grade(ss, pe, residential, data['ref_zeb_grade_criteria']['rows'])
            result.append({'option_set_id': '+'.join((r['option_id'] for r in combo)), 'site_code': site, 'selfsuff_pct': str(ss), 'primary_energy_kwh_m2y': str(pe), 'grade_rank': rank, 'cost_krw': sum((r['cost_krw'] for r in combo)), 'parallel_lead_days': max((r['lead_time_days'] for r in combo)), 'energy_feasible': rank <= b['target_rank'], 'decision_feasible': False, 'block_reason': 'INTERACTION_EXCLUSIVITY_AND_SCHEDULE_UNVERIFIED', 'baseline_hash': b['baseline_hash'], 'event_id': b['event_id']})
    return sorted(result, key=lambda r: (r['cost_krw'], r['option_set_id']))

def purchase_status(data):
    equipment = {r['wbs_code']: r for r in data['pms_equipment_plan']['rows']}
    result = []
    for po in data['scm_purchase_order']['rows']:
        site = equipment[po['wbs_element']]['site_code']
        deadline = next((r['planned_date'] for r in data['pms_cert_milestone']['rows'] if r['site_code'] == site and r['milestone_type'] == '설비 설치 완료'))
        events = sorted([r for r in data['scm_po_event']['rows'] if r['po_no'] == po['po_no']], key=lambda r: (r['event_time'], r['event_id']))
        eta = next((r['new_expected_date'] for r in reversed(events) if r['new_expected_date']), po['expected_date'])
        actual_or_eta = po['delivered_date'] or eta
        result.append({'po_no': po['po_no'], 'site_code': site, 'effective_eta': actual_or_eta, 'installation_deadline': deadline, 'deadline_breach': actual_or_eta > deadline})
    return result

def decision_record(request, config, data):
    guard_target(config, config.get('workspace_id'), config.get('lakehouse_id'))
    if config.get('platform_approval_binding_verified') is not True or not config.get('action_binding_evidence_ref'):
        raise ValueError('Administrator-verified Operations approval action binding required')
    creator = config.get('configured_creator_actor_id')
    if not creator or str(uuid.UUID(creator)) == str(uuid.UUID(int=0)):
        raise ValueError('Configured delegated creator ID required; not a verified human approver')
    if any((k in request for k in ('human_approved', 'approved_by', 'identity_mode'))):
        raise ValueError('Client approval/identity flags are not authorization evidence')
    if request.get('participant_id') != config['participant_id'] or request.get('scenario_id') != SCENARIO:
        raise ValueError('Participant/scenario mismatch')
    if request.get('decision') != 'record_for_engineering_review':
        raise ValueError('Only review decisions may be logged; physical actions prohibited')
    evidence = request.get('approval_evidence_ref', '')
    if not isinstance(evidence, str) or len(evidence) > 2048:
        raise ValueError('Approval evidence reference must be a bounded string')
    evaluated = candidates(data)
    match = next((r for r in evaluated if r['option_set_id'] == request.get('option_set_id')), None)
    if match is None or request.get('site_code') != match['site_code']:
        raise ValueError('Unknown option set/site')
    recommended = next((r for r in evaluated if r['energy_feasible']))
    if match['option_set_id'] != recommended['option_set_id']:
        raise ValueError("Confirmed option differs from this event's independently computed recommendation")
    for key in ('baseline_hash', 'event_id'):
        if request.get(key) != match[key]:
            raise ValueError(f'Stale or incorrect {key}')
    if request.get('result_hash') != digest(match) or not match['energy_feasible']:
        raise ValueError('Unreviewed result or energy-infeasible option set')
    record = {key: request[key] for key in ('participant_id', 'scenario_id', 'site_code', 'event_id', 'option_set_id', 'baseline_hash', 'result_hash', 'decision')}
    record['approval_evidence_ref'] = evidence
    record['approval_evidence_status'] = 'externally_supplied_not_verified' if evidence else 'not_supplied_by_platform'
    record['approval_provenance'] = 'operations_action_creator_delegated_platform_confirmation_required'
    record['configured_creator_actor_id'] = creator
    record['execution_principal_verification'] = 'configured_creator_not_verified_in_notebook'
    record['invocation_route_verification'] = 'notebook_cannot_verify_platform_origin'
    record['human_approver_identity'] = 'not_supplied_or_verified'
    record['action_binding_evidence_ref'] = config['action_binding_evidence_ref']
    record['decision_id'] = digest({k: record[k] for k in ('participant_id', 'scenario_id', 'event_id')})
    record['payload_hash'] = digest(record)
    return record

def idempotent(existing, record):
    found = next((r for r in existing if r['decision_id'] == record['decision_id']), None)
    if found and found['payload_hash'] != record['payload_hash']:
        raise ValueError('Conflicting decision payload: preserve existing audit record')
    return list(existing) if found else [*existing, record]


# CELL
# Read-only preflight: no schema/table/File writes before this passes.
import notebookutils
runtime = notebookutils.runtime.context
guard_target(TARGET, runtime.get("currentWorkspaceId"), runtime.get("defaultLakehouseId"))
print("Approved target context matched:", TARGET["participant_id"], TARGET["scenario_id"])


# CELL
from pyspark.sql import functions as F
def write_new(df, table):
    # An existing table is an explicit stop, never an automatic reset/overwrite.
    if spark.catalog.tableExists(table):
        raise ValueError("Existing table: inspect it; no implicit reset: " + table)
    df.write.format("delta").mode("errorifexists").saveAsTable(table)
    print(table, spark.table(table).count())


# CELL
# REQUIRED public-source segment: run only after genuine bytes + manifest are provisioned.
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
