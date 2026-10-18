# %% [markdown]
# # 01. Bronze ① 공공 인증 데이터 수집
#
# 공공데이터포털(data.go.kr)에서 건축물 인증 데이터 4종을 **이 Notebook이 직접 내려받아** Bronze 테이블로 저장합니다.
# 내려받은 파일은 Lakehouse에 따로 두지 않고 메모리에서 바로 읽습니다.
#
# | Bronze 테이블 | 공공데이터 (데이터 ID) | 제공 기관 |
# |---|---|---|
# | `bronze.pub_zeb_cert` | 제로에너지건축물 인증현황 (15085042) | 한국에너지공단 |
# | `bronze.pub_gseed_cert` | 녹색건축 인증현황 (15003214) | 한국부동산원 |
# | `bronze.pub_bf_cert` | 장애물 없는 생활환경(BF) 인증 시설 정보 (15014781) | 한국장애인고용공단 |
# | `bronze.pub_green_tech_cert` | 녹색기술인증현황 (15054156) | 한국산업기술진흥원 |
#
# - Bronze에는 값을 **문자열 그대로** 보관하고 열 이름만 영문으로 바꿉니다. 정제는 `03_silver_conform`에서 합니다.
# - 어느 파일의 몇 번째 행인지(`source_row_num`, `_source_dataset_id`)와 적재 시각(`_ingested_at`)을 붙입니다.
# - 녹색기술 인증의 `사업자등록번호`는 실습에 필요하지 않아 수집하지 않습니다.
#
# 위에서부터 한 셀씩 실행합니다(**Shift+Enter**). 전체 실행 시간은 약 3–5분입니다.

# %% [parameters]
# 파라미터 — 파이프라인에서 덮어쓸 수 있습니다.
dataset_ids = "15085042,15003214,15014781,15054156"
# 포털에 접속할 수 없는 환경에서만 관리자가 지정합니다. 예: "Files/public" → Files/public/15085042.csv 를 읽습니다.
local_folder = ""

# %% [markdown]
# ## 1. 수집 대상과 열 이름 정의
#
# 데이터마다 저장할 Bronze 테이블, 최소 행 수, 한글 열 이름 → 영문 열 이름을 정합니다.
#
# **예상 결과:** `batch_id: …` 한 줄이 출력됩니다. 이번 적재를 구분하는 ID입니다.

# %%
import io, re, json, time, uuid
from datetime import datetime, timezone
import requests
import pandas as pd
from pyspark.sql import functions as F

BASE = "https://www.data.go.kr"
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"}

DATASETS = {
    "15085042": {"table": "bronze.pub_zeb_cert", "min_rows": 9000, "drop": [], "columns": {
        "인증구분": "cert_stage", "건물용도": "building_use_group", "건물주용도": "building_main_use",
        "에너지자립률": "energy_self_sufficiency", "지역": "region", "건축물명": "building_name",
        "업체명": "applicant_name", "제로에너지건축물 인증등급(ZEB)": "zeb_grade", "인증일자": "cert_date"}},
    "15003214": {"table": "bronze.pub_gseed_cert", "min_rows": 5000, "drop": [], "columns": {
        "인증번호": "cert_no", "시도": "sido", "인증기준": "cert_standard", "인증구분": "cert_stage",
        "건축물명": "building_name", "인증대상 건축물군": "building_group", "인증등급": "cert_grade",
        "인증일자": "cert_date", "건축물 주소": "address", "연면적": "gross_floor_area",
        "지상층수": "floors_above", "지하층수": "floors_below"}},
    "15014781": {"table": "bronze.pub_bf_cert", "min_rows": 20000, "drop": [], "columns": {
        "연번": "seq", "인증번호": "cert_no", "인증구분": "cert_stage", "인증등급": "cert_grade",
        "지역코드": "sido", "시군구": "sigungu", "지역(시설)명": "facility_name", "인증대상": "cert_target",
        "신청기관": "applicant_name", "면적": "area", "용도구분": "use_type", "인증일자": "cert_date",
        "인증만료일": "cert_expiry", "인증기관": "cert_body"}},
    "15054156": {"table": "bronze.pub_green_tech_cert", "min_rows": 1500, "drop": ["사업자등록번호"], "columns": {
        "순번": "seq", "인증번호": "cert_no", "기술명칭": "tech_name", "분류코드": "class_code",
        "분류코드명": "class_name", "신청기관명": "applicant_name", "발급부처": "issuing_ministry",
        "인증확정일": "cert_date", "인증만료일": "cert_expiry", "데이터 기준일자": "data_base_date"}},
}

spark.sql("CREATE SCHEMA IF NOT EXISTS bronze")
batch_id = str(uuid.uuid4())
print("batch_id:", batch_id)

# %% [markdown]
# ## 2. 공공데이터포털 다운로드 함수
#
# 포털 화면에서 **다운로드** 버튼을 눌렀을 때와 같은 순서로 요청합니다. 로그인이나 인증키가 필요 없습니다.
# 포털이 CSV 대신 HTML(오류·제한 화면)을 돌려주면 저장하지 않고 멈춥니다.
#
# **예상 결과:** 결과 없이 끝납니다.

# %%
def download_public_file(pk: str):
    s = requests.Session()
    s.headers.update(UA)
    page = s.get(f"{BASE}/data/{pk}/fileData.do", timeout=60)
    page.raise_for_status()
    m = re.search(r"fn_fileDataDown\('(\d+)',\s*'([^']+)',\s*'([^']*)',\s*'(\d+)',\s*'(\d+)'\)", page.text)
    if not m:
        raise RuntimeError(f"[{pk}] 다운로드 정보를 찾지 못했습니다. 포털 화면 구조가 바뀌었는지 확인하세요.")
    detail_pk, file_sn = m.group(2), m.group(4)
    hdr = {"X-Requested-With": "XMLHttpRequest", "Referer": f"{BASE}/data/{pk}/fileData.do"}
    r = s.post(f"{BASE}/tcs/dss/selectFileDataDownload.do",
               data={"publicDataDetailPk": detail_pk, "publicDataPk": pk, "atchFileId": "",
                     "fileDetailSn": file_sn, "publicDataTyCode": "PR0051"},
               headers=hdr, timeout=60)
    r.raise_for_status()
    info = json.loads(r.text)
    if not info.get("status"):
        raise RuntimeError(f"[{pk}] 다운로드 요청이 거절되었습니다: {info}")
    atch, sn = info["atchFileId"], info["fileDetailSn"]
    name = info["dataSetFileDetailInfo"]["dataNm"]
    limit = s.post(f"{BASE}/cmm/cmm/check-limit.json", data={"atchFileId": atch, "fileDetailSn": sn},
                   headers=hdr, timeout=60).json()
    if limit.get("needCaptcha"):
        raise RuntimeError(f"[{pk}] 다운로드 횟수 제한에 걸렸습니다. 1–2분 뒤 이 셀부터 다시 실행하세요.")
    f = s.get(f"{BASE}/cmm/cmm/fileDownload.do",
              params={"atchFileId": atch, "fileDetailSn": sn, "dataNm": name},
              headers={"Referer": f"{BASE}/data/{pk}/fileData.do"}, timeout=180)
    f.raise_for_status()
    if f.content[:1] in (b"<", b"\x89"):
        raise RuntimeError(f"[{pk}] CSV가 아닌 응답(HTML 또는 이미지)을 받았습니다.")
    return f.content, {"dataset_id": pk, "data_name": name, "file_id": atch}


def to_pandas(raw: bytes) -> pd.DataFrame:
    for enc in ("utf-8-sig", "cp949"):
        try:
            text = raw.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    else:
        raise ValueError("파일 인코딩을 판별하지 못했습니다.")
    return pd.read_csv(io.StringIO(text), dtype=str, keep_default_na=False)

# %% [markdown]
# ## 3. 내려받아 Bronze 테이블로 저장
#
# 데이터마다 내려받기 → 열 이름 변경 → 출처 열 추가 → Delta 테이블 저장을 반복합니다. 다시 실행하면 테이블을 덮어씁니다.
#
# **예상 결과:** 4줄이 모두 `OK`로 시작합니다. 행 수는 포털의 최신 파일에 따라 달라지며, 실습 기준 파일(ZEB `2025-12-31` 기준)에서
# `pub_zeb_cert`는 **9,760행**입니다. 오른쪽 `←` 뒤에 내려받은 파일 이름(기준일 포함)이 보입니다.

# %%
ingested_at = datetime.now(timezone.utc)
log_rows = []
for pk in [x.strip() for x in dataset_ids.split(",") if x.strip()]:
    cfg = DATASETS[pk]
    t0 = time.time()
    if local_folder:
        with open(f"/lakehouse/default/{local_folder.strip('/')}/{pk}.csv", "rb") as fh:
            raw, meta = fh.read(), {"dataset_id": pk, "data_name": f"{local_folder}/{pk}.csv (관리자 제공)", "file_id": "local"}
    else:
        raw, meta = download_public_file(pk)
    pdf = to_pandas(raw).drop(columns=[c for c in cfg["drop"]], errors="ignore")
    extra = [c for c in pdf.columns if c not in cfg["columns"]]
    rename = dict(cfg["columns"])
    for i, c in enumerate(extra, 1):
        rename[c] = f"extra_{i}"
        print(f"  [주의] {pk}: 새 열 '{c}' → extra_{i}")
    pdf = pdf.rename(columns=rename)
    pdf.insert(0, "source_row_num", range(1, len(pdf) + 1))
    sdf = (spark.createDataFrame(pdf)
           .withColumn("_source_dataset_id", F.lit(pk))
           .withColumn("_source_name", F.lit(meta["data_name"]))
           .withColumn("_source_file_id", F.lit(meta["file_id"]))
           .withColumn("_batch_id", F.lit(batch_id))
           .withColumn("_ingested_at", F.lit(ingested_at)))
    sdf.write.mode("overwrite").option("overwriteSchema", "true").saveAsTable(cfg["table"])
    n = spark.table(cfg["table"]).count()
    status = "OK" if n >= cfg["min_rows"] else "CHECK"
    log_rows.append((batch_id, pk, meta["data_name"], cfg["table"], n, status, round(time.time() - t0, 1), ingested_at))
    print(f"{status}  {cfg['table']:<28} {n:>7,}행  ← {meta['data_name']}")
    if not local_folder:
        time.sleep(2)

# %% [markdown]
# ## 4. 수집 기록 남기기
#
# 이번 적재 결과를 `bronze.ingest_log`에 한 줄씩 추가합니다. 언제 어떤 파일을 몇 행 받았는지 나중에 확인할 수 있습니다.
#
# **예상 결과:** 4행 표. `status`가 모두 `OK`입니다. `CHECK`가 있으면 최소 행 수보다 적게 받은 것이므로 셀이 오류로 멈춥니다.

# %%
log_df = spark.createDataFrame(
    log_rows,
    "batch_id string, dataset_id string, source_name string, table_name string, row_count long, status string, seconds double, ingested_at timestamp")
log_df.write.mode("append").saveAsTable("bronze.ingest_log")
display(log_df)
bad = [r for r in log_rows if r[5] != "OK"]
assert not bad, f"행 수가 예상보다 적은 데이터가 있습니다: {bad}"

# %% [markdown]
# ## 5. 원본 그대로인지 확인
#
# Bronze는 값을 바꾸지 않습니다. 같은 시도도 **기관마다 표기가 다르고**, 날짜 앞에 공백이 있는 값도 그대로 남습니다.
#
# **예상 결과:** 세 표가 나옵니다.
#
# 1. ZEB 인증 3행. `cert_date`가 `" 2025-12-31"`처럼 **앞에 공백이 있는 문자열**입니다. `energy_self_sufficiency`도 문자열입니다.
# 2. ZEB의 `region`은 `경기` 1,897건, `경남` 870건처럼 **짧은 표기**입니다.
# 3. BF의 `sido`는 `경기도` 3,827건, `전라남도` 2,070건처럼 **정식 표기**입니다.
#
# 표기 통일과 형식 변환은 04장(Silver)에서 합니다.

# %%
display(spark.table("bronze.pub_zeb_cert")
        .select("source_row_num", "cert_stage", "building_main_use", "energy_self_sufficiency", "region", "building_name", "zeb_grade", "cert_date")
        .orderBy("source_row_num").limit(3))
display(spark.table("bronze.pub_zeb_cert").groupBy("region").count().orderBy(F.desc("count")).limit(5))
display(spark.table("bronze.pub_bf_cert").groupBy("sido").count().orderBy(F.desc("count")).limit(5))

# %% [markdown]
# 다음 단계: `02_bronze_contoso_generate`에서 Contoso 건설의 내부 시스템 데이터를 만듭니다.
