# %% [markdown]
# # 06. 위험 이벤트 만들고 Eventhouse로 보내기
#
# 05장에서 계산한 현장 상태(`ops.site_status`)에서 **위험** 현장을 찾아, Operations agent가 감시할 위험 이벤트를 만듭니다.
#
# 1. 위험·주의 현장의 보완안을 하나씩 적용해 보고, 필요한 등급을 되찾으면서 설비 설치 전에 준비가 끝나는 안을 고릅니다(`ops.option_eval`).
# 2. 예상 등급이 예비인증 등급보다 낮은 **위험** 현장마다 위험 이벤트 1건을 만들고 **가장 싼 보완안**을 추천안으로 정합니다(`ops.risk_event`).
# 3. 위험 이벤트를 Eventhouse `eh_zeb`의 `ZebRiskEvent` 테이블에 `open` 상태로 보냅니다.
#
# 추천안은 계산으로 정하고, 최종 결정은 담당자가 Teams에서 합니다. 이 Notebook은 설계나 발주를 바꾸지 않습니다.
#
# **시작 전:** 09장 2단계에서 `ZebRiskEvent` 테이블을 만들고, 6단계에서 Operations agent를 **Start**한 다음에 실행합니다.

# %% [parameters]
as_of_date = "2026-09-30"
eventhouse_name = "eh_zeb"
send_to_eventhouse = True

# %% [markdown]
# ## 1. 보완안 평가
#
# 위험·주의 현장 중 보완안이 있는 현장(D단지, H단지)의 보완안을 **하나씩** 현재 설계안에 더해 예상 등급을 다시 계산합니다.
#
# | 열 | 뜻 |
# |---|---|
# | `required_grade` | 지켜야 할 등급. 예비인증이 있으면 예비인증 등급, 없으면 목표 등급 |
# | `meets_grade` | 보완안 적용 후 예상 등급이 필요 등급 이상인가 |
# | `ready_date`, `meets_schedule` | 기준일에 시작하면 준비가 끝나는 날, 그날이 설비 설치 완료 계획일 이전인가 |
# | `feasible`, `cost_rank` | 두 조건을 모두 만족하는가, 만족하는 안 중 비용 순위 |
#
# **예상 결과:** `ops.option_eval 11행`. D단지는 D2(1순위, 2억 3천만 원)·D4·D1이, H단지는 H3이 `feasible`입니다.

# %%
from datetime import date, datetime, timedelta, timezone
from pyspark.sql import Window, functions as F

AS_OF = date.fromisoformat(as_of_date)
G = lambda t: spark.table(f"gold.{t}")
O = lambda t: spark.table(f"ops.{t}")

criteria = [r.asDict() for r in G("ref_zeb_grade_criteria").collect()]
RANK = {"+": 0, "1": 1, "2": 2, "3": 3, "4": 4, "5": 5}
LABEL = {0: "ZEB+", 1: "1등급", 2: "2등급", 3: "3등급", 4: "4등급", 5: "5등급", 6: "인증 기준 미달"}


def zeb_rank(selfsuff_pct, primary_energy, residential):
    limit = "primary_energy_limit_residential" if residential else "primary_energy_limit_nonresidential"
    by_ss = min([RANK[c["grade_code"]] for c in criteria if selfsuff_pct >= c["selfsuff_min_pct"]], default=6)
    by_pe = min([RANK[c["grade_code"]] for c in criteria if primary_energy < c[limit]], default=6)
    return min(by_ss, by_pe)


install = {r.site_code: r.planned_date for r in G("pms_cert_milestone").where("milestone_type = '설비 설치 완료'").collect()}
sites = {r.site_code: r for r in O("site_status").where("grade_risk <> '정상'").collect()}
rows = []
for o in G("sim_improvement_option").where(F.col("site_code").isin(list(sites))).collect():
    s = sites[o.site_code]
    required = RANK.get(s.prelim_zeb_grade or s.target_zeb_grade)
    ss = round(s.selfsuff_pct + o.selfsuff_gain_pp, 1)
    pe = round(s.primary_energy_kwh_m2y + o.primary_energy_delta, 1)
    rank = zeb_rank(ss, pe, s.use_family == "주거용")
    ready = AS_OF + timedelta(days=o.lead_time_days)
    rows.append((o.site_code, o.option_id, o.option_name, o.cost_krw, o.lead_time_days, s.current_version_code,
                 s.selfsuff_pct, s.primary_energy_kwh_m2y, ss, pe, LABEL[rank], LABEL[required], rank <= required,
                 ready, install[o.site_code], ready <= install[o.site_code]))
option_eval = (spark.createDataFrame(rows,
                   "site_code string, option_id string, option_name string, cost_krw long, lead_time_days int, base_version string, "
                   "base_selfsuff_pct double, base_primary_energy double, expected_selfsuff_pct double, expected_primary_energy double, "
                   "expected_grade string, required_grade string, meets_grade boolean, ready_date date, install_deadline date, meets_schedule boolean")
               .withColumn("feasible", F.col("meets_grade") & F.col("meets_schedule")))
ranked = (option_eval.where("feasible")
          .withColumn("cost_rank", F.row_number().over(Window.partitionBy("site_code").orderBy("cost_krw", "option_id")))
          .select("site_code", "option_id", "cost_rank"))
option_eval = option_eval.join(ranked, ["site_code", "option_id"], "left")
option_eval.write.mode("overwrite").option("overwriteSchema", "true").saveAsTable("ops.option_eval")
print(f"ops.option_eval {spark.table('ops.option_eval').count():>5}행")
display(spark.table("ops.option_eval").orderBy("site_code", "cost_krw")
        .select("site_code", "option_id", "option_name", "cost_krw", "expected_selfsuff_pct", "expected_primary_energy",
                "expected_grade", "required_grade", "ready_date", "feasible", "cost_rank"))

# %% [markdown]
# ## 2. 위험 이벤트와 추천 보완안
#
# 현장 상태가 **위험**이고 예상 등급이 예비인증 등급보다 낮은 현장마다 이벤트를 1건씩 만듭니다.
# 추천 보완안은 위 표에서 `cost_rank = 1`인 안이고, 이벤트 ID는 `ZEB-<현장 코드>-<기준일>` 형식입니다.
#
# 승인을 반영하고 있는(`approved`) 이벤트는 상태를 그대로 두고 다시 보내지 않습니다. 위험이 해소(`resolved`)된 현장이 다시 위험해지면 새로 `open`이 됩니다.
#
# **예상 결과:** 1행이 나옵니다. `ZEB-HS-D-20260930`, 에코시티 D단지 현장, 예비인증 4등급·예상 5등급, 추천안 `OPT-D2` 주차장 캐노피 태양광(+90kW),
# 비용 `230,000,000`원, 적용 후 자립률 41.4%·4등급, 상태 `open`입니다.

# %%
events = (O("site_status").where("risk_level = '위험' AND grade_risk = '예비 등급 미달'")
          .join(spark.table("ops.option_eval").where("cost_rank = 1")
                .select("site_code", F.col("option_id").alias("recommended_option_id"), F.col("option_name").alias("recommended_option_name"),
                        F.col("cost_krw").alias("option_cost_krw"), "expected_selfsuff_pct", F.col("expected_grade").alias("expected_grade_after")),
                "site_code", "left")
          .select(F.concat(F.lit("ZEB-"), F.col("site_code"), F.lit("-" + AS_OF.strftime("%Y%m%d"))).alias("event_id"),
                  "site_code", "site_name", "risk_reason", F.col("prelim_zeb_grade").alias("prelim_grade"),
                  F.col("forecast_zeb_label").alias("forecast_grade"), "selfsuff_pct", "primary_energy_kwh_m2y",
                  "recommended_option_id", "recommended_option_name", "option_cost_krw", "expected_selfsuff_pct", "expected_grade_after",
                  F.lit("open").alias("status"), F.current_timestamp().alias("created_at")))

if spark.catalog.tableExists("ops.risk_event"):
    kept = spark.table("ops.risk_event").where("status = 'approved'").select("event_id", F.col("status").alias("_kept"))
    events = (events.join(kept, "event_id", "left")
                    .withColumn("status", F.coalesce("_kept", "status")).drop("_kept"))
    events = events.unionByName(spark.table("ops.risk_event").join(events.select("event_id"), "event_id", "left_anti"))
events.write.mode("overwrite").option("overwriteSchema", "true").saveAsTable("ops.risk_event")
risk_events = spark.table("ops.risk_event")
display(risk_events)

# %% [markdown]
# ## 3. Eventhouse로 보내기
#
# 같은 작업 영역에서 이름으로 Eventhouse `eh_zeb`를 찾아, `open` 상태인 이벤트를 `ZebRiskEvent`에 한 행씩 추가합니다.
# Operations agent는 `event_status`가 `open`으로 **바뀌는 순간** Teams로 알립니다.
#
# **예상 결과:** `ZEB-HS-D-20260930: ZebRiskEvent에 open 추가` 한 줄과, Eventhouse에서 다시 읽은 1행짜리 표가 나옵니다.
# `ZebRiskEvent 테이블이 없습니다` 오류가 나면 09장 2단계에서 테이블을 먼저 만듭니다.

# %%
import pandas as pd
import requests
import sempy.fabric as fabric

workspace_id = fabric.get_workspace_id()
eventhouses = fabric.FabricRestClient().get(f"v1/workspaces/{workspace_id}/eventhouses").json()["value"]
matches = [e for e in eventhouses if e["displayName"] == eventhouse_name]
if len(matches) != 1:
    raise ValueError(f"현재 작업 영역에 {eventhouse_name} Eventhouse가 정확히 1개 있어야 합니다. 09장 1단계를 확인하세요.")
kusto_uri = matches[0]["properties"]["queryServiceUri"]
headers = {"Authorization": "Bearer " + notebookutils.credentials.getToken("kusto")}


def kql_text(value):
    return "'" + str(value).replace("\\", "\\\\").replace("'", "\\'") + "'" if value is not None else "''"


def kusto(endpoint, command):
    response = requests.post(f"{kusto_uri}/v1/rest/{endpoint}", headers=headers,
                             json={"db": eventhouse_name, "csl": command}, timeout=60)
    response.raise_for_status()
    result = response.json()
    if result.get("Exceptions"):
        raise RuntimeError(f"Kusto 요청 실패: {result['Exceptions']}")
    table = result["Tables"][0]
    return pd.DataFrame(table["Rows"], columns=[c["ColumnName"] for c in table["Columns"]])


def send(ev, status):
    kusto("mgmt", f""".set-or-append ZebRiskEvent <|
print event_id = {kql_text(ev.event_id)}, status_time = now(), event_status = {kql_text(status)},
      site_code = {kql_text(ev.site_code)}, site_name = {kql_text(ev.site_name)}, risk_reason = {kql_text(ev.risk_reason)},
      prelim_grade = {kql_text(ev.prelim_grade)}, forecast_grade = {kql_text(ev.forecast_grade)},
      selfsuff_pct = real({ev.selfsuff_pct}), recommended_option_id = {kql_text(ev.recommended_option_id)},
      recommended_option_name = {kql_text(ev.recommended_option_name)}, option_cost_krw = tolong({ev.option_cost_krw or 0}),
      expected_selfsuff_pct = real({ev.expected_selfsuff_pct or 0}), expected_grade = {kql_text(ev.expected_grade_after)}""")
    print(f"{ev.event_id}: ZebRiskEvent에 {status} 추가")


if send_to_eventhouse:
    if kusto("mgmt", ".show tables | where TableName == 'ZebRiskEvent'").empty:
        raise ValueError("ZebRiskEvent 테이블이 없습니다. 09장 2단계에서 테이블을 먼저 만드세요.")
    to_send = risk_events.where("status = 'open'").collect()
    if not to_send:
        print("open 상태인 위험 이벤트가 없어 보내지 않았습니다.")
    for ev in to_send:
        send(ev, "open")
    display(kusto("query", "ZebRiskEvent | project status_time, event_id, event_status, site_code, recommended_option_id, "
                           "option_cost_krw, expected_grade | order by status_time asc"))
