# 메달리온 아키텍처: 원천 보존에서 판단 근거까지

이 워크숍의 중심은 제품을 연결하는 것이 아니라 **같은 데이터를 Bronze → Silver → Gold로 발전시키면서 각 단계의 책임과 완료 조건을 구분하는 것**입니다. [전체 구성도](../assets/architecture.svg)의 상단 메달리온 세 계층과 아래 Gold 소비 경로를 함께 읽으십시오.

## 공식 권고와 실습 배치

Microsoft Learn은 Bronze를 **Raw**, Silver를 **Enriched**, Gold를 **Curated**로 설명하며 단계적 품질 개선과 원본 보존을 권고합니다. **Gold는 집계만을 뜻하지 않습니다.** 보고서·질의에 맞게 정리한 업무 entity와 계산 결과도 Gold입니다. [공식 문서와 확인 근거](../docs/sources.md#메달리온-설계-검증-2026-10-13)를 참고합니다.

공식 운영 권고는 계층별 Lakehouse를 만들고 각각 별도 workspace로 분리하여 거버넌스를 제어하는 방식입니다. 여기서는 참가자별 작업 대상을 명확하게 하고 12명 실습의 바인딩·설정을 단순화하기 위해 **참가자당 하나의 workspace + 하나의 schema-enabled Lakehouse**를 사용합니다. `bronze`·`silver`·`gold`는 **논리적 계층 분리**이고, schema 이름만으로 접근권한·보존정책·보안 경계가 생기지 않습니다. 운영 도입 시 계층별 소유권·권한·보존·재처리 책임을 별도로 설계해야 합니다.

```text
참가자 workspace
└─ schema-enabled Lakehouse — OneLake 저장 기반
   ├─ Files/workshop/             원본 fixture·공공 CSV·manifest 보존
   ├─ Tables / bronze.*           Raw 값·출처 (Delta)
   ├─ Tables / silver.*           Enriched 타입·키 검증 (Delta)
   ├─ Tables / gold.*             Curated 업무 entity·계산 결과 (Delta)
   └─ Tables / audit.decision_log 승인 검토 증적; 메달리온의 네 번째 계층 아님
```

OneLake는 세 계층과 Files를 담는 **통합 저장소**입니다. Gold 뒤에 복사하는 네 번째 ETL 단계가 아닙니다. Files 원본 보존과 Bronze Delta 생성도 동일한 산출물이 아닙니다.

## 계층별 데이터 계약

| 계약 | Bronze · Raw | Silver · Enriched | Gold · Curated |
|---|---|---|---|
| 질문 | 무엇을 받았는가? | 어떤 프로젝트·현장·설계인가? | 어떤 위험·보완안·발주 상태인가? |
| 입력 | 보존된 fixture JSON·공공 CSV/manifest | Bronze Delta string | typed Silver + 교육 기준 |
| 실제 writer | `01_bronze`, 공공은 `06_public_zeb` | `02_silver`, 공공은 `06_public_zeb` | `03_gold` |
| 실제 처리 | fixture 값 string 표현; 공공 컬럼명 명시 mapping; source hash 추가 | trim·명시 schema cast·date parse; typed fixture의 key/MDM/현행/제출 관계 검증 | 업무 entity 매핑, project 지역 alias 정규화; 현황·등급·위험·63개 보완안·PO 상태 계산 |
| 정상 산출물 | 가상 16 + 공공 1 table | 가상 16 + 공공 1 table | 업무 entity 12 + 결과 3 table |
| 완료 확인 | 원본 byte hash·manifest 행 수·문자열·출처 metadata | 원천별 행 수 유지·타입·유일 키/고아/현행 설계·metadata | 현장 8행·조합 63행·PO 25행/초과 0; Silver 기준 독립 검산 |
| 실패 처리 | hash/CSV/manifest mismatch 시 중단 | invalid cast/date/key 관계 시 중단; 자동 quarantine·deduplication 없음 | 모호한 지역 alias·미매핑·입력 검증 실패 시 중단 |

`01_bronze`는 fixture bytes hash와 원천 `validate()`도 먼저 검사합니다. 품질 검사가 Bronze에는 전혀 없다는 의미가 아니라, **Raw 값 자체를 업무 값으로 고치지 않는다**는 계약입니다. Silver의 trim은 정상 nullable 값을 삭제하지 않으며 Gold 지역 정규화와도 다릅니다.

내부 출처 컬럼은 `_source_kind=SYNTHETIC`, `_source_sha256`입니다. 공공은 `source_row_num`, `_source_dataset_id=15085042`, `_source_file_sha256`입니다. 현재 수집 timestamp·batch ID는 구현하지 않았습니다. 공공 Silver는 date parse와 region trim을 하며 **가상 fixture와 동일한 업무 키 검증을 수행한다고 주장하지 않습니다**.

## 실제 table 매핑

아래 입력 이름은 Bronze와 Silver에서 동일하며, 각 계층의 table은 별도로 물리화됩니다. 합계는 `tools/build_notebooks.py`의 반복·mapping과 `data/synthetic/fixtures.json`의 16개 source를 기준으로 합니다.

| Bronze → Silver의 source 이름 | source 행 | Gold 업무 entity |
|---|---:|---|
| `erp_project` | 8 | `gold.project` — 표준 `sido` 추가 |
| `pms_site` | 8 | `gold.site` |
| `mdm_site_xref` | 8 | `gold.mdm_site_xref` |
| `bim_design_version` | 18 | `gold.design_version` |
| `pms_cert_target` | 12 | `gold.cert_target` |
| `pms_certificate` | 10 | `gold.site_certificate` |
| `pms_cert_milestone` | 48 | `gold.cert_milestone` |
| `pms_equipment_plan` | 39 | `gold.equipment` |
| `scm_vendor` | 9 | `gold.vendor` |
| `scm_purchase_order` | 25 | `gold.purchase_order` |
| `sim_improvement_option` | 12 | `gold.improvement_option` |
| `ref_zeb_grade_criteria` | 6 | `gold.grade_criteria` |
| `scm_po_event` | 1 | Silver의 발주 event를 `gold.po_status` 계산에 사용; 별도 Gold 복사 없음 |
| `pms_action_log` | 0 | 원천 빈 과거 로그; 승인 audit와 별개, Gold 복사 없음 |
| `ref_region` | 17 | `gold.project.sido` 매핑에 사용; 별도 Gold 복사 없음 |
| `ref_equipment_category` | 8 | Silver reference 보존; 별도 Gold 복사 없음 |
| `pub_zeb_cert` — 별도 실제 공공 경로 | p01 각 9,760 | 공공 Gold 생성 없음; 가상 site 이름 join 금지 |

추가 Gold 결과는 `site_status` **8행**, `option_eval` **63행**, `po_status` **25행**입니다. `option_eval`의 에너지 값은 `decimal(12,4)`로 저장합니다. 공공 포함 Bronze/Silver는 **17/17**, Gold는 **15**이며 원본 workspace의 21/21/22 범위를 복사한 것이 아닙니다.

## HS-D 한 건을 계층 끝까지 따라가기

1. **Bronze**: `erp_project.project_no=CT-24-0189`의 `sido_raw="경기 "`와 BIM 값들을 string으로 보존합니다. V2/V3 원천 record를 덮어쓰지 않습니다.
2. **Silver**: 공백을 trim하고 SS/PE/PV를 double, 설계일을 date 등으로 cast합니다. MDM `CT-24-0189 ↔ HS-D ↔ BIM-0397`과 인증서의 `BIM-0397-V2` 참조를 검증합니다. 현행 V3가 하나인지 확인하되 V1/V2를 삭제하지 않습니다.
3. **Gold entity**: `project.sido`를 지역 reference에 따라 `경기`로 매핑하고 `design_version`·`site_certificate`는 현행과 제출안을 모두 설명할 수 있게 남깁니다.
4. **Gold 계산**: 제출 V2 `43.5%, 69, PV530kW`와 현행 V3 `38.2%, 76, PV380kW`를 구분합니다. 현행 교육 등급은 5, 예비 인증 4보다 나빠 `danger`입니다. 주거 4등급은 **SS ≥ 40 또는 PE < 70**입니다.
5. **Gold 소비**: Ontology는 현장·설계·대안을 관계로 탐색하고 Direct Lake 모델은 같은 Gold를 보고합니다. `04_snapshot`은 Gold 위험 4개를 파일에 만들며 Eventhouse 수집은 명시적 별도 단계입니다. 실시간 Gold table 동기화가 아닙니다.

`OPT-D5+OPT-D6`은 가산 에너지 기준의 최저 비용 조합일 뿐입니다. 비용 110,000,000원·최대 병렬 lead 30일, `40.1%, 72.2`라도 실제 공학·배타성·시공성은 미검증이므로 `decision_feasible=false`를 유지합니다.

## 읽기 검산과 승인 기록의 경계

- **Spark Notebook**은 세 계층의 Delta table writer입니다. **SQL analytics endpoint**는 같은 Delta를 T-SQL로 읽습니다. SQL view/function/procedure를 만들 수 있다는 사실과 물리 Delta INSERT/UPDATE/DELETE 가능 여부를 혼동하지 않습니다.
- [독립 SQL 검산](../sql/reference_checks.sql)은 Silver 설계와 교육 threshold를 사용합니다. Gold의 저장된 grade를 다시 읽는 것만으로 검산을 완료하지 않습니다. 오프라인 [Decimal 정답](../data/reference-answers.md)과도 대조합니다.
- **Direct Lake**는 OneLake Gold Delta를 읽는 semantic model 저장 모드입니다. 이 실습의 모델은 Gold 4개 table을 소비하며 모든 Gold table을 무조건 노출하지 않습니다.
- **audit**는 승인 검토의 증적입니다. `05_decision_log`는 Teams Proceed/Confirm 후 승인된 Operations action으로만 실행하며 notebook 문자열만으로 인간 identity를 증명하지 않습니다. audit는 원천 `pms_action_log`와 다르고 Bronze/Silver/Gold·설계·발주를 수정하지 않습니다.
- 그림의 소비·승인 흐름은 목표 경로입니다. 실제 실행/미완료는 [리허설 상태](validation.md)에 있습니다. 이번 설계 반영으로 Teams 제안이나 승인 action이 새로 실행된 것은 아닙니다.

## 교육 안전 동작과 운영 확장

현재 기본 writer는 `errorifexists`이며 append 배치·overwrite·자동 reset을 하지 않습니다. 실패한 Silver 검증 전에 일부 Delta table이 생성될 수 있으므로 **전체 stage를 원자적으로 rollback하는 pipeline이라고 주장하지 않습니다**. 실패 시 관리자에게 원인·table 상태를 확인받고 Gold로 진행하지 않습니다.

운영 전환에는 계층별 권한/소유권, 수집 batch/timestamp, 명시적 quarantine 및 품질 metric, 안전한 재처리·증분 수집, 스케줄링·장애 복구·보존 정책이 필요합니다. 여기서는 설계 고려사항이며 구현 완료 항목이 아닙니다. MLV나 table 최적화 설정을 기존 notebook에 임의 적용하지 않았습니다. 추가 runtime 검증 없는 Z-ORDER/V-Order/OPTIMIZE 성능 보장도 하지 않습니다.
