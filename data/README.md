# 데이터 출처·사전·계산 경계

## 세 종류를 분리

1. **기본 내부 fixture**: 기존 Notebook02의 literal record와 결정적 생성 로직을 읽기 전용으로 추출한 SYNTHETIC 데이터입니다. 가상 ERP/PMS/MDM/BIM/SCM 구조를 표현하지만 실제 고객 시스템/export가 아닙니다.
2. **공공 데이터**: 실제 ZEB `15085042` snapshot `20251231`은 별도 보존·검토되어 p01 Bronze/Silver 각각 9,760행을 확인했습니다. raw CSV는 **공개 GitHub kit에 포함하지 않으며** 관리자가 각 참가자에게 승인된 bytes/manifest를 공급합니다. 다른 3종은 원본 workspace의 읽기 관찰 count/date reference일 뿐 이 실습에서 취득·처리했다고 주장하지 않습니다.
3. **파생 정답**: fixture를 표준 Python Decimal/itertools로 독립 계산한 reference_answers.json입니다. Gold 원천으로 거꾸로 제공하는 것이 아니라 오프라인 검산용입니다.

기준일 `2026-09-30`. 공공 source snapshot label, 실제 record cert date, 내부 progress date, BIM version date는 서로 다른 의미입니다.

## 기본 source 사전

CSV는 UTF-8, 빈 칸은 nullable 원천값입니다. schema와 원천 literal 값은 fixtures.json, 파일 hash/행 수는 synthetic/manifest.json에 있습니다.

| source table | 행 | 핵심 키/관계 | 주요 타입 |
|---|---:|---|---|
| erp_project | 8 | project_no | string, households int nullable, dates date |
| pms_site | 8 | site_code | progress_pct double, progress_as_of date |
| mdm_site_xref | 8 | site_code / project_no / bim_model_id | string, valid_from date |
| bim_design_version | 18 | version_id / bim_model_id | SS/PE/PV double, version_date date, status string |
| pms_cert_target | 12 | target_id / site_code | type/grade string |
| pms_certificate | 10 | cert_no / design_version_id | cert_date date, submitted version FK |
| pms_cert_milestone | 48 | milestone_id / site_code | seq int, planned/actual date |
| pms_equipment_plan | 39 | wbs_code / site_code / design_version_id | capacity nullable double, planned cost long |
| scm_vendor | 9 | vendor_code | lead int, on_time_rate double, alternative boolean |
| scm_purchase_order | 25 | po_no / wbs_element / vendor_code | dates, amount long |
| scm_po_event | 1 | event_id / po_no | new_expected_date date; event_time string |
| sim_improvement_option | 12 | option_id / site_code | gain/delta double, cost long, lead int |
| pms_action_log | 0 | source action_id | empty historical source, **not audit** |
| ref_zeb_grade_criteria | 6 | grade_code | SS minimum / residential+nonresidential PE limit |
| ref_region | 17 | sido | synthetic reference aliases/geography |
| ref_equipment_category | 8 | category_code | synthetic category context |

계산/학습용 이름·PM·업체는 가상 fixture입니다. fixture package는 원본 generator record를 보존하고 원본 notebook definition/인증정보를 출판하지 않습니다. 임의 source defect나 새로운 supplier shock를 추가하지 않았습니다.

## 참가자 Medallion

- Bronze 16개: 문자열 그대로, `_source_kind`, `_source_sha256`; Files fixture bytes를 보존합니다.
- Silver 16개: 명시 schema cast/trim, null/key/MDM/current/certificate model 검증.
- Gold 15개: project/site/mdm/design/target/certificate/milestone/equipment/vendor/PO/option/criteria 12개 + site_status 8행 + option_eval 63행 + po_status 25행.
- audit.decision_log: 기본적으로 없음; Teams Proceed/Confirm 후 creator-delegated Operations action에서 생성, original pms_action_log와 분리. 네 번째 메달리온 계층이 아닙니다.
- **필수 public ZEB segment** 실행 시 Bronze/Silver 각각 1개가 추가되어 총17/17개입니다. 내부16개만으로 계산 검산은 재현되지만 공공 원천 실습 완료는 아닙니다.

원본의 **21 Bronze / 21 Silver / 22 Gold / 3 Ops**와 kit의 범위는 다릅니다. 원본 full model/evaluation/benchmark를 실습에 무조건 복사하지 않습니다.

세 schema의 Delta와 원본 Files는 모두 **OneLake 안**에 있습니다. 원본 Files → Bronze Delta → Silver → Gold는 표현·품질이 높아지는 흐름이지, Gold 이후 OneLake로 이동하는 흐름이 아닙니다. [설계 계약·전체 source→Gold 매핑](../admin/medallion-architecture.md)을 함께 읽습니다.

## 키와 품질

원본 읽기 점검에서는 중복/고아/현행 수 실패가 없었습니다. kit는 실제 의미 있는 키·타입 검사를 수행하고 인위적 오류를 정상 원천처럼 꾸미지 않습니다. 테스트가 주입하는 duplicate/orphan는 분리된 테스트 입력이며 실제 fixture defect라고 표현하지 않습니다.

지역은 원천 alias가 있습니다. Silver는 공백 trim으로 원천 의미를 보존하고 Gold.project는 ref_region alias로 `sido`를 정규화합니다. alias 중복/미매핑은 중단합니다. public certified building identity resolution을 자동 수행하지 않으며 공개 건물과 가상 site를 이름으로 동일 건물이라 join하지 않습니다.

## 계산·판단 제한

[정답 해설](reference-answers.md)에서 OR/strict-PE/rank 및 옵션 가산식을 확인합니다. 법적 threshold 현행 적용, BEMS 또는 remote metering 충족 여부, 물리적 효과·배타성·병렬 schedule은 미검증입니다. `decision_feasible=false`가 의도된 안전 결과입니다.

## 재현

```powershell
python .\tools\build_data.py
python .\tools\reference.py
```

fixture source literal을 수정하지 않으면 CSV/hash/정답이 결정적으로 재현됩니다. 생성 결과의 날짜를 오늘로 바꾸지 않습니다. public snapshot은 [별도 관리자 가이드](public/README.md)를 따릅니다.
