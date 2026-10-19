# %% [markdown]
# # 03. Silver — 표기와 형식 맞추기
# 
# Bronze의 공공 데이터와 Contoso 내부 데이터를 **서로 비교할 수 있도록** 정리합니다.
# Silver에서는 값을 정리하고 표기를 맞추고 이벤트를 반영하기만 합니다. **예상 등급이나 위험 여부는 계산하지 않습니다.**
# 
# | 규칙 | 예시 |
# |---|---|
# | 시도 표기 통일 | `전라북도`·`전북특별자치도` → `전북`, `서울시`·`서울특별시` → `서울`, `경기 ` → `경기` |
# | 용도 통일 | `제1종 근린생활시설` → `근린생활시설`, 녹색건축 `학교시설` → `교육연구시설` |
# | 인증 구분·등급 표기 통일 | BF `본`/`예비` → `본인증`/`예비인증`, 녹색건축 `우수(그린2등급)` → `우수` |
# | 같은 건물 연결 | 시도와 정리한 건물명(괄호·기호·'신축공사' 등을 지움)이 같으면 ZEB·녹색건축·BF 인증을 한 건물로 묶음 |
# | 날짜·숫자 형식 | 앞뒤 공백을 지우고, 날짜가 아닌 값(예: `본인증 교부전 또는 사용승인 후 1년 이내`)은 비고 열로 옮김 |
# | 이벤트·조치 반영 | 발주 납기 변경·공급사 변경 이벤트와 승인된 보완안을 반영해 현재 상태로 맞춤 |
#
# 이 Notebook은 실행할 때마다 `silver` 스키마를 비우고 Bronze에서 다시 만듭니다. 전체 실행에 약 3분 걸립니다.

# %% [parameters]
as_of_date = "2026-09-30"

# %% [markdown]
# ## 0. 준비 — 정리용 함수
#
# 문자열 앞뒤 공백 제거(`trim_strings`), 빈 문자열을 null로 바꾸기(`blank_null`), 날짜·숫자 변환(`as_date`, `as_double`) 함수를 만듭니다.
# 날짜나 숫자로 바꿀 수 없는 값이 있어도 멈추지 않고 null로 둡니다.
#
# **예상 결과:** 결과 없이 끝납니다.

# %%
from pyspark.sql import functions as F, Window as W

spark.sql("CREATE SCHEMA IF NOT EXISTS silver")
for r in spark.sql("SHOW TABLES IN silver").collect():
    spark.sql(f"DROP TABLE IF EXISTS silver.{r.tableName}")

def save(df, table):
    df.write.mode("overwrite").option("overwriteSchema", "true").saveAsTable(table)
    print(f"{table:<38} {spark.table(table).count():>7,}행")

def trim_strings(df):
    return df.select([F.trim(F.col(c)).alias(c) if t == "string" else F.col(c) for c, t in df.dtypes])

def blank_null(c):
    return F.when(F.col(c) == "", F.lit(None)).otherwise(F.col(c))

def as_date(c):
    return F.when(F.col(c).rlike(r"^\d{4}-\d{2}-\d{2}$"), F.to_date(F.col(c)))

def as_double(c):
    return F.expr(f"try_cast(nullif(regexp_replace({c}, ',', ''), '') as double)")

B = lambda t: trim_strings(spark.table(f"bronze.{t}")).drop("_source", "_generated_at")

# %% [markdown]
# ## 1. 공통 규칙 — 시도, 건물명, 용도
#
# - **시도:** `ref_region`의 정식명과 별칭을 모두 펼쳐 `별칭 → 시도` 대응표를 만들고, 원천 표기를 이 표로 바꿉니다.
# - **건물명 키:** 괄호 안 내용, 기호, `신축공사` 같은 말을 지워서 기관마다 조금씩 다른 건물명이 같은 키가 되게 합니다.
# - **용도:** 원천 용도를 실습에서 쓰는 용도 그룹(`use_group`)으로 바꿉니다.
#
# **예상 결과:** `silver.ref_zeb_grade_criteria 6행`, `silver.ref_region 17행`, `silver.ref_equipment_category 8행`

# %%
ref_region = spark.table("bronze.ref_region")
region_alias = (ref_region.select("sido", F.explode(F.split("aliases", r"\|")).alias("alias"))
                .unionByName(ref_region.select("sido", F.col("sido").alias("alias")))
                .unionByName(ref_region.select("sido", F.col("sido_full").alias("alias")))
                .select("sido", F.trim("alias").alias("alias"))
                .dropDuplicates(["alias"]))

def conform_sido(df, raw_col):
    a = region_alias.select("sido", F.col("alias").alias("_alias"))
    return df.join(F.broadcast(a), F.col(raw_col) == F.col("_alias"), "left").drop("_alias")

STOP_WORDS = ["기본및실시설계용역", "실시설계용역", "설계용역", "신축공사", "건립공사", "증축공사", "신축", "건립", "공사", "사업", "건설"]

def name_key(col):
    x = F.regexp_replace(F.coalesce(col, F.lit("")), r"\(.*?\)|\[.*?\]", "")
    x = F.regexp_replace(x, r"[^0-9A-Za-z가-힣]", "")
    for w in STOP_WORDS:
        x = F.regexp_replace(x, w, "")
    return F.when(x == "", F.lit(None)).otherwise(x)

USE_EXACT = {
    "공동주택": "공동주택", "단독주택": "단독주택", "업무시설": "업무시설", "교육연구시설": "교육연구시설",
    "문화 및 집회시설": "문화 및 집회시설", "노유자시설": "노유자시설", "제1종 근린생활시설": "근린생활시설",
    "제2종 근린생활시설": "근린생활시설", "근린생활시설": "근린생활시설", "운동시설": "운동시설", "의료시설": "의료시설",
    "숙박시설": "숙박시설", "판매시설": "판매시설", "공장": "공장", "교정 및 군사 시설": "군사·교정시설", "국방·군사시설": "군사·교정시설",
}
use_map = spark.createDataFrame(list(USE_EXACT.items()), "_use_src string, use_group string")

def conform_use(df, raw_col):
    return (df.join(F.broadcast(use_map), F.col(raw_col) == F.col("_use_src"), "left").drop("_use_src")
              .withColumn("use_group", F.coalesce("use_group", F.lit("기타"))))

save(B("ref_zeb_grade_criteria"), "silver.ref_zeb_grade_criteria")
save(ref_region.drop("_source", "_generated_at"), "silver.ref_region")
save(B("ref_equipment_category"), "silver.ref_equipment_category")

# %% [markdown]
# ## 2. 공공 인증 데이터
#
# 인증 4종을 같은 규칙으로 정리합니다. 행을 지우지 않으므로 **행 수는 Bronze와 같습니다.**
# 인증마다 `cert_id`(예: `ZEB-00001`)와, 같은 건물을 묶는 `building_key`(`시도|정리한 건물명`)가 붙습니다.
#
# **예상 결과:** 4줄이 출력됩니다. `silver.zeb_certification`, `silver.gseed_certification`, `silver.bf_certification`, `silver.green_tech_certificate`의
# 행 수가 Bronze와 같습니다.

# %%
# 제로에너지건축물(ZEB) 인증 — 인증 구분(본인증/예비인증)과 등급 코드(+, 1~5)는 기관 원본 값을 그대로 씁니다.
z = (trim_strings(spark.table("bronze.pub_zeb_cert"))
     .withColumnRenamed("region", "sido_raw")
     .withColumn("grade_code", blank_null("zeb_grade"))
     .withColumn("selfsuff_pct", as_double("energy_self_sufficiency"))
     .withColumn("cert_date", as_date("cert_date")))
z = conform_use(conform_sido(z, "sido_raw"), "building_main_use")
z = (z.withColumn("name_key", name_key(F.col("building_name")))
      .withColumn("building_key", F.when(F.col("sido").isNotNull() & F.col("name_key").isNotNull(), F.concat_ws("|", "sido", "name_key")))
      .withColumn("cert_year", F.year("cert_date"))
      .withColumn("cert_id", F.concat(F.lit("ZEB-"), F.lpad(F.col("source_row_num").cast("string"), 5, "0"))))
zeb = z.select("cert_id", "building_key", "building_name", "sido", "sido_raw", "use_group", F.col("building_main_use").alias("main_use"),
               F.col("building_use_group").alias("residential_type"), "cert_stage", "grade_code",
               "selfsuff_pct", "cert_date", "cert_year", "applicant_name")
save(zeb, "silver.zeb_certification")

# 녹색건축(G-SEED) 인증
g = (trim_strings(spark.table("bronze.pub_gseed_cert"))
     .withColumnRenamed("sido", "sido_raw").withColumnRenamed("building_group", "building_group_raw")
     .withColumn("is_validity_extension", F.col("cert_stage").startswith("유효기간연장"))
     .withColumn("cert_stage", F.when(F.col("cert_stage").contains("본인증"), "본인증").when(F.col("cert_stage").startswith("예비"), "예비인증"))
     .withColumn("grade_label", F.regexp_extract("cert_grade", r"^(최우수|우수|우량|일반)", 1))
     .withColumn("cert_grade_raw", F.col("cert_grade"))
     .withColumn("cert_date", as_date("cert_date"))
     .withColumn("gross_floor_area_m2", as_double("gross_floor_area"))
     .withColumn("floors_above", F.expr("try_cast(nullif(floors_above, '') as int)"))
     .withColumn("floors_below", F.expr("try_cast(nullif(floors_below, '') as int)")))
g = conform_sido(g, "sido_raw")
first = F.split(F.col("building_group_raw"), ",").getItem(0)
g = g.withColumn("use_group", F.when(first.contains("공동주택"), "공동주택").when(first.contains("학교"), "교육연구시설")
                               .when(first.contains("업무"), "업무시설").when(first.contains("숙박"), "숙박시설")
                               .when(first.contains("판매"), "판매시설").when(first.contains("주택"), "단독주택").otherwise("기타"))
g = (g.withColumn("name_key", name_key(F.col("building_name")))
      .withColumn("building_key", F.when(F.col("sido").isNotNull() & F.col("name_key").isNotNull(), F.concat_ws("|", "sido", "name_key")))
      .withColumn("cert_year", F.year("cert_date"))
      .withColumn("cert_id", F.concat(F.lit("GS-"), F.lpad(F.col("source_row_num").cast("string"), 5, "0"))))
gseed = g.select("cert_id", "cert_no", "building_key", "building_name", "sido", "sido_raw", "use_group", "building_group_raw",
                 "cert_stage", "is_validity_extension", "grade_label", "cert_grade_raw", "cert_date", "cert_year", "address",
                 "gross_floor_area_m2", "floors_above", "floors_below")
save(gseed, "silver.gseed_certification")

# 장애물 없는 생활환경(BF) 인증
b = (trim_strings(spark.table("bronze.pub_bf_cert"))
     .withColumnRenamed("sido", "sido_raw")
     .withColumn("cert_stage", F.when(F.col("cert_stage") == "본", "본인증").when(F.col("cert_stage") == "예비", "예비인증"))
     .withColumn("grade_label", blank_null("cert_grade"))
     .withColumn("cert_date", as_date("cert_date"))
     .withColumn("expiry_date", as_date("cert_expiry"))
     .withColumn("expiry_note", F.when(F.col("expiry_date").isNull(), blank_null("cert_expiry")))
     .withColumn("area_m2", as_double("area"))
     .withColumn("is_building", F.col("cert_target") == "건축물"))
b = conform_use(conform_sido(b, "sido_raw"), "use_type")
b = (b.withColumn("name_key", name_key(F.col("facility_name")))
      .withColumn("building_key", F.when(F.col("is_building") & F.col("sido").isNotNull() & F.col("name_key").isNotNull(), F.concat_ws("|", "sido", "name_key")))
      .withColumn("cert_year", F.year("cert_date"))
      .withColumn("cert_id", F.concat(F.lit("BF-"), F.lpad(F.col("source_row_num").cast("string"), 5, "0"))))
bf = b.select("cert_id", "cert_no", "building_key", "facility_name", "sido", "sido_raw", "sigungu", "cert_target", "is_building",
              "use_group", "use_type", "cert_stage", "grade_label", "cert_date", "cert_year", "expiry_date", "expiry_note",
              "applicant_name", "cert_body", "area_m2")
save(bf, "silver.bf_certification")

# 녹색기술 인증
cat = (spark.table("bronze.ref_equipment_category")
       .select("category_code", F.explode(F.split("green_tech_classes", r"\|")).alias("class_name"))
       .where(F.col("class_name") != ""))
t = (trim_strings(spark.table("bronze.pub_green_tech_cert"))
     .withColumn("cert_date", as_date("cert_date"))
     .withColumn("expiry_date", as_date("cert_expiry"))
     .withColumn("data_base_date", as_date("data_base_date"))
     .join(F.broadcast(cat), "class_name", "left")
     .withColumn("cert_id", F.concat(F.lit("GT-"), F.lpad(F.col("source_row_num").cast("string"), 5, "0"))))
green_tech = t.select("cert_id", "cert_no", "tech_name", "class_code", "class_name", "category_code", "applicant_name",
                      "issuing_ministry", "cert_date", "expiry_date", "data_base_date")
save(green_tech, "silver.green_tech_certificate")

# %% [markdown]
# ## 3. 같은 건물 연결 — 인증 건물
# 
# 한 건물이 ZEB·녹색건축·BF 인증을 각각 받으면 기관마다 따로 기록됩니다. **시도와 정리한 건물명**이 같으면 같은 건물(`building_key`)로 봅니다.
# 건물 이름·시도·용도는 ZEB → 녹색건축 → BF 순서로 찾고, 인증마다 가장 최근 기록(본인증 우선)의 값을 씁니다.
#
# **예상 결과:** `silver.certified_building 25,362행` 한 줄이 출력됩니다. 한 건물이 받은 여러 인증이 한 행으로 묶이므로 세 인증의 건수를 더한 값보다 적습니다.

# %%
def latest(df, name_col, cols):
    w = W.partitionBy("building_key").orderBy(F.when(F.col("cert_stage") == "본인증", 0).otherwise(1), F.col("cert_date").desc_nulls_last())
    return (df.where(F.col("building_key").isNotNull()).withColumn("_rn", F.row_number().over(w)).where("_rn = 1")
              .select("building_key", F.col(name_col).alias(cols[0]), F.col("sido").alias(cols[1]), F.col("use_group").alias(cols[2])))

zl = latest(zeb, "building_name", ["zeb_name", "zeb_sido", "zeb_use"])
gl = latest(gseed, "building_name", ["gseed_name", "gseed_sido", "gseed_use"])
bl = latest(bf.where("is_building"), "facility_name", ["bf_name", "bf_sido", "bf_use"])
certified_building = (zl.join(gl, "building_key", "full").join(bl, "building_key", "full")
      .select("building_key",
              F.coalesce("zeb_name", "gseed_name", "bf_name").alias("building_name"),
              F.coalesce("zeb_sido", "gseed_sido", "bf_sido").alias("sido"),
              F.coalesce("zeb_use", F.when(F.col("gseed_use") != "기타", F.col("gseed_use")), "bf_use", F.lit("기타")).alias("use_group")))
save(certified_building, "silver.certified_building")

# %% [markdown]
# ## 4. Contoso 내부 데이터 — 이벤트와 승인된 조치를 반영한 현재 상태
#
# 내부 데이터는 값을 정리하면서 **이벤트와 조치를 반영해 현재 상태로 맞춥니다.**
#
# - **발주 이벤트:** 납기 변경 이벤트가 있으면 `expected_date`를 새 날짜로 바꾸고, 원래 날짜는 `original_expected_date`에 남깁니다.
#   리버뷰 B단지 창호(`IC-B-ENV`)의 예상 입고일이 `2027-04-15`에서 `2027-04-20`으로 바뀝니다.
# - **승인된 보완안:** `pms_action_log`에 `apply_options` 기록이 있으면, 현재 설계안에 보완안 효과를 더한 **새 설계안(조치 반영안)** 을 만들어
#   `현행`으로 바꿉니다. 지금은 조치 기록이 없어서 새 설계안이 생기지 않습니다(10장에서 생깁니다).
#
# **예상 결과:** 내부 테이블 13개가 Bronze와 같은 행 수로 만들어집니다. `silver.bim_design_version 18행`, `silver.pms_equipment_plan 39행`,
# `silver.scm_purchase_order 25행`, `silver.pms_action_log 0행` 등입니다.

# %%
# ERP 프로젝트, PMS 현장, MDM 매핑
erp = conform_use(conform_sido(B("erp_project"), "sido_raw"), "main_use")
save(erp.select("project_no", "project_name", "sido", "sido_raw", "sigungu", "use_group", "main_use", "households", "gross_floor_area_m2",
                "client_type", "start_date", "planned_completion_date", "pm_name", "zeb_incentive"), "silver.erp_project")
save(B("pms_site"), "silver.pms_site")
xref = B("mdm_site_xref")
save(xref, "silver.mdm_site_xref")

# 조치 기록
acts = (B("pms_action_log")
        .withColumn("action_ts", F.to_timestamp("action_time"))
        .withColumn("option_ids", F.from_json("detail_json", "struct<option_ids:array<string>>").getField("option_ids")))
save(acts.drop("option_ids", "action_time"), "silver.pms_action_log")

opts = B("sim_improvement_option")
applied = (acts.where(F.col("action_type") == "apply_options")
           .select("action_id", "site_code", "action_ts", F.explode("option_ids").alias("option_id"))
           .join(opts, ["site_code", "option_id"]))

# 설계안 + 승인된 보완안으로 만든 새 설계안(버전 번호를 하나씩 올림)
dv = B("bim_design_version").withColumn("version_no", F.expr("cast(substring(version_code, 2) as int)"))
base = (dv.where(F.col("version_status") == "현행")
          .select("bim_model_id", F.col("version_no").alias("base_no"), F.col("selfsuff_pct").alias("base_ss"),
                  F.col("primary_energy_kwh_m2y").alias("base_pe"), F.col("pv_kw").alias("base_pv"), F.col("geothermal_kw").alias("base_geo")))
gain = (applied.groupBy("site_code", "action_id", "action_ts").agg(
            F.sum("selfsuff_gain_pp").alias("gain_pp"), F.sum("primary_energy_delta").alias("pe_delta"),
            F.concat_ws(", ", F.collect_list("option_name")).alias("option_names"))
        .join(xref.select("site_code", "bim_model_id"), "site_code"))
wcum = W.partitionBy("bim_model_id").orderBy("action_ts").rowsBetween(W.unboundedPreceding, 0)
new_dv = (gain.join(base, "bim_model_id")
          .withColumn("seq", F.row_number().over(W.partitionBy("bim_model_id").orderBy("action_ts")))
          .withColumn("cum_gain", F.sum("gain_pp").over(wcum)).withColumn("cum_pe", F.sum("pe_delta").over(wcum))
          .withColumn("version_no", (F.col("base_no") + F.col("seq")).cast("int"))
          .select(F.concat(F.col("bim_model_id"), F.lit("-V"), F.col("version_no").cast("string")).alias("version_id"),
                  "bim_model_id", F.concat(F.lit("V"), F.col("version_no").cast("string")).alias("version_code"),
                  F.lit("조치 반영안").alias("version_name"), F.to_date("action_ts").alias("version_date"),
                  F.round(F.col("base_ss") + F.col("cum_gain"), 1).alias("selfsuff_pct"),
                  F.round(F.col("base_pe") + F.col("cum_pe"), 1).alias("primary_energy_kwh_m2y"),
                  F.col("base_pv").alias("pv_kw"), F.col("base_geo").alias("geothermal_kw"),
                  F.concat(F.lit("보완안 적용: "), F.col("option_names")).alias("change_note"),
                  F.lit("현행").alias("version_status"), "version_no", F.col("action_id").alias("source_action_id"), "site_code"))
design = dv.withColumn("source_action_id", F.lit(None).cast("string")).select(*[c for c in new_dv.columns if c != "site_code"]) \
           .unionByName(new_dv.drop("site_code"))
design = (design.withColumn("_rn", F.row_number().over(W.partitionBy("bim_model_id").orderBy(F.col("version_no").desc())))
                .withColumn("version_status", F.when(F.col("_rn") == 1, "현행").otherwise("이전")).drop("_rn"))
save(design, "silver.bim_design_version")

# 설비 계획 + 승인된 보완안 설비
eq = B("pms_equipment_plan").withColumn("added_by_action_id", F.lit(None).cast("string"))
new_eq = (applied.join(new_dv.select(F.col("source_action_id").alias("action_id"), F.col("version_id").alias("design_version_id")), "action_id")
          .select(F.concat(F.col("site_code"), F.lit("-"), F.col("option_id")).alias("wbs_code"), "site_code", "design_version_id", "category_code",
                  F.col("option_name").alias("equipment_name"), F.lit(None).cast("double").alias("capacity"), F.lit(None).cast("string").alias("capacity_unit"),
                  F.col("selfsuff_gain_pp").alias("selfsuff_contribution_pp"), F.col("cost_krw").alias("planned_cost_krw"),
                  F.col("action_id").alias("added_by_action_id")))
save(eq.unionByName(new_eq.select(*eq.columns)), "silver.pms_equipment_plan")

# 공급사, 발주 + 납기 변경·공급사 변경 이벤트
save(B("scm_vendor"), "silver.scm_vendor")
po = B("scm_purchase_order")
ev = B("scm_po_event").withColumn("event_ts", F.to_timestamp("event_time"))
save(ev.drop("event_time"), "silver.scm_po_event")
w_last = W.partitionBy("po_no").orderBy(F.col("event_ts").desc(), F.col("event_id").desc())
last_eta = (ev.where(F.col("new_expected_date").isNotNull()).withColumn("_rn", F.row_number().over(w_last)).where("_rn = 1")
              .select("po_no", F.col("new_expected_date").alias("_ev_eta"), F.col("reason").alias("last_change_reason"), F.col("event_ts").alias("last_change_at")))
last_vendor = (ev.where(F.col("new_vendor_code").isNotNull()).withColumn("_rn", F.row_number().over(w_last)).where("_rn = 1")
                 .select("po_no", F.col("new_vendor_code").alias("_ev_vendor")))
ev_cnt = ev.groupBy("po_no").agg(F.count("*").alias("change_event_count"))
purchase_order = (po.join(last_eta, "po_no", "left").join(last_vendor, "po_no", "left").join(ev_cnt, "po_no", "left")
                  .withColumn("original_vendor_code", F.col("vendor_code"))
                  .withColumn("vendor_code", F.coalesce("_ev_vendor", "vendor_code"))
                  .withColumn("original_expected_date", F.col("expected_date"))
                  .withColumn("expected_date", F.coalesce("_ev_eta", "expected_date"))
                  .withColumn("change_event_count", F.coalesce("change_event_count", F.lit(0)))
                  .withColumn("status", F.when(F.col("delivered_date").isNotNull(), "입고완료").otherwise(F.col("status")))
                  .drop("_ev_eta", "_ev_vendor"))
save(purchase_order, "silver.scm_purchase_order")

# 인증 목표·취득 인증서·인증 일정, 보완안
save(B("pms_cert_target"), "silver.pms_cert_target")
save(B("pms_certificate"), "silver.pms_certificate")
save(B("pms_cert_milestone"), "silver.pms_cert_milestone")
applied_ids = applied.select("option_id", F.col("action_id").alias("applied_action_id")).dropDuplicates(["option_id"])
save(opts.join(applied_ids, "option_id", "left").withColumn("is_applied", F.col("applied_action_id").isNotNull()), "silver.sim_improvement_option")

# %% [markdown]
# ## 5. 정리 결과 확인
#
# 시도 표기가 제대로 맞춰졌는지 확인합니다.
#
# **예상 결과:** 두 표가 나옵니다.
#
# 1. `시도를 정하지 못한 원천 값`: 1행. 원천 값이 비어 있는 1건뿐이고, 나머지 표기는 모두 시도로 바뀌었습니다.
# 2. BF 인증에서 `전북`으로 바뀐 원천 표기: 2행. `전라북도` 1,125건, `전북특별자치도` 167건

# %%
unmatched = (spark.table("silver.gseed_certification").where("sido is null").select("sido_raw")
             .unionByName(spark.table("silver.bf_certification").where("sido is null").select("sido_raw"))
             .unionByName(spark.table("silver.zeb_certification").where("sido is null").select("sido_raw"))
             .groupBy("sido_raw").count())
print("시도를 정하지 못한 원천 값:")
display(unmatched)
print("전북 표기 통일 예시 (BF 인증):")
display(spark.table("silver.bf_certification").where("sido = '전북'").groupBy("sido_raw").count())

# %% [markdown]
# 다음 단계: `04_gold_model`에서 보고서·온톨로지·에이전트가 함께 쓰는 Gold 테이블을 만듭니다.
