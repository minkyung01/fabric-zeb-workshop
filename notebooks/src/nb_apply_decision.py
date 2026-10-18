# %% [markdown]
# # 보완안 승인 반영
#
# 담당자가 Operations agent의 Teams 제안을 승인(**Proceed** → **Confirm**)하면 이 Notebook이 실행됩니다. **직접 실행하지 않습니다.**
#
# 1. 위험 이벤트와 추천 보완안이 맞는지 확인합니다.
# 2. 공사관리(PMS) 조치 기록 `bronze.pms_action_log`에 `apply_options` 1행을 추가하고, Eventhouse에 `approved` 상태를 기록합니다.
# 3. Silver·Gold Notebook을 다시 실행합니다. Silver가 조치 기록을 읽어 **보완안을 반영한 새 설계안**을 만들고, Gold가 예상 등급을 다시 계산합니다.
# 4. 현장이 더 이상 위험하지 않으면 Eventhouse와 `ops.risk_event`에 `resolved` 상태를 기록합니다.
#
# 실습 데이터의 설계안과 등급만 다시 계산하며, 실제 설계 변경이나 발주는 하지 않습니다.

# %% [parameters]
event_id = "ZEB-HS-D-20260930"
option_id = "OPT-D2"

# %% [markdown]
# ## 1. 위험 이벤트와 보완안 확인
#
# **예상 결과:** 1행이 나옵니다. `ZEB-HS-D-20260930`, `HS-D`, 추천안 `OPT-D2`, 상태 `open`입니다.

# %%
from datetime import datetime, timezone
import json
from pyspark.sql import functions as F

event = spark.table("ops.risk_event").where(F.col("event_id") == event_id)
display(event.select("event_id", "site_code", "site_name", "forecast_grade", "prelim_grade", "recommended_option_id", "option_cost_krw", "status"))
found = event.take(2)
if len(found) != 1:
    raise ValueError(f"{event_id} 위험 이벤트가 정확히 1행이어야 합니다. 조회 행 수: {len(found)}")
ev = found[0]
if option_id != ev.recommended_option_id:
    raise ValueError(f"option_id={option_id!r}가 이벤트의 추천 보완안 {ev.recommended_option_id!r}와 다릅니다.")
option = (spark.table("ops.option_eval")
          .where((F.col("site_code") == ev.site_code) & (F.col("option_id") == option_id) & F.col("feasible")).take(1))
if not option:
    raise ValueError(f"{option_id}는 {ev.site_code}의 기준 충족 보완안이어야 합니다.")
if ev.status not in ("open", "approved"):
    raise ValueError(f"{event_id}의 상태 {ev.status!r}에서는 승인을 반영할 수 없습니다.")

# %% [markdown]
# ## 2. 조치 기록과 승인 상태 남기기
#
# 같은 이벤트의 조치 기록이 이미 있으면 다시 추가하지 않습니다. 승인자로는 Operations agent를 만든 사람(조치를 실행한 계정)이 기록됩니다.
#
# **예상 결과:** `ACT-ZEB-HS-D-20260930: 조치 기록 추가`, `ZEB-HS-D-20260930: ZebRiskEvent에 approved 추가`

# %%
import pandas as pd
import requests
import sempy.fabric as fabric

EVENTHOUSE = "eh_zeb"
action_id = f"ACT-{event_id}"
try:
    approver = notebookutils.runtime.context.get("userName") or "담당자"
except Exception:
    approver = "담당자"

if spark.table("bronze.pms_action_log").where(F.col("action_id") == action_id).count() == 0:
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    detail = json.dumps({"option_ids": [option_id], "event_id": event_id}, ensure_ascii=False)
    (spark.createDataFrame([(action_id, now.strftime("%Y-%m-%d %H:%M:%S"), ev.site_code, "apply_options", detail,
                             f"{approver} (Teams 승인)", "Operations agent")],
                           "action_id string, action_time string, site_code string, action_type string, detail_json string, "
                           "approved_by string, source_system string")
          .withColumn("_source", F.lit("Operations agent 승인"))
          .withColumn("_generated_at", F.current_timestamp())
          .write.mode("append").saveAsTable("bronze.pms_action_log"))
    print(f"{action_id}: 조치 기록 추가")
else:
    print(f"{action_id}: 조치 기록이 이미 있어 추가하지 않았습니다.")

workspace_id = fabric.get_workspace_id()
eventhouses = fabric.FabricRestClient().get(f"v1/workspaces/{workspace_id}/eventhouses").json()["value"]
matches = [e for e in eventhouses if e["displayName"] == EVENTHOUSE]
if len(matches) != 1:
    raise ValueError(f"현재 작업 영역에 {EVENTHOUSE} Eventhouse가 정확히 1개 있어야 합니다.")
kusto_uri = matches[0]["properties"]["queryServiceUri"]
headers = {"Authorization": "Bearer " + notebookutils.credentials.getToken("kusto")}


def kql_text(value):
    return "'" + str(value).replace("\\", "\\\\").replace("'", "\\'") + "'" if value is not None else "''"


def kusto(endpoint, command):
    response = requests.post(f"{kusto_uri}/v1/rest/{endpoint}", headers=headers,
                             json={"db": EVENTHOUSE, "csl": command}, timeout=60)
    response.raise_for_status()
    result = response.json()
    if result.get("Exceptions"):
        raise RuntimeError(f"Kusto 요청 실패: {result['Exceptions']}")
    table = result["Tables"][0]
    return pd.DataFrame(table["Rows"], columns=[c["ColumnName"] for c in table["Columns"]])


def send(status, forecast_grade, selfsuff_pct):
    kusto("mgmt", f""".set-or-append ZebRiskEvent <|
print event_id = {kql_text(ev.event_id)}, status_time = now(), event_status = {kql_text(status)},
      site_code = {kql_text(ev.site_code)}, site_name = {kql_text(ev.site_name)}, risk_reason = {kql_text(ev.risk_reason)},
      prelim_grade = {kql_text(ev.prelim_grade)}, forecast_grade = {kql_text(forecast_grade)},
      selfsuff_pct = real({selfsuff_pct}), recommended_option_id = {kql_text(ev.recommended_option_id)},
      recommended_option_name = {kql_text(ev.recommended_option_name)}, option_cost_krw = tolong({ev.option_cost_krw}),
      expected_selfsuff_pct = real({ev.expected_selfsuff_pct}), expected_grade = {kql_text(ev.expected_grade_after)}""")
    print(f"{event_id}: ZebRiskEvent에 {status} 추가")


def set_status(status):
    spark.sql(f"UPDATE ops.risk_event SET status = '{status}' WHERE event_id = '{event_id}'")


if ev.status == "open":
    send("approved", ev.forecast_grade, ev.selfsuff_pct)
    set_status("approved")

# %% [markdown]
# ## 3. Silver·Gold 다시 계산
#
# 같은 작업 영역의 `03_silver_conform`, `04_gold_model`을 차례로 실행합니다. 약 5–8분 걸립니다.
#
# **예상 결과:** 두 Notebook이 오류 없이 끝나고 `Silver·Gold 다시 계산 완료`가 출력됩니다.

# %%
notebookutils.notebook.run("03_silver_conform", 1800)
notebookutils.notebook.run("04_gold_model", 1800, {"wait_for_graph": False})
print("Silver·Gold 다시 계산 완료")

# %% [markdown]
# ## 4. 결과 확인과 이벤트 종료
#
# 보완안을 반영한 새 설계안이 `현행`이 되고, 현장의 예상 등급과 상태가 다시 계산됩니다.
#
# **예상 결과:** 에코시티 D단지 현장의 현행 설계안이 `V4`(조치 반영안), 자립률 41.4%, 1차에너지 72.5, 예상 **4등급**, 상태 **정상**입니다.
# 위험이 해소되었으므로 `ZebRiskEvent`에 `resolved`가 추가되고, `ops.risk_event`의 상태도 `resolved`로 바뀝니다.

# %%
site = spark.table("ops.site_status").where(F.col("site_code") == ev.site_code).first()
print(f"{site.site_name}: 현행 {site.current_version_code}({site.current_version_name}) 자립률 {site.selfsuff_pct}% · "
      f"1차에너지 {site.primary_energy_kwh_m2y} → 예상 {site.forecast_zeb_label}, 상태 {site.risk_level}")
if site.risk_level != "위험":
    send("resolved", site.forecast_zeb_label, site.selfsuff_pct)
    set_status("resolved")
else:
    print(f"{ev.site_code}는 아직 위험 상태입니다: {site.risk_reason}")

bim_model_id = spark.table("gold.mdm_site_xref").where(F.col("site_code") == ev.site_code).first().bim_model_id
display(spark.table("gold.bim_design_version").where(F.col("bim_model_id") == bim_model_id).orderBy("version_code"))
display(kusto("query", f"ZebRiskEvent | where event_id == {kql_text(event_id)} "
                       "| project status_time, event_id, event_status, forecast_grade, selfsuff_pct, recommended_option_id | order by status_time asc"))
