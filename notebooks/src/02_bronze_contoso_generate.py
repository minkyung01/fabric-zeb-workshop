# %% [markdown]
# # 02. Bronze ② Contoso 건설 내부 시스템 데이터 만들기
# 
# Contoso 건설의 **가상** 내부 시스템 데이터를 만듭니다. 회사·현장·공급사·사람 이름과 수치는 모두 실습용으로 만든 값입니다.
# 값이 고정되어 있어 몇 번을 실행해도 결과가 같고, 다시 실행하면 **실습을 처음 시작할 때의 상태로 돌아갑니다.**
# 
# 실제 건설사처럼 **시스템마다 코드 체계가 다릅니다.** 같은 현장이라도 ERP는 프로젝트 번호, 공사관리(PMS)는 현장 코드,
# BIM·에너지 시뮬레이션은 모델 번호를 쓰며, 세 코드의 대응 관계는 기준정보(MDM) 매핑표에 있습니다.
# 
# | 원천 시스템(가상) | Bronze 테이블 | 키 | 내용 |
# |---|---|---|---|
# | ERP | `erp_project` | 프로젝트 번호 `CT-24-0189` | 8개 프로젝트, 발주처 구분, 준공 예정일, 인센티브 |
# | 공사관리(PMS) | `pms_site`, `pms_equipment_plan`, `pms_cert_target`, `pms_certificate`, `pms_cert_milestone`, `pms_action_log` | 현장 코드 `HS-D`, WBS `HS-D-GEO` | 공정률, 설비 계획, 인증 목표·취득 인증서·인증 일정, 조치 기록 |
# | 기준정보(MDM) | `mdm_site_xref` | — | ERP 프로젝트 번호 ↔ PMS 현장 코드 ↔ BIM 모델 번호 |
# | BIM·에너지 시뮬레이션 | `bim_design_version` | 모델 번호 `BIM-0397` | 설계안별 에너지자립률·1차에너지소요량 |
# | 구매(SCM) | `scm_vendor`, `scm_purchase_order`, `scm_po_event` | 거래처 코드 `V-30452`, 발주 번호 | 공급사, 발주(WBS 연결), 납기 변경 이벤트 |
# | 에너지 컨설팅 | `sim_improvement_option` | 보완안 번호 | 등급 보완안 시뮬레이션 결과 |
# | 기준 정보 | `ref_zeb_grade_criteria`, `ref_region`, `ref_equipment_category` | — | 인증 등급 기준, 시도, 설비 분야 |
# 
# `ref_zeb_grade_criteria`는 제로에너지건축물 인증시스템(zeb.energy.or.kr)의 **인증 등급 기준값**입니다.
# 등급을 어떻게 판정하는지(두 기준 중 더 좋은 등급, BEMS 필수 등)는 이 테이블에 없고, 06장에서 **온톨로지의 업무 규칙**으로 정의합니다.
#
# 맨 위 셀부터 한 셀씩 실행합니다. 전체 실행에 약 2분 걸립니다.

# %% [parameters]
as_of_date = "2026-09-30"

# %% [markdown]
# ## 0. 준비
#
# 기준일(`as_of_date`)과 테이블 저장 함수 `save`를 정합니다. 저장할 때 출처(`_source`)와 생성 시각(`_generated_at`)을 함께 기록합니다.
#
# **예상 결과:** 결과 없이 끝납니다.

# %%
from datetime import date, timedelta
from pyspark.sql import functions as F

spark.sql("CREATE SCHEMA IF NOT EXISTS bronze")
AS_OF = date.fromisoformat(as_of_date)
SOURCE = "Contoso 건설 가상 데이터(데모용)"

def d(s):
    return date.fromisoformat(s) if s else None

def save(rows, table, ddl, source=SOURCE):
    df = spark.createDataFrame(rows, ddl).withColumn("_source", F.lit(source)).withColumn("_generated_at", F.current_timestamp())
    df.write.mode("overwrite").option("overwriteSchema", "true").saveAsTable(table)
    print(f"{table:<34} {spark.table(table).count():>5,}행")

# %% [markdown]
# ## 1. 기준 정보 — 인증 등급 기준값, 시도, 설비 분야
#
# ZEB 등급은 `+`(ZEB+)가 가장 높고 1 → 5등급 순서로 낮아집니다. 등급마다 **에너지자립률 하한**과 **1차에너지소요량 기준값**(주거용/주거용 이외)이 있습니다.
# 시도 표에는 원천마다 다르게 쓰는 표기(`경기도`, `경기`, `서울시` …)를 하나로 맞출 때 쓸 별칭(`aliases`)을 함께 적어 둡니다.
#
# **예상 결과:** `bronze.ref_zeb_grade_criteria 6행`, `bronze.ref_region 17행`, `bronze.ref_equipment_category 8행`

# %%
# 제로에너지건축물 인증 등급 기준값 (에너지자립률 하한 %, 1차에너지소요량 상한 kWh/㎡·년 — 주거용/주거용 이외)
grade_criteria = [
    ("+", "ZEB+", 120.0, -10.0, -70.0),
    ("1", "1등급", 100.0, 10.0, -30.0),
    ("2", "2등급", 80.0, 30.0, 10.0),
    ("3", "3등급", 60.0, 50.0, 50.0),
    ("4", "4등급", 40.0, 70.0, 90.0),
    ("5", "5등급", 20.0, 90.0, 130.0),
]
save(grade_criteria, "bronze.ref_zeb_grade_criteria",
     "grade_code string, grade_name string, selfsuff_min_pct double, primary_energy_limit_residential double, primary_energy_limit_nonresidential double",
     source="제로에너지건축물 인증시스템 인증제도 기준(zeb.energy.or.kr)")

regions = [
    ("서울", "서울특별시", "서울특별시|서울시|서울", 37.5665, 126.9780, "수도권"),
    ("인천", "인천광역시", "인천광역시|인천시", 37.4563, 126.7052, "수도권"),
    ("경기", "경기도", "경기도|경기|김포|평택시|과천지식정보타운", 37.4138, 127.5183, "수도권"),
    ("강원", "강원특별자치도", "강원특별자치도|강원도|강원", 37.8228, 128.1555, "강원"),
    ("대전", "대전광역시", "대전광역시|대전시", 36.3504, 127.3845, "충청"),
    ("세종", "세종특별자치시", "세종특별자치시|세종시|세종", 36.4800, 127.2890, "충청"),
    ("충북", "충청북도", "충청북도|충북", 36.8000, 127.7000, "충청"),
    ("충남", "충청남도", "충청남도|충남", 36.5184, 126.8000, "충청"),
    ("광주", "광주광역시", "광주광역시|광주시", 35.1595, 126.8526, "호남"),
    ("전북", "전북특별자치도", "전북특별자치도|전라북도|전북", 35.7175, 127.1530, "호남"),
    ("전남", "전라남도", "전라남도|전남|남악신도시(오룡지구)", 34.8679, 126.9910, "호남"),
    ("대구", "대구광역시", "대구광역시|대구시", 35.8714, 128.6014, "영남"),
    ("부산", "부산광역시", "부산광역시|부산시|부산", 35.1796, 129.0756, "영남"),
    ("울산", "울산광역시", "울산광역시|울산시", 35.5384, 129.3114, "영남"),
    ("경북", "경상북도", "경상북도|경북", 36.4919, 128.8889, "영남"),
    ("경남", "경상남도", "경상남도|경남", 35.4606, 128.2132, "영남"),
    ("제주", "제주특별자치도", "제주특별자치도|제주도|제주", 33.4890, 126.4983, "제주"),
]
save(regions, "bronze.ref_region", "sido string, sido_full string, aliases string, latitude double, longitude double, region_group string")

categories = [
    ("PV", "태양광", "에너지 생산", "태양전지|태양 전지용 BOS(Balance Of system) 주변 기기"),
    ("GEO", "지열 히트펌프", "에너지 생산", "지열 냉난방 기술"),
    ("EHP", "전기 히트펌프", "에너지 절감", "전기구동 히트펌프(EHP,ElectricHeatPump)"),
    ("FC", "연료전지", "에너지 생산", "건물용 PEMFC (핵심부품)|건물용 PEMFC (시스템 양산제조기술)|건물용 SOFC (구성요소 및 스택)"),
    ("ENV", "고효율 창호·외피", "에너지 절감", "고효율 외피시스템"),
    ("VENT", "전열교환 환기", "에너지 절감", "에코 실내 환기설비"),
    ("LIGHT", "고효율 조명·제어", "에너지 절감", ""),
    ("BEMS", "건물에너지관리시스템(BEMS)", "에너지 관리", ""),
]
save(categories, "bronze.ref_equipment_category", "category_code string, category_name string, zeb_role string, green_tech_classes string")

# %% [markdown]
# ## 2. ERP 프로젝트, PMS 현장, MDM 코드 매핑
# 
# 원천 시스템마다 시도 표기가 다르므로(`경기도`, `경기`, `경기 `, `서울시`, `전북특별자치도` 등) Silver에서 하나로 맞춥니다.
# 같은 현장도 ERP는 `CT-24-0189`, PMS는 `HS-D`, BIM은 `BIM-0397`로 부르고, MDM 매핑표가 이 세 코드를 연결합니다.
#
# **예상 결과:** `bronze.erp_project 8행`, `bronze.pms_site 8행`, `bronze.mdm_site_xref 8행`

# %%
# ERP: 프로젝트 번호, 이름, 시도(원천 표기), 시군구, 주용도, 세대수, 연면적, 발주처 구분, 착공일, 준공 예정일, PM, 인센티브
erp = [
    ("CT-24-0231", "에코시티 A단지", "경기도", "화성시", "공동주택", 1120, 128400.0, "민간", d("2025-03-10"), d("2027-06-30"), "김도윤", "용적률 완화"),
    ("CT-25-0107", "리버뷰 B단지", "인천광역시", "연수구", "공동주택", 860, 97300.0, "민간", d("2025-08-04"), d("2027-12-20"), "이서연", "용적률 완화"),
    ("CT-26-0044", "스마트오피스 C센터", "경기", "성남시", "업무시설", None, 42800.0, "민간", d("2027-02-01"), d("2028-12-29"), "박지호", None),
    ("CT-24-0189", "에코시티 D단지", "경기 ", "화성시", "공동주택", 1480, 171900.0, "민간", d("2024-11-18"), d("2027-03-31"), "최민준", "용적률 완화"),
    ("CT-26-0052", "세종 E학교", "세종특별자치시", "세종시", "교육연구시설", None, 18600.0, "공공", d("2027-03-02"), d("2028-08-31"), "정하은", None),
    ("CT-25-0078", "해운대 F청사", "부산", "해운대구", "업무시설", None, 24300.0, "공공", d("2025-05-12"), d("2027-04-30"), "강태윤", None),
    ("CT-25-0133", "전주 G도서관", "전북특별자치도", "전주시", "문화 및 집회시설", None, 9800.0, "공공", d("2025-10-01"), d("2027-05-31"), "윤지아", None),
    ("CT-26-0091", "마포 H단지", "서울시", "마포구", "공동주택", 540, 61200.0, "민간", d("2027-04-01"), d("2029-10-31"), "한도현", None),
]
save(erp, "bronze.erp_project",
     "project_no string, project_name string, sido_raw string, sigungu string, main_use string, households int, gross_floor_area_m2 double, "
     "client_type string, start_date date, planned_completion_date date, pm_name string, zeb_incentive string")

# PMS: 현장 코드, 현장명, 단계, 공정률
sites = [
    ("HS-A", "에코시티 A단지 현장", "시공", 58.0), ("IC-B", "리버뷰 B단지 현장", "시공", 41.0),
    ("SN-C", "스마트오피스 C센터 현장", "설계", 0.0), ("HS-D", "에코시티 D단지 현장", "시공", 72.0),
    ("SJ-E", "세종 E학교 현장", "설계", 0.0), ("BS-F", "해운대 F청사 현장", "시공", 63.0),
    ("JJ-G", "전주 G도서관 현장", "시공", 35.0), ("MP-H", "마포 H단지 현장", "설계", 0.0),
]
save([(s, n, st, pr, AS_OF) for s, n, st, pr in sites], "bronze.pms_site",
     "site_code string, site_name string, stage string, progress_pct double, progress_as_of date")

# MDM: 같은 현장을 가리키는 시스템별 코드
xref = [
    ("CT-24-0231", "HS-A", "BIM-0412"), ("CT-25-0107", "IC-B", "BIM-0518"), ("CT-26-0044", "SN-C", "BIM-0633"),
    ("CT-24-0189", "HS-D", "BIM-0397"), ("CT-26-0052", "SJ-E", "BIM-0641"), ("CT-25-0078", "BS-F", "BIM-0455"),
    ("CT-25-0133", "JJ-G", "BIM-0529"), ("CT-26-0091", "MP-H", "BIM-0620"),
]
save([(p, s, b, d("2024-01-02")) for p, s, b in xref], "bronze.mdm_site_xref",
     "project_no string, site_code string, bim_model_id string, valid_from date")

SITE_OF = {p: s for p, s, _ in xref}
BIM_OF = {s: b for _, s, b in xref}
COMPLETION = {SITE_OF[r[0]]: r[9] for r in erp}
START = {SITE_OF[r[0]]: r[8] for r in erp}

# %% [markdown]
# ## 3. 설계안 — BIM·에너지 시뮬레이션
# 
# D단지는 예비인증(4등급, 설계안 V2: 자립률 43.5%)을 받은 뒤 **원가 절감(VE)으로 옥상 태양광을 줄여** V3에서 자립률이 38.2%로 낮아졌습니다.
# B단지는 자립률이 40% 미만이지만 1차에너지소요량이 낮습니다.
# 현장마다 가장 최근 설계안이 `현행`이고, 나머지는 `이전`입니다.
#
# **예상 결과:** `bronze.bim_design_version 18행`

# %%
# (현장, 설계안 번호, 이름, 날짜, 에너지자립률 %, 1차에너지소요량 kWh/㎡·년, 태양광 kW, 지열 kW, 변경 내용)
dv = [
    ("HS-A", 1, "기본설계", "2024-06-14", 41.2, 72.0, 480.0, 700.0, "기본설계 에너지 시뮬레이션"),
    ("HS-A", 2, "예비인증 제출안", "2024-11-22", 44.0, 66.0, 520.0, 700.0, "태양광 +40kW, 창호 성능 상향"),
    ("IC-B", 1, "기본설계", "2025-02-10", 36.5, 71.0, 360.0, 0.0, "기본설계 에너지 시뮬레이션"),
    ("IC-B", 2, "예비인증 제출안", "2025-05-20", 39.0, 65.0, 400.0, 0.0, "태양광 +40kW, 외단열 강화로 1차에너지소요량 감소"),
    ("SN-C", 1, "기본설계", "2026-05-08", 58.0, 88.0, 260.0, 350.0, "기본설계 에너지 시뮬레이션"),
    ("SN-C", 2, "계획설계", "2026-09-04", 63.0, 82.0, 300.0, 350.0, "태양광 +40kW, 조명 제어 적용"),
    ("HS-D", 1, "기본설계", "2024-05-17", 41.0, 74.0, 500.0, 600.0, "기본설계 에너지 시뮬레이션"),
    ("HS-D", 2, "예비인증 제출안", "2024-08-09", 43.5, 69.0, 530.0, 600.0, "태양광 +30kW, 창호 성능 상향"),
    ("HS-D", 3, "VE 반영안", "2026-07-15", 38.2, 76.0, 380.0, 600.0, "원가 절감(VE)으로 옥상 태양광 530→380kW 축소"),
    ("SJ-E", 1, "기본설계", "2026-04-17", 60.5, 58.0, 160.0, 200.0, "기본설계 에너지 시뮬레이션"),
    ("SJ-E", 2, "예비인증 제출안", "2026-07-10", 64.2, 52.0, 180.0, 200.0, "태양광 +20kW, 외피 성능 상향"),
    ("BS-F", 1, "기본설계", "2024-10-11", 80.1, 12.0, 400.0, 0.0, "기본설계 에너지 시뮬레이션"),
    ("BS-F", 2, "예비인증 제출안", "2025-01-24", 82.5, 8.0, 420.0, 0.0, "태양광 +20kW, 조명 제어 적용"),
    ("JJ-G", 1, "기본설계", "2025-03-14", 57.0, 60.0, 140.0, 120.0, "기본설계 에너지 시뮬레이션"),
    ("JJ-G", 2, "예비인증 제출안", "2025-06-20", 61.0, 55.0, 150.0, 120.0, "태양광 +10kW, 조명 제어 적용"),
    ("MP-H", 1, "기본설계", "2026-03-13", 31.0, 88.0, 230.0, 0.0, "기본설계 에너지 시뮬레이션"),
    ("MP-H", 2, "창호 성능 상향안", "2026-06-05", 34.2, 84.0, 230.0, 0.0, "창호 로이 3중 유리 적용 (+3.2%p)"),
    ("MP-H", 3, "태양광 증설안", "2026-09-11", 36.0, 82.0, 260.0, 0.0, "옥상 태양광 +30kW (+1.8%p)"),
]
latest_no = {}
for s, n, *_ in dv:
    latest_no[s] = max(latest_no.get(s, 0), n)
design_versions = [(f"{BIM_OF[s]}-V{n}", BIM_OF[s], f"V{n}", name, d(dt), ss, pe, pv, geo, note, "현행" if n == latest_no[s] else "이전")
                   for s, n, name, dt, ss, pe, pv, geo, note in dv]
save(design_versions, "bronze.bim_design_version",
     "version_id string, bim_model_id string, version_code string, version_name string, version_date date, selfsuff_pct double, "
     "primary_energy_kwh_m2y double, pv_kw double, geothermal_kw double, change_note string, version_status string")
CURRENT_VERSION = {s: f"{BIM_OF[s]}-V{latest_no[s]}" for s in latest_no}

# %% [markdown]
# ## 4. 인증 목표와 취득 인증서 — PMS
# 
# 예비인증서에는 **어느 설계안으로 받았는지**(`design_version_id`)가 함께 기록됩니다.
# 세종 E학교는 ZEB·녹색건축·BF **세 가지 인증**을 목표로 합니다.
#
# **예상 결과:** `bronze.pms_cert_target 12행`, `bronze.pms_certificate 10행`

# %%
cert_targets = [
    ("HS-A", "ZEB", "4", "예비인증 등급 유지"), ("IC-B", "ZEB", "4", "예비인증 등급 유지"), ("SN-C", "ZEB", "3", "사내 목표"),
    ("HS-D", "ZEB", "4", "예비인증 등급 유지"), ("SJ-E", "ZEB", "3", "발주처 요구"), ("SJ-E", "G-SEED", "우수", "발주처 요구"),
    ("SJ-E", "BF", "최우수", "발주처 요구"), ("BS-F", "ZEB", "2", "발주처 요구"), ("BS-F", "BF", "우수", "발주처 요구"),
    ("JJ-G", "ZEB", "3", "발주처 요구"), ("JJ-G", "BF", "최우수", "발주처 요구"), ("MP-H", "ZEB", "4", "사내 ESG 목표"),
]
save([(f"{s}-{t}", s, t, g, b) for s, t, g, b in cert_targets], "bronze.pms_cert_target",
     "target_id string, site_code string, cert_type string, target_grade string, basis string")

# (인증서 번호, 현장, 인증 종류, 인증 구분, 등급, 인증일, 기준 설계안, 인증기관)
certificates = [
    ("ZEB-P-2024-1287", "HS-A", "ZEB", "예비인증", "4", "2024-12-20", f"{BIM_OF['HS-A']}-V2", "한국에너지공단"),
    ("ZEB-P-2025-0642", "IC-B", "ZEB", "예비인증", "4", "2025-06-12", f"{BIM_OF['IC-B']}-V2", "한국에너지공단"),
    ("ZEB-P-2024-0831", "HS-D", "ZEB", "예비인증", "4", "2024-08-30", f"{BIM_OF['HS-D']}-V2", "한국에너지공단"),
    ("ZEB-P-2026-0915", "SJ-E", "ZEB", "예비인증", "3", "2026-08-14", f"{BIM_OF['SJ-E']}-V2", "한국에너지공단"),
    ("ZEB-P-2025-0233", "BS-F", "ZEB", "예비인증", "2", "2025-02-27", f"{BIM_OF['BS-F']}-V2", "한국에너지공단"),
    ("ZEB-P-2025-0718", "JJ-G", "ZEB", "예비인증", "3", "2025-07-03", f"{BIM_OF['JJ-G']}-V2", "한국에너지공단"),
    ("GS-P-2026-1102", "SJ-E", "G-SEED", "예비인증", "우수", "2026-09-18", f"{BIM_OF['SJ-E']}-V2", "한국부동산원"),
    ("BF-P-2026-2210", "SJ-E", "BF", "예비인증", "우수", "2026-09-25", f"{BIM_OF['SJ-E']}-V2", "한국장애인개발원"),
    ("BF-P-2025-0391", "BS-F", "BF", "예비인증", "우수", "2025-03-20", f"{BIM_OF['BS-F']}-V2", "한국장애인개발원"),
    ("BF-P-2025-0957", "JJ-G", "BF", "예비인증", "최우수", "2025-08-11", f"{BIM_OF['JJ-G']}-V2", "한국장애인개발원"),
]
save([(c, s, t, st, g, d(dt), v, org) for c, s, t, st, g, dt, v, org in certificates], "bronze.pms_certificate",
     "cert_no string, site_code string, cert_type string, cert_stage string, grade string, cert_date date, design_version_id string, issuer string")
PRELIM_DATE = {s: d(dt) for _, s, t, _, _, dt, _, _ in certificates if t == "ZEB"}

# %% [markdown]
# ## 5. 인증 일정 — PMS
# 
# 설비 설치를 마쳐야 본인증을 신청할 수 있습니다. 일정 계획은 현장마다 같은 기준(준공 121일 전 설비 설치 완료, 75일 전 본인증 신청, 30일 전 본인증 취득)으로 세웁니다.
#
# **예상 결과:** `bronze.pms_cert_milestone 48행` (현장 8개 × 일정 6단계)

# %%
milestones = []
for s in COMPLETION:
    comp, start = COMPLETION[s], START[s]
    plan_rows = [
        ("예비인증 취득", PRELIM_DATE.get(s) or (start - timedelta(days=60))),
        ("착공", start),
        ("설비 설치 완료", comp - timedelta(days=121)),
        ("본인증 신청", comp - timedelta(days=75)),
        ("본인증 취득", comp - timedelta(days=30)),
        ("사용승인", comp),
    ]
    for seq, (mtype, planned) in enumerate(plan_rows, 1):
        actual = planned if planned <= AS_OF else None
        milestones.append((f"{s}-M{seq}", s, seq, mtype, planned, actual))
save(milestones, "bronze.pms_cert_milestone",
     "milestone_id string, site_code string, seq int, milestone_type string, planned_date date, actual_date date")

# %% [markdown]
# ## 6. 설비 계획(PMS)과 공급사·발주(SCM)
# 
# 발주는 **WBS 코드**(`wbs_element`)로 PMS 설비 계획과 이어집니다. **Northwind 지열**이 A단지와 D단지의 지열 히트펌프를 납품합니다.
# 스마트오피스 C센터는 설비 계획에 BEMS가 빠져 있습니다(실습을 위해 일부러 넣은 상황).
# 리버뷰 B단지 창호 발주 1건에는 납기 변경 이벤트(+5일)가 있으며, 이 이벤트는 Silver에서 반영합니다.
#
# **예상 결과:** `bronze.pms_equipment_plan 39행`, `bronze.scm_vendor 9행`, `bronze.scm_purchase_order 25행`, `bronze.scm_po_event 1행`

# %%
# (현장, [(분야, 설비명, 용량, 단위, 자립률 기여 %p, 예산)])
plan = {
    "HS-A": [("PV", "옥상 태양광", 520, "kW", 24.0, 1.56e9), ("GEO", "지열 히트펌프", 700, "kW", 15.0, 2.45e9),
             ("ENV", "고효율 창호", None, None, 3.2, 3.90e9), ("VENT", "전열교환 환기", 1120, "세대", 1.8, 1.68e9), ("BEMS", "BEMS", 1, "식", 0.0, 1.8e8)],
    "IC-B": [("PV", "옥상 태양광", 400, "kW", 21.5, 1.20e9), ("EHP", "전기 히트펌프", 900, "kW", 10.0, 1.35e9),
             ("ENV", "고효율 창호·외단열", None, None, 5.0, 3.10e9), ("VENT", "전열교환 환기", 860, "세대", 2.5, 1.29e9), ("BEMS", "BEMS", 1, "식", 0.0, 1.5e8)],
    "SN-C": [("PV", "옥상·외벽 태양광", 300, "kW", 30.0, 9.0e8), ("GEO", "지열 히트펌프", 350, "kW", 25.0, 1.23e9),
             ("ENV", "고효율 커튼월", None, None, 5.0, 2.40e9), ("LIGHT", "LED 조명·조명 제어", 1, "식", 3.0, 3.2e8)],
    "HS-D": [("PV", "옥상 태양광", 380, "kW", 22.4, 1.14e9), ("GEO", "지열 히트펌프", 600, "kW", 12.6, 2.10e9),
             ("ENV", "고효율 창호", None, None, 2.1, 4.80e9), ("VENT", "전열교환 환기", 1480, "세대", 1.1, 2.22e9), ("BEMS", "BEMS", 1, "식", 0.0, 2.0e8)],
    "SJ-E": [("PV", "옥상 태양광", 180, "kW", 34.0, 5.4e8), ("GEO", "지열 히트펌프", 200, "kW", 24.0, 7.0e8),
             ("ENV", "고효율 창호", None, None, 4.2, 9.0e8), ("VENT", "전열교환 환기", 1, "식", 2.0, 2.6e8), ("BEMS", "BEMS", 1, "식", 0.0, 1.2e8)],
    "BS-F": [("PV", "옥상·주차장 태양광", 420, "kW", 46.0, 1.26e9), ("FC", "연료전지", 100, "kW", 28.0, 1.90e9),
             ("ENV", "고효율 커튼월", None, None, 5.5, 1.60e9), ("LIGHT", "LED 조명·조명 제어", 1, "식", 3.0, 2.1e8), ("BEMS", "BEMS", 1, "식", 0.0, 1.4e8)],
    "JJ-G": [("PV", "옥상 태양광", 150, "kW", 33.0, 4.5e8), ("GEO", "지열 히트펌프", 120, "kW", 22.0, 4.2e8),
             ("ENV", "고효율 창호", None, None, 4.0, 5.2e8), ("LIGHT", "LED 조명·조명 제어", 1, "식", 2.0, 9.0e7), ("BEMS", "BEMS", 1, "식", 0.0, 8.0e7)],
    "MP-H": [("PV", "옥상 태양광", 260, "kW", 20.0, 7.8e8), ("EHP", "전기 히트펌프", 560, "kW", 9.8, 8.4e8),
             ("ENV", "고효율 창호(로이 3중)", None, None, 4.2, 1.90e9), ("VENT", "전열교환 환기", 540, "세대", 2.0, 8.1e8), ("BEMS", "BEMS", 1, "식", 0.0, 1.1e8)],
}
equipment = []
for s, rows in plan.items():
    for cat, name, cap, unit, pp, cost in rows:
        equipment.append((f"{s}-{cat}", s, CURRENT_VERSION[s], cat, name, None if cap is None else float(cap), unit, pp, int(cost)))
save(equipment, "bronze.pms_equipment_plan",
     "wbs_code string, site_code string, design_version_id string, category_code string, equipment_name string, capacity double, "
     "capacity_unit string, selfsuff_contribution_pp double, planned_cost_krw long")

vendors = [
    ("V-20118", "Fabrikam 솔라", "PV", 60, 0.94, False, "태양광 모듈·인버터"),
    ("V-30452", "Northwind 지열", "GEO", 90, 0.78, False, "지열 히트펌프"),
    ("V-11873", "Litware 창호", "ENV", 75, 0.91, False, "고효율 창호·커튼월"),
    ("V-40219", "Tailspin 환기", "VENT", 45, 0.95, False, "전열교환 환기장치"),
    ("V-50331", "Proseware BEMS", "BEMS", 40, 0.97, False, "건물에너지관리시스템"),
    ("V-60127", "Wingtip 에너지", "EHP", 70, 0.90, False, "전기 히트펌프·연료전지"),
    ("V-20564", "Woodgrove 솔라", "PV", 50, 0.92, True, "태양광 모듈(대체 공급 가능)"),
    ("V-30977", "Alpine 지열", "GEO", 55, 0.90, True, "지열 히트펌프(대체 공급 가능, 재고 보유)"),
    ("V-70045", "Adatum 조명", "LIGHT", 30, 0.96, False, "LED 조명·조명 제어"),
]
save(vendors, "bronze.scm_vendor",
     "vendor_code string, vendor_name string, category_code string, standard_lead_time_days int, on_time_rate double, "
     "is_alternative_pool boolean, note string")

# 시공 중인 현장(A·B·D·F·G)만 발주가 있습니다. (WBS, 거래처, 발주일, 약속 납기, 예상 입고, 입고일)
po_spec = [
    ("HS-D-PV", "V-20118", "2026-06-02", "2026-10-20", "2026-10-22", None),
    ("HS-D-GEO", "V-30452", "2026-05-18", "2026-11-10", "2026-11-12", None),
    ("HS-D-ENV", "V-11873", "2025-11-03", "2026-06-15", "2026-06-15", "2026-06-15"),
    ("HS-D-VENT", "V-40219", "2026-06-20", "2026-10-05", "2026-10-05", None),
    ("HS-D-BEMS", "V-50331", "2026-08-01", "2026-11-02", "2026-11-02", None),
    ("HS-A-PV", "V-20118", "2026-08-10", "2026-12-01", "2026-12-01", None),
    ("HS-A-GEO", "V-30452", "2026-07-06", "2026-12-15", "2026-12-18", None),
    ("HS-A-ENV", "V-11873", "2026-06-15", "2026-11-20", "2026-11-20", None),
    ("HS-A-VENT", "V-40219", "2026-09-07", "2027-01-10", "2027-01-10", None),
    ("HS-A-BEMS", "V-50331", "2026-09-21", "2027-01-20", "2027-01-20", None),
    ("IC-B-PV", "V-20564", "2026-09-14", "2027-05-10", "2027-05-10", None),
    ("IC-B-EHP", "V-60127", "2026-09-14", "2027-06-01", "2027-06-01", None),
    ("IC-B-ENV", "V-11873", "2026-08-24", "2027-04-15", "2027-04-15", None),
    ("IC-B-VENT", "V-40219", "2026-09-28", "2027-06-20", "2027-06-20", None),
    ("IC-B-BEMS", "V-50331", "2026-09-28", "2027-07-01", "2027-07-01", None),
    ("BS-F-PV", "V-20118", "2026-04-06", "2026-08-28", "2026-08-28", "2026-08-28"),
    ("BS-F-FC", "V-60127", "2026-06-08", "2026-11-16", "2026-11-20", None),
    ("BS-F-ENV", "V-11873", "2025-12-01", "2026-07-10", "2026-07-10", "2026-07-10"),
    ("BS-F-LIGHT", "V-70045", "2026-08-17", "2026-10-30", "2026-10-30", None),
    ("BS-F-BEMS", "V-50331", "2026-09-01", "2026-11-25", "2026-11-25", None),
    ("JJ-G-PV", "V-20564", "2026-08-03", "2026-11-25", "2026-11-25", None),
    ("JJ-G-GEO", "V-30977", "2026-07-20", "2026-12-10", "2026-12-10", None),
    ("JJ-G-ENV", "V-11873", "2026-06-29", "2026-10-30", "2026-10-30", None),
    ("JJ-G-LIGHT", "V-70045", "2026-09-14", "2026-12-01", "2026-12-01", None),
    ("JJ-G-BEMS", "V-50331", "2026-09-14", "2026-12-15", "2026-12-15", None),
]
cost_of = {e[0]: e[8] for e in equipment}
purchase_orders = []
for i, (wbs, vendor, od, prom, eta, gr) in enumerate(po_spec, 1):
    status = "입고완료" if gr else ("출하준비" if (d(eta) - AS_OF).days <= 10 else "생산중")
    purchase_orders.append((f"45000{31200 + i}", wbs, vendor, d(od), d(prom), d(eta), d(gr), status, cost_of[wbs]))
save(purchase_orders, "bronze.scm_purchase_order",
     "po_no string, wbs_element string, vendor_code string, order_date date, promised_date date, expected_date date, "
     "delivered_date date, status string, amount_krw long")

po_of = {p[1]: p[0] for p in purchase_orders}
po_events = [("EV-0001", po_of["IC-B-ENV"], "납기변경", d("2027-04-20"), None, "창호 유리 사양 확정 지연(+5일)", "2026-09-10 09:30:00", "SCM")]
save(po_events, "bronze.scm_po_event",
     "event_id string, po_no string, event_type string, new_expected_date date, new_vendor_code string, reason string, event_time string, source_system string")

# %% [markdown]
# ## 7. 등급 보완안 — 에너지 컨설팅 시뮬레이션 결과, 조치 기록
#
# 보완안마다 적용했을 때 **에너지자립률이 몇 %p 오르는지(`selfsuff_gain_pp`), 1차에너지소요량이 얼마나 줄어드는지(`primary_energy_delta`)**,
# 비용과 준비 기간이 얼마인지 들어 있습니다. D단지 6개, H단지 5개, C센터 1개입니다.
#
# `pms_action_log`(조치 기록)는 **처음에는 비어 있습니다.** 11장에서 담당자가 Teams에서 보완안을 승인하면 이 테이블에 기록이 추가되고,
# Silver가 그 기록을 읽어 새 설계안을 만듭니다. 이 Notebook을 다시 실행하면 조치 기록도 지워져 **실습 처음 상태로 돌아갑니다.**
#
# **예상 결과:** `bronze.sim_improvement_option 12행`, `bronze.pms_action_log 0행`

# %%
options = [
    ("OPT-D1", "HS-D", "옥상 태양광 원설계 복원(+150kW)", "PV", 5.3, -6.0, 420_000_000, 60),
    ("OPT-D2", "HS-D", "주차장 캐노피 태양광(+90kW)", "PV", 3.2, -3.5, 230_000_000, 45),
    ("OPT-D3", "HS-D", "발코니 BIPV(+40kW)", "PV", 1.4, -1.5, 280_000_000, 75),
    ("OPT-D4", "HS-D", "창호 성능 상향(로이 3중)", "ENV", 2.1, -4.0, 340_000_000, 50),
    ("OPT-D5", "HS-D", "전열교환 환기 효율 상향", "VENT", 1.0, -2.0, 60_000_000, 30),
    ("OPT-D6", "HS-D", "공용부 LED·조명 제어", "LIGHT", 0.9, -1.8, 50_000_000, 20),
    ("OPT-H1", "MP-H", "옥상 태양광 증설(+60kW)", "PV", 2.2, -2.5, 160_000_000, 40),
    ("OPT-H2", "MP-H", "창호 추가 상향", "ENV", 1.5, -3.0, 190_000_000, 50),
    ("OPT-H3", "MP-H", "지열 히트펌프 도입", "GEO", 4.6, -8.0, 650_000_000, 90),
    ("OPT-H4", "MP-H", "발코니 BIPV(+50kW)", "PV", 1.9, -2.0, 220_000_000, 70),
    ("OPT-H5", "MP-H", "전열교환 환기 효율 상향", "VENT", 0.8, -1.5, 40_000_000, 30),
    ("OPT-C1", "SN-C", "BEMS 도입", "BEMS", 0.0, 0.0, 180_000_000, 40),
]
save(options, "bronze.sim_improvement_option",
     "option_id string, site_code string, option_name string, category_code string, selfsuff_gain_pp double, "
     "primary_energy_delta double, cost_krw long, lead_time_days int")

# 조치 기록은 빈 테이블로 만듭니다.
save([], "bronze.pms_action_log",
     "action_id string, action_time string, site_code string, action_type string, detail_json string, approved_by string, source_system string")

# %% [markdown]
# ## 8. Bronze 테이블 확인
#
# **예상 결과:** 01·02 Notebook이 만든 Bronze 테이블 **21개**가 보입니다(공공 4개 + 수집 기록 1개 + Contoso 내부 16개).

# %%
display(spark.sql("SHOW TABLES IN bronze"))

# %% [markdown]
# ## 9. 같은 현장, 시스템마다 다른 코드
#
# 에코시티 D단지의 데이터를 시스템별로 찾아 봅니다. MDM 매핑표가 ERP 프로젝트 번호·PMS 현장 코드·BIM 모델 번호를 연결하고,
# 예비인증서에는 **어느 설계안으로 받았는지**(`design_version_id`)가 기록되어 있습니다.
#
# **예상 결과:** 3행이 나옵니다. 같은 현장(`CT-24-0189` = `HS-D` = `BIM-0397`)의 설계안 V1·V2·V3입니다.
# 예비인증서 `ZEB-P-2024-0831`(4등급)은 **V2**(자립률 43.5%)로 받았지만, 현재 설계안(`현행`)은 VE 반영안 **V3**(자립률 38.2%)입니다.
# ERP의 시도는 원천 표기인 `경기 `(뒤에 공백 포함)입니다.

# %%
display(spark.sql("""
    SELECT e.project_no, e.project_name, e.sido_raw, x.site_code, x.bim_model_id,
           v.version_code, v.version_name, v.selfsuff_pct, v.primary_energy_kwh_m2y, v.pv_kw, v.version_status,
           c.cert_no AS prelim_cert_no, c.grade AS prelim_grade
    FROM bronze.mdm_site_xref x
    JOIN bronze.erp_project e ON e.project_no = x.project_no
    JOIN bronze.bim_design_version v ON v.bim_model_id = x.bim_model_id
    LEFT JOIN bronze.pms_certificate c ON c.design_version_id = v.version_id AND c.cert_type = 'ZEB'
    WHERE x.site_code = 'HS-D'
    ORDER BY v.version_code"""))

# %% [markdown]
# 다음 단계: `03_silver_conform`에서 공공 데이터와 내부 데이터의 표기·형식을 맞춥니다.
