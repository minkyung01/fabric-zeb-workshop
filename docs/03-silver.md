# 03. Silver에서 타입과 현장 정체성 연결하기

## 업무 목적
ERP 프로젝트, PMS 현장, BIM 모델과 SCM 발주를 명확한 키로 연결해 인증 제출 설계를 잘못 해석하지 않도록 합니다.

**메달리온의 Enriched 계층**입니다. Bronze string을 업무에 맞는 타입으로 바꾸되 아직 인증 등급·대안을 계산하지 않습니다. `bim_design_version` 18행을 유지하여 “제출 V2”와 “현행 V3”를 비교할 수 있게 합니다. `경기 `의 공백은 trim하지만 지역 alias를 표준 `sido`로 매핑하는 작업은 현재 **Gold.project**에 있습니다.

## 시작 전 준비
내부 Bronze 16개와 fixture hash, 02의 실제 public ZEB 실행 완료를 확인합니다. [데이터 사전](../data/README.md)의 키/타입 표를 참고합니다. nullable 용량·입고일은 정상적인 원천 상태이며 오류로 꾸미지 않습니다.

## 실행 순서
1. `02_silver`를 자신의 대상에서 실행합니다. 문자열을 trim하고 명시 schema의 date/int/long/double/boolean으로 변환합니다.
2. non-null 원천이 null로 cast되면 중단합니다. **현재 notebook은 예외로 중단할 뿐 격리 테이블을 자동 생성하지 않습니다.** 오류 행 격리·원인 검토는 별도 작업이며 “성공”으로 통과시키지 않습니다.
3. 다음 연결을 확인합니다.

```text
erp_project.project_no -> mdm_site_xref.project_no
mdm_site_xref.site_code -> pms_site.site_code
mdm_site_xref.bim_model_id -> bim_design_version.bim_model_id
pms_certificate.design_version_id -> bim_design_version.version_id
scm_purchase_order.wbs_element -> pms_equipment_plan.wbs_code
```

4. site/project/BIM MDM 중복 및 각 사이트 현행 설계가 정확히 1개인지 검사 결과를 확인합니다. 인증서 제출 모델이 같은 현장의 BIM인지도 검사합니다.
5. 아래 읽기 쿼리를 **자신의 SQL analytics endpoint**에서 수행합니다. 동기화가 지연되면 기다렸다 다시 읽고, SQL endpoint에서 Delta 쓰기를 시도하지 않습니다.

```sql
SELECT project_no,site_code,bim_model_id
FROM silver.mdm_site_xref WHERE site_code='HS-D';
SELECT version_id,version_status,version_date,selfsuff_pct,primary_energy_kwh_m2y
FROM silver.bim_design_version WHERE bim_model_id='BIM-0397';
```

## 확인할 결과
HS-D 연결은 `CT-24-0189 ↔ HS-D ↔ BIM-0397`. V1/V2는 이전, V3만 현행입니다. 인증서의 `BIM-0397-V2`를 현행 V3로 바꾸지 않습니다. **내부 Silver16개 + 필수 public ZEB1개 = 총17개**이며 각 retained source counts가 유지됩니다. 원천에는 중복/고아가 검증되지 않았으므로 결함을 발명하지 않습니다.

## 완료 기준
키·고아·타입·현행 수 검사를 모두 통과하고, 원천 metadata가 Silver에 남습니다. 기존 Silver를 일괄 DROP하지 않았습니다.

검증 실패는 다음 계층 진행 금지입니다. 키/관계 검증은 Silver table 생성 후 전체 typed 입력에 실행되므로 실패 시 일부 table이 남을 수 있습니다. 재실행으로 덮어쓰지 말고 관리자가 원인과 생성 상태를 확인합니다. 정상 fixture에 중복을 발명하거나 자동 deduplicate했다고 설명하지 않습니다.

## 다음 단계
[04. Gold 및 독립 기준 계산](04-gold.md).
