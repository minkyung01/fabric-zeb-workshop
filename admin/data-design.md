# 데이터 설계

[목차](../README.md) \| [관리자 준비 가이드](README.md)

실습 데이터의 계층·테이블·판정 규칙·정답을 정리한 문서입니다. 모든 테이블은 참가자 작업 영역의 schema-enabled Lakehouse `lh_zeb` 하나에 있습니다. `bronze`·`silver`·`gold`·`ops`는 스키마로 나눈 **논리적 계층**이며, 스키마 이름만으로 권한·보존 경계가 생기지는 않습니다. 운영에서는 계층별 Lakehouse·작업 영역과 권한을 따로 설계합니다.

## 계층과 책임

| 계층 | Writer | 원칙 | 테이블 수 |
|---|---|---|---|
| `bronze` | `01_bronze_public_ingest`, `02_bronze_contoso_generate`, `nb_apply_decision`(조치 기록 추가) | 원천 그대로. 공공은 문자열·영문 열 이름, 출처 열(`source_row_num`, `_source_dataset_id`, `_batch_id`, `_ingested_at`) | 21 |
| `silver` | `03_silver_conform` | 정제·표기 통일·같은 건물 연결·이벤트와 승인된 조치 반영. 업무 판단 없음. 실행마다 전체 재생성 | 21 |
| `gold` | `04_gold_model` | Silver에서 정리한 **업무 데이터**. 원천 시스템 코드 유지. 판단 결과 없음 | 22 |
| `ops` | `04_gold_model`, `06_risk_event`, `nb_apply_decision` | 판정 규칙을 적용한 운영 지표·위험 이벤트(보고서·Operations agent 전용) | 5 |

판단 기준을 Gold에 넣지 않고 Ontology 업무 규칙(06장)으로 정의하는 것이 이 설계의 핵심입니다. `ops`는 같은 규칙으로 계산한 결과를 보고서와 감시에 쓰기 위한 별도 계층입니다.

## 원천

| 구분 | Bronze 테이블 | 행(실습 기준) | 비고 |
|---|---|---|---|
| 공공 ZEB 인증(15085042) | `pub_zeb_cert` | 9,760 | 한국에너지공단, 20251231 |
| 공공 녹색건축 인증(15003214) | `pub_gseed_cert` | 5,104 | 한국부동산원, 20251231 |
| 공공 BF 인증(15014781) | `pub_bf_cert` | 22,184 | 한국장애인고용공단, 20260630 |
| 공공 녹색기술 인증(15054156) | `pub_green_tech_cert` | 1,905 | 한국산업기술진흥원, 20260626. 사업자등록번호 미수집 |
| 수집 기록 | `ingest_log` | 적재마다 4행 추가 | |
| ERP | `erp_project` | 8 | 시도 원천 표기(`경기 `, `서울시` 등) |
| PMS | `pms_site` 8, `pms_equipment_plan` 39, `pms_cert_target` 12, `pms_certificate` 10, `pms_cert_milestone` 48, `pms_action_log` 0 | | 조치 기록은 빈 상태로 시작 |
| MDM | `mdm_site_xref` | 8 | ERP 프로젝트 ↔ PMS 현장 ↔ BIM 모델 |
| BIM | `bim_design_version` | 18 | 현장별 마지막 설계안이 `현행` |
| SCM | `scm_vendor` 9, `scm_purchase_order` 25, `scm_po_event` 1 | | IC-B 창호 납기 +5일 이벤트 |
| 컨설팅 | `sim_improvement_option` | 12 | D단지 6, H단지 5, C센터 1 |
| 기준 | `ref_zeb_grade_criteria` 6, `ref_region` 17, `ref_equipment_category` 8 | | |

## 현장

| 현장 | ERP | BIM | 용도 | 시도 | 단계·공정률 | 현행 설계 | 자립률 | 1차에너지 | 예비 | 목표 | 05장 상태 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| HS-A 에코시티 A단지 | CT-24-0231 | BIM-0412 | 공동주택 | 경기 | 시공 58 | V2 | 44.0 | 66 | 4 | 4 | 정상 |
| IC-B 리버뷰 B단지 | CT-25-0107 | BIM-0518 | 공동주택 | 인천 | 시공 41 | V2 | 39.0 | 65 | 4 | 4 | 정상(1차에너지로 4등급) |
| SN-C 스마트오피스 C센터 | CT-26-0044 | BIM-0633 | 업무시설 | 경기 | 설계 0 | V2 | 63.0 | 82 | – | 3 | 주의(BEMS 미계획) |
| **HS-D 에코시티 D단지** | CT-24-0189 | BIM-0397 | 공동주택 | 경기 | 시공 72 | **V3 VE 반영안** | **38.2** | **76** | **4** | 4 | **위험(예상 5등급)** |
| SJ-E 세종 E학교 | CT-26-0052 | BIM-0641 | 교육연구시설 | 세종 | 설계 0 | V2 | 64.2 | 52 | 3 | 3 | 주의(BF 목표 미달) |
| BS-F 해운대 F청사 | CT-25-0078 | BIM-0455 | 업무시설 | 부산 | 시공 63 | V2 | 82.5 | 8 | 2 | 2 | 정상 |
| JJ-G 전주 G도서관 | CT-25-0133 | BIM-0529 | 문화 및 집회시설 | 전북 | 시공 35 | V2 | 61.0 | 55 | 3 | 3 | 정상 |
| MP-H 마포 H단지 | CT-26-0091 | BIM-0620 | 공동주택 | 서울 | 설계 0 | V3 | 36.0 | 82 | – | 4 | 주의(목표 미달) |

## 판정 규칙

Ontology(06장 4단계)와 `04_gold_model`·`05_answers`·`06_risk_event`가 같은 규칙을 씁니다.

| 규칙 | 정의 |
|---|---|
| ZEB 예상 등급 | 자립률 등급 = `selfsuff_pct >= selfsuff_min_pct`인 가장 좋은 등급, 1차에너지 등급 = `primary_energy_kwh_m2y < 기준값`(주거용/주거용 이외)인 가장 좋은 등급, 최종 = 둘 중 더 좋은 등급. 어느 쪽도 못 맞추면 `인증 기준 미달` |
| 등급 순서 | `+` → 1 → 2 → 3 → 4 → 5. '4등급 이상' = +, 1–4 |
| 주거 구분 | 공동주택·단독주택 = 주거용, 그 밖 = 주거용 이외 |
| 예비인증 → 본인증 | 예상 등급 < 예비인증 등급이면 본인증 위험(`grade_risk = 예비 등급 미달`) |
| BEMS | 설비 계획에 `BEMS`가 없으면 필수 요건 미충족(`requirement_risk`) |
| 인증 일정 | 설비 설치 완료 = 사용승인 121일 전, 본인증 신청 75일 전, 취득 30일 전. 미입고 발주의 예상 입고일이 설치 완료 계획일을 넘으면 3–6단계가 넘긴 일수만큼 밀림 |
| 대체 공급 | `is_alternative_pool = true` 공급사로 바꾸면 예상 입고일 = 기준일 2026-09-30 + 표준 납기 |
| 보완안 추천 | 보완안 하나를 현행 설계안에 더해(자립률 +`selfsuff_gain_pp`, 1차에너지 +`primary_energy_delta`) 필요 등급(예비, 없으면 목표)을 회복하고, 기준일 + `lead_time_days`가 설치 완료 계획일 이전인 안 중 비용 최저 |
| 위험 수준 | 위험 = 예비 등급 미달 또는 설치 지연, 주의 = 목표 미달·BEMS 미계획·추가 인증 목표 미달, 그 외 정상 |

등급 기준값은 제로에너지건축물 인증시스템(zeb.energy.or.kr)의 인증 등급 기준입니다. 판정은 교육용 단순화이며 실제 인증 심사를 대신하지 않습니다.

## Gold와 ops

| 스키마 | 테이블 |
|---|---|
| `gold` 기준 4 | `ref_region`, `ref_building_use`(14), `ref_zeb_grade_criteria`(+`grade_color`), `ref_equipment_category` |
| `gold` 공공 5 | `pub_zeb_certification`, `pub_gseed_certification`, `pub_bf_certification`, `pub_green_tech_certificate`, `pub_certified_building`(25,362) |
| `gold` 내부 13 | `erp_project`, `pms_site`, `mdm_site_xref`, `bim_design_version`, `pms_certificate`, `pms_cert_target`, `pms_cert_milestone`, `pms_equipment_plan`, `scm_vendor`, `scm_purchase_order`, `scm_po_event`, `sim_improvement_option`, `pms_action_log` |
| `ops` | `site_status`(8), `po_status`(25), `milestone_forecast`(48) — `04_gold_model`<br>`option_eval`(11), `risk_event`(위험 현장당 1) — `06_risk_event` |

## Operations 데이터 계약

| 대상 | 내용 |
|---|---|
| `ops.option_eval` | 현장·보완안별 적용 후 자립률·1차에너지·예상 등급, 필요 등급, 준비 완료일, 설치 완료 계획일, `feasible`, `cost_rank` |
| `ops.risk_event` | `event_id = ZEB-<현장>-<기준일>`, 현장·사유·예비/예상 등급, 추천 보완안(`cost_rank = 1`)·비용·적용 후 자립률·등급, `status`(`open` → `approved` → `resolved`) |
| Eventhouse `eh_zeb.ZebRiskEvent` | 상태 이력(append only). 열: `event_id, status_time, event_status, site_code, site_name, risk_reason, prelim_grade, forecast_grade, selfsuff_pct, recommended_option_id, recommended_option_name, option_cost_krw, expected_selfsuff_pct, expected_grade` |
| Operations agent 규칙 | `event_status`가 `open`으로 **바뀔 때** Teams 알림 + `ApplyZebOption(event_id, option_id)` 추천 |
| `nb_apply_decision` | 매개 변수 `event_id`, `option_id`. 추천안과 다르거나 `feasible`이 아니면 거부. `bronze.pms_action_log`에 `ACT-<event_id>` 1행(`apply_options`, `{"option_ids": [...], "event_id": ...}`, 이벤트당 한 번), Eventhouse `approved` → `03_silver_conform`·`04_gold_model` 실행(`wait_for_graph = False`) → 위험 해소 시 `resolved` |
| 반영 결과 | Silver가 조치를 읽어 `BIM-0397-V4 조치 반영안`(41.4 / 72.5)을 만들고 `현행`으로, 설비 `HS-D-OPT-D2` 추가 → D단지 4등급·정상 |

Eventhouse와 Delta는 하나의 트랜잭션이 아닙니다. Notebook이 중간에 실패하면 실패한 셀과 각 저장소의 상태를 확인한 뒤 재시도합니다. 조치 기록은 이벤트당 한 번만 추가됩니다.

## 정답

### 07장 Data agent 질문

| 번호 | 정답 |
|---|---|
| Q1 | 경기 1,897 → 경남 870 → 경북 828 |
| Q2 | 받을 수 있다. 자립률 기준 5등급, 1차에너지 65 < 70 → 4등급 → 최종 4등급, BEMS 계획 있음 |
| Q3 | 에코시티 D단지(HS-D) 한 곳. 예비 4등급, 현행 V3 예상 5등급 |
| Q4 | 30건(준공 후 인증 = 본인증) |
| Q5 | D단지만 +3일(12/03 > 11/30). A단지 여유 52일 |
| Q6 | 9건, 평균 52.2% — D단지 38.2%보다 14.0%p 높음 |
| Q7 | 지킬 수 있음. Alpine 지열 55일 → 11/24, 여유 6일 |
| Q8 | OPT-D2 주차장 캐노피 태양광, 230,000,000원 → 41.4% 4등급 |

### 보완안 평가 (D단지, 현행 V3 38.2 / 76, 설치 완료 계획일 2026-11-30)

| 보완안 | 비용(원) | 적용 후 | 예상 | 준비 완료 | feasible |
|---|---|---|---|---|---|
| OPT-D6 | 50,000,000 | 39.1 / 74.2 | 5등급 | 10-20 | – |
| OPT-D5 | 60,000,000 | 39.2 / 74.0 | 5등급 | 10-30 | – |
| **OPT-D2** | **230,000,000** | **41.4 / 72.5** | **4등급** | 11-14 | **1순위** |
| OPT-D3 | 280,000,000 | 39.6 / 74.5 | 5등급 | 12-14 | – |
| OPT-D4 | 340,000,000 | 40.3 / 72.0 | 4등급 | 11-19 | 2순위 |
| OPT-D1 | 420,000,000 | 43.5 / 70.0 | 4등급 | 11-29 | 3순위 |

### 보고서

1페이지 카드 `9,760`·`2,732`·`+23.0%`·`45.1%`, 등급 분포 +24·1등급 368·2등급 332·3등급 980·4등급 2,697·5등급 5,359, 주거용 285·주거용 이외 9,475, 자립률 하한 미만 인증 176. 2페이지 카드 승인 전 `8`·`1`·`3`·`0`·`34`, 승인 후 위험 `0`.

## 참고 Ontology

`fabric/ont_zeb_reference`는 원본 데모에서 사용한 참고 설계(엔터티 22개·관계 27개, 업무 규칙을 엔터티 설명에 포함)의 Fabric 항목 정의입니다. 바인딩의 작업 영역·Lakehouse ID는 `{{WORKSPACE_ID}}`, `{{LAKEHOUSE_ID}}`이며 `admin/provision.py --reference-ontology`가 참가자 값으로 바꿔 배포합니다.
