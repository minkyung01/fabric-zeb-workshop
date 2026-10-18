# %% [markdown]
# # 04. Gold — 보고서·온톨로지·에이전트가 함께 쓰는 테이블
# 
# Gold는 **정제된 사실 데이터**만 담습니다. 원천 시스템의 코드(ERP 프로젝트 번호, PMS 현장 코드, BIM 모델 번호, SCM 거래처 코드)를 그대로 두고,
# 시스템 간 연결은 MDM 매핑표(`mdm_site_xref`)와 WBS 코드로 이어집니다.
# 
# **예상 등급·위험 여부 같은 업무 판단 결과는 Gold에 넣지 않습니다.** 판단 기준(등급 판정 규칙, 본인증 조건, 일정 연쇄 등)은
# 온톨로지(Fabric IQ)의 업무 규칙으로 정의하고, 운영 모니터링용 계산 결과는 별도 `ops` 스키마에 둡니다(보고서 전용).
# 
# | 영역 | Gold 테이블 |
# |---|---|
# | 기준 정보 | `ref_region`, `ref_building_use`, `ref_zeb_grade_criteria`, `ref_equipment_category` |
# | 공공 인증 | `pub_certified_building`, `pub_zeb_certification`, `pub_gseed_certification`, `pub_bf_certification`, `pub_green_tech_certificate` |
# | Contoso 내부 | `erp_project`, `pms_site`, `mdm_site_xref`, `bim_design_version`, `pms_certificate`, `pms_cert_target`, `pms_cert_milestone`, `pms_equipment_plan`, `scm_vendor`, `scm_purchase_order`, `scm_po_event`, `sim_improvement_option`, `pms_action_log` |
# | 운영 모니터링(`ops`) | `ops.site_status`, `ops.po_status`, `ops.milestone_forecast` |
#
# 다시 실행하면 이 Notebook이 만드는 테이블만 덮어씁니다. 09장의 위험 이벤트 테이블(`ops.risk_event` 등)은 그대로 둡니다.
# 전체 실행 시간은 약 2–3분입니다.

# %% [parameters]
as_of_date = "2026-09-30"
refresh_graph = True
wait_for_graph = True

# %% [markdown]
# ## 0. 준비
#
# Power BI가 빠르게 읽도록 V-Order로 저장합니다(Direct Lake 권장 설정).
#
# **예상 결과:** 결과 없이 끝납니다.

# %%
from pyspark.sql import functions as F, Window as W

spark.conf.set("spark.sql.parquet.vorder.default", "true")
spark.conf.set("spark.databricks.delta.optimizeWrite.enabled", "true")
for schema in ["gold", "ops"]:
    spark.sql(f"CREATE SCHEMA IF NOT EXISTS {schema}")
AS_OF = F.to_date(F.lit(as_of_date))

def save(df, table):
    df.write.mode("overwrite").option("overwriteSchema", "true").saveAsTable(table)
    print(f"{table:<34} {spark.table(table).count():>7,}행")

S = lambda t: spark.table(f"silver.{t}")

# %% [markdown]
# ## 1. 기준 정보
#
# 보고서 색(`grade_color`)과 용도의 주거 구분(`use_family`: 주거용/주거용 이외)을 더합니다. 1차에너지 기준값은 주거 구분에 따라 다릅니다.
#
# **예상 결과:** `gold.ref_region 17행`, `gold.ref_building_use …행`, `gold.ref_zeb_grade_criteria 6행`, `gold.ref_equipment_category 8행`

# %%
save(S("ref_region").select("sido", "sido_full", "region_group", "latitude", "longitude"), "gold.ref_region")

uses = (S("zeb_certification").select("use_group").unionByName(S("gseed_certification").select("use_group"))
        .unionByName(S("bf_certification").select("use_group")).unionByName(S("erp_project").select("use_group")).distinct())
save(uses.withColumn("use_family", F.when(F.col("use_group").isin("공동주택", "단독주택"), "주거용").otherwise("주거용 이외")), "gold.ref_building_use")

COLORS = {"+": "#004B1C", "1": "#107C10", "2": "#3F9B3F", "3": "#73B873", "4": "#A8D5A8", "5": "#D9EED9"}
color = F.create_map(*[x for k, v in COLORS.items() for x in (F.lit(k), F.lit(v))])
save(S("ref_zeb_grade_criteria").withColumn("grade_color", color[F.col("grade_code")]), "gold.ref_zeb_grade_criteria")
save(S("ref_equipment_category").select("category_code", "category_name", "zeb_role"), "gold.ref_equipment_category")

# %% [markdown]
# ## 2. 공공 인증
#
# Silver의 공공 인증을 그대로 옮기고 원천 표기 열(`sido_raw`)만 뺍니다. 테이블 이름 앞의 `pub_`는 공공 데이터라는 뜻입니다.
#
# **예상 결과:** 5줄. `gold.pub_zeb_certification`의 행 수가 Bronze `pub_zeb_cert`와 같습니다.

# %%
save(S("certified_building"), "gold.pub_certified_building")
save(S("zeb_certification").drop("sido_raw"), "gold.pub_zeb_certification")
save(S("gseed_certification").drop("sido_raw"), "gold.pub_gseed_certification")
save(S("bf_certification").drop("sido_raw"), "gold.pub_bf_certification")
save(S("green_tech_certificate"), "gold.pub_green_tech_certificate")

# %% [markdown]
# ## 3. Contoso 내부 — 시스템별 사실 데이터
#
# 원천 시스템의 코드와 이름을 그대로 둡니다. 예상 등급이나 위험 여부 같은 **판단 결과는 넣지 않습니다.**
#
# **예상 결과:** 13줄. `gold.erp_project 8행` … `gold.pms_action_log 0행`

# %%
save(S("erp_project").drop("sido_raw"), "gold.erp_project")
save(S("pms_site"), "gold.pms_site")
save(S("mdm_site_xref"), "gold.mdm_site_xref")
save(S("bim_design_version").select("version_id", "bim_model_id", "version_code", "version_name", "version_date", "selfsuff_pct",
                                    "primary_energy_kwh_m2y", "pv_kw", "geothermal_kw", "change_note", "version_status"), "gold.bim_design_version")
save(S("pms_certificate"), "gold.pms_certificate")
save(S("pms_cert_target"), "gold.pms_cert_target")
save(S("pms_cert_milestone"), "gold.pms_cert_milestone")
save(S("pms_equipment_plan"), "gold.pms_equipment_plan")
save(S("scm_vendor"), "gold.scm_vendor")
save(S("scm_purchase_order").select("po_no", "wbs_element", "vendor_code", "original_vendor_code", "order_date", "promised_date",
                                    "original_expected_date", "expected_date", "delivered_date", "status", "amount_krw",
                                    "change_event_count", "last_change_reason", "last_change_at"), "gold.scm_purchase_order")
save(S("scm_po_event"), "gold.scm_po_event")
save(S("sim_improvement_option"), "gold.sim_improvement_option")
save(S("pms_action_log").select("action_id", "action_ts", "site_code", "action_type", "detail_json", "approved_by", "source_system"), "gold.pms_action_log")

# %% [markdown]
# ## 4. 운영 모니터링(`ops`) — 보고서용 계산 결과
# 
# 온톨로지 규칙과 **같은 기준**으로 계산한 현재 상태입니다. Power BI 보고서(08장)와 Operations agent(09장)가 사용합니다.
# - 예상 등급 = 에너지자립률 기준 등급과 1차에너지소요량 기준 등급(주거용/주거용 이외 기준값) 중 **높은 등급**
# - 예비인증을 받은 현장은 사용승인 전 **예비 등급 이상의 본인증**이 필요
# - BEMS(또는 원격검침)는 인증 필수 요건
# - 필수 설비 입고가 '설비 설치 완료' 계획일을 넘기면 이후 인증 일정(본인증 신청·취득, 사용승인)이 넘긴 일수만큼 밀림
#
# | 상태(`risk_level`) | 조건 |
# |---|---|
# | 위험 | 예상 등급이 **예비인증 등급보다 낮음**, 또는 필수 설비가 설치 완료 계획일을 넘겨 입고 |
# | 주의 | 예상 등급이 목표 등급보다 낮음, BEMS 미계획, 추가 인증(녹색건축·BF) 목표 미달 |
# | 정상 | 위 조건에 해당하지 않음 |
#
# **예상 결과:** `ops.po_status 25행`, `ops.milestone_forecast 48행`, `ops.site_status 8행`

# %%
G = lambda t: spark.table(f"gold.{t}")
rule = G("ref_zeb_grade_criteria").withColumn("grade_rank", F.when(F.col("grade_code") == "+", 0).otherwise(F.col("grade_code").cast("int")))

def code_to_rank(c):
    return F.when(F.col(c) == "+", F.lit(0)).when(F.col(c).rlike(r"^[1-5]$"), F.col(c).cast("int"))

def rank_to_code(c):
    return F.when(F.col(c) == 0, "+").when(F.col(c).between(1, 5), F.col(c).cast("string")).otherwise("미달")

def rank_to_label(c):
    return F.when(F.col(c) == 0, "ZEB+").when(F.col(c).between(1, 5), F.concat(F.col(c).cast("string"), F.lit("등급"))).otherwise("인증 기준 미달")

# 발주 상태
eq = G("pms_equipment_plan")
install = G("pms_cert_milestone").where(F.col("milestone_type") == "설비 설치 완료").select("site_code", F.col("planned_date").alias("install_deadline"))
po = (G("scm_purchase_order")
      .join(eq.select(F.col("wbs_code").alias("wbs_element"), "site_code", "category_code"), "wbs_element", "left")
      .join(install, "site_code", "left")
      .withColumn("is_delivered", F.col("delivered_date").isNotNull())
      .withColumn("delay_vs_promise_days", F.datediff("expected_date", "promised_date"))
      .withColumn("days_late_vs_deadline", F.when(~F.col("is_delivered"), F.datediff("expected_date", "install_deadline")))
      .withColumn("is_late_vs_deadline", F.coalesce(F.col("days_late_vs_deadline") > 0, F.lit(False))))
save(po, "ops.po_status")
po = spark.table("ops.po_status")

# 인증 일정 예측
ms = G("pms_cert_milestone")
install_plan = ms.where(F.col("milestone_type") == "설비 설치 완료").select("site_code", F.col("planned_date").alias("_install_planned"))
po_max = po.where(~F.col("is_delivered")).groupBy("site_code").agg(F.max("expected_date").alias("_po_max"))
slip = (install_plan.join(po_max, "site_code", "left")
        .withColumn("install_slip_days", F.greatest(F.coalesce(F.datediff("_po_max", "_install_planned"), F.lit(0)), F.lit(0)))
        .select("site_code", "install_slip_days"))
ms = (ms.join(slip, "site_code", "left")
        .withColumn("install_slip_days", F.coalesce("install_slip_days", F.lit(0)))
        .withColumn("forecast_date", F.when(F.col("actual_date").isNotNull(), F.col("actual_date"))
                                      .when(F.col("seq") >= 3, F.date_add("planned_date", F.col("install_slip_days")))
                                      .otherwise(F.col("planned_date")))
        .withColumn("delay_days", F.datediff("forecast_date", "planned_date"))
        .withColumn("status", F.when(F.col("actual_date").isNotNull(), "완료").when(F.col("delay_days") > 0, "지연 위험").otherwise("예정")))
save(ms.select("milestone_id", "site_code", "seq", "milestone_type", "planned_date", "forecast_date", "actual_date", "delay_days", "status"),
     "ops.milestone_forecast")

# 현장 상태
site = (G("pms_site").join(G("mdm_site_xref").select("site_code", "project_no", "bim_model_id"), "site_code")
        .join(G("erp_project"), "project_no")
        .join(G("ref_building_use"), "use_group", "left")
        .join(G("ref_region").select("sido", "latitude", "longitude"), "sido", "left"))
cur = (G("bim_design_version").where(F.col("version_status") == "현행")
       .select("bim_model_id", F.col("version_id").alias("current_version_id"), F.col("version_code").alias("current_version_code"),
               F.col("version_name").alias("current_version_name"), "selfsuff_pct", "primary_energy_kwh_m2y"))
base = site.join(cur, "bim_model_id", "left")
r1 = (base.crossJoin(F.broadcast(rule)).where(F.col("selfsuff_pct") >= F.col("selfsuff_min_pct"))
          .groupBy("site_code").agg(F.min("grade_rank").alias("rank_by_selfsuff")))
pe_limit = F.when(F.col("use_family") == "주거용", F.col("primary_energy_limit_residential")).otherwise(F.col("primary_energy_limit_nonresidential"))
r2 = (base.crossJoin(F.broadcast(rule)).where(F.col("primary_energy_kwh_m2y") < pe_limit)
          .groupBy("site_code").agg(F.min("grade_rank").alias("rank_by_primary_energy")))
prelim = (G("pms_certificate").where("cert_type = 'ZEB' AND cert_stage = '예비인증'")
          .select("site_code", F.col("grade").alias("prelim_zeb_grade"), F.col("cert_date").alias("prelim_zeb_date")))
tgt = G("pms_cert_target").where("cert_type = 'ZEB'").select("site_code", F.col("target_grade").alias("target_zeb_grade"), F.col("basis").alias("target_basis"))
lvl = lambda c: F.when(F.col(c) == "최우수", 1).when(F.col(c) == "우수", 2).when(F.col(c) == "우량", 3).otherwise(4)
other = (G("pms_certificate").where("cert_type <> 'ZEB'").select("site_code", "cert_type", F.col("grade").alias("prelim_grade"))
         .join(G("pms_cert_target").select("site_code", "cert_type", "target_grade"), ["site_code", "cert_type"])
         .where(lvl("prelim_grade") > lvl("target_grade"))
         .groupBy("site_code").agg(F.concat_ws(", ", F.collect_list(F.concat(F.col("cert_type"), F.lit(" 예비 "), F.col("prelim_grade"),
                                                                            F.lit(" < 목표 "), F.col("target_grade")))).alias("other_cert_gap")))
bems = eq.where("category_code = 'BEMS'").select("site_code").distinct().withColumn("has_bems", F.lit(True))
late = (po.where("is_late_vs_deadline").groupBy("site_code")
          .agg(F.count("*").alias("late_po_count"), F.max("days_late_vs_deadline").alias("max_days_late")))

p = (base.join(r1, "site_code", "left").join(r2, "site_code", "left").join(prelim, "site_code", "left").join(tgt, "site_code", "left")
         .join(other, "site_code", "left").join(bems, "site_code", "left").join(late, "site_code", "left")
         .withColumn("has_bems", F.coalesce("has_bems", F.lit(False)))
         .withColumn("late_po_count", F.coalesce("late_po_count", F.lit(0)))
         .withColumn("max_days_late", F.coalesce("max_days_late", F.lit(0)))
         .withColumn("forecast_rank", F.least(F.coalesce("rank_by_selfsuff", F.lit(6)), F.coalesce("rank_by_primary_energy", F.lit(6))))
         .withColumn("prelim_rank", code_to_rank("prelim_zeb_grade"))
         .withColumn("target_rank", code_to_rank("target_zeb_grade"))
         .withColumn("required_rank", F.least(F.coalesce("prelim_rank", F.lit(99)), F.coalesce("target_rank", F.lit(99)))))
p = p.join(F.broadcast(rule.select(F.col("grade_rank").alias("required_rank"), F.col("selfsuff_min_pct").alias("required_selfsuff_min_pct"))),
           "required_rank", "left")
p = (p.withColumn("forecast_zeb_grade", rank_to_code("forecast_rank"))
      .withColumn("forecast_zeb_label", rank_to_label("forecast_rank"))
      .withColumn("grade_by_selfsuff", rank_to_code("rank_by_selfsuff"))
      .withColumn("grade_by_primary_energy", rank_to_code("rank_by_primary_energy"))
      .withColumn("grade_basis", F.when(F.coalesce("rank_by_primary_energy", F.lit(6)) < F.coalesce("rank_by_selfsuff", F.lit(6)), "1차에너지소요량")
                                 .when(F.coalesce("rank_by_selfsuff", F.lit(6)) < F.coalesce("rank_by_primary_energy", F.lit(6)), "에너지자립률")
                                 .otherwise("두 기준 동일"))
      .withColumn("grade_risk", F.when(F.col("prelim_rank").isNotNull() & (F.col("forecast_rank") > F.col("prelim_rank")), "예비 등급 미달")
                                 .when(F.col("target_rank").isNotNull() & (F.col("forecast_rank") > F.col("target_rank")), "목표 등급 미달")
                                 .otherwise("정상"))
      .withColumn("selfsuff_shortfall_pp", F.when(F.col("grade_risk") != "정상",
                                                  F.round(F.col("required_selfsuff_min_pct") - F.col("selfsuff_pct"), 1)).otherwise(F.lit(0.0)))
      .withColumn("requirement_risk", F.when(~F.col("has_bems"), "BEMS 미계획").otherwise("정상"))
      .withColumn("schedule_risk", F.when(F.col("late_po_count") > 0, "설치 지연").otherwise("정상"))
      .withColumn("other_cert_risk", F.when(F.col("other_cert_gap").isNotNull(), "추가 인증 목표 미달").otherwise("정상")))
p = (p.withColumn("risk_level", F.when((F.col("grade_risk") == "예비 등급 미달") | (F.col("schedule_risk") == "설치 지연"), "위험")
                                 .when((F.col("grade_risk") != "정상") | (F.col("requirement_risk") != "정상") | (F.col("other_cert_risk") != "정상"), "주의")
                                 .otherwise("정상"))
      .withColumn("risk_sort", F.when(F.col("risk_level") == "위험", 1).when(F.col("risk_level") == "주의", 2).otherwise(3))
      .withColumn("risk_reason", F.concat_ws(" / ",
          F.when(F.col("grade_risk") == "예비 등급 미달", F.concat(F.lit("예상 "), F.col("forecast_zeb_label"), F.lit("(자립률 "), F.col("selfsuff_pct").cast("string"),
                                                                  F.lit("%)이 예비인증 "), F.col("prelim_zeb_grade"), F.lit("등급보다 낮음"))),
          F.when(F.col("grade_risk") == "목표 등급 미달", F.concat(F.lit("예상 "), F.col("forecast_zeb_label"), F.lit("(자립률 "), F.col("selfsuff_pct").cast("string"),
                                                                  F.lit("%)이 목표 "), F.col("target_zeb_grade"), F.lit("등급보다 낮음"))),
          F.when(F.col("schedule_risk") == "설치 지연", F.concat(F.lit("필수 설비 "), F.col("late_po_count").cast("string"), F.lit("건이 설치 완료 계획일 초과(최대 "),
                                                                F.col("max_days_late").cast("string"), F.lit("일)"))),
          F.when(F.col("requirement_risk") != "정상", F.lit("인증 필수 요건인 BEMS가 설비 계획에 없음")),
          F.when(F.col("other_cert_gap").isNotNull(), F.col("other_cert_gap")))))
site_status = p.select("site_code", "site_name", "project_no", "project_name", "sido", "sigungu", "latitude", "longitude", "use_group", "use_family",
                       "households", "stage", "progress_pct", "planned_completion_date", "pm_name", "zeb_incentive",
                       "current_version_id", "current_version_code", "current_version_name", "selfsuff_pct", "primary_energy_kwh_m2y",
                       "grade_by_selfsuff", "grade_by_primary_energy", "grade_basis", "forecast_zeb_grade", "forecast_zeb_label",
                       "prelim_zeb_grade", "prelim_zeb_date", "target_zeb_grade", "target_basis", "required_selfsuff_min_pct",
                       "selfsuff_shortfall_pp", "grade_risk", "has_bems", "requirement_risk", "late_po_count", "max_days_late",
                       "schedule_risk", "other_cert_gap", "other_cert_risk", "risk_level", "risk_sort", "risk_reason")
save(site_status, "ops.site_status")

# %% [markdown]
# ## 5. 결과 확인
#
# **예상 결과:** 첫 표는 현장 8행이며 위험 순서로 정렬됩니다. 위험 1곳(에코시티 D단지), 주의 3곳, 정상 4곳입니다.
#
# - **에코시티 D단지(HS-D):** VE 반영안 V3 자립률 38.2%·1차에너지 76 → 예상 **5등급**. 예비인증 4등급보다 낮아 **위험**
# - **주의:** 스마트오피스 C센터(BEMS 미계획), 세종 E학교(BF 예비 우수 < 목표 최우수), 마포 H단지(예상 5등급 < 목표 4등급)
# - **리버뷰 B단지(IC-B):** 자립률 39%로 4등급 하한(40%)에 못 미치지만 1차에너지소요량 65가 주거용 4등급 기준(70 미만)을 충족해 **4등급·정상**
#
# 두 번째 표는 `gold` 스키마의 테이블 22개입니다.

# %%
display(spark.table("ops.site_status").select("site_name", "selfsuff_pct", "primary_energy_kwh_m2y", "forecast_zeb_label", "grade_basis",
                                              "prelim_zeb_grade", "target_zeb_grade", "risk_level", "risk_reason").orderBy("risk_sort", "site_code"))
display(spark.sql("SHOW TABLES IN gold"))

# %% [markdown]
# ## 6. 온톨로지 그래프 새로 고침
# 
# Gold를 다시 만들었으므로 온톨로지 그래프(`ont_zeb_graph_…`)가 있으면 새로 고쳐 최신 데이터를 반영합니다.
# 05장에서는 아직 온톨로지가 없으므로 `온톨로지 그래프가 없어 새로 고침을 건너뜁니다.`가 정상입니다.
# 그래프는 06장의 선택 단계에서만 만듭니다. `wait_for_graph = False`이면 새로 고침을 요청만 하고 기다리지 않습니다(승인 반영 Notebook이 사용).

# %%
import time
import sempy.fabric as fabric

if refresh_graph:
    client = fabric.FabricRestClient()
    ws_id = fabric.get_workspace_id()
    graphs = [g for g in client.get(f"/v1/workspaces/{ws_id}/items?type=GraphModel").json().get("value", [])
              if g["displayName"].startswith("ont_zeb_graph")]
    if not graphs:
        print("온톨로지 그래프가 없어 새로 고침을 건너뜁니다.")
    for g in graphs:
        r = client.post(f"/v1/workspaces/{ws_id}/graphModels/{g['id']}/jobs/refreshGraph/instances")
        loc = r.headers.get("Location")
        print(f"{g['displayName']}: 새로 고침 요청 ({r.status_code})")
        t0 = time.time()
        while wait_for_graph and loc and time.time() - t0 < 900:
            time.sleep(15)
            st = client.get(loc).json().get("status")
            if st in ("Completed", "Failed", "Cancelled", "Deduped"):
                print(f"  → {st} ({int(time.time() - t0)}초)")
                break
