# 06. Ontology

[목차](../README.md) \| 이전: [05. Gold와 운영 지표](05-gold.md) \| 다음: [07. Data agent](07-data-agent.md)

05장의 Gold는 사실 데이터만 담고 있습니다. "D단지가 위험한가?"에 답하려면 **같은 현장을 가리키는 시스템별 코드가 어떻게 이어지는지**, **예상 등급을 어떻게 판정하는지**를 알아야 합니다. 이 장에서는 그 업무 개념·관계·규칙을 **Ontology**에 담습니다. 07장의 Data agent는 이 Ontology를 근거로 질문에 답합니다.

**빈 Ontology 만들기 → Ontology agent 초안 검토 → Act로 적용 → 업무 규칙 넣기 → 키·바인딩·데이터 점검** 순서로 진행합니다. **1–5단계가 필수**이며, 6단계 Graph 생성은 선택입니다.

## 시작 전 확인

- 05장을 마치고 본인 `lh_zeb`의 **Tables → gold**에 테이블 22개가 있는지 확인합니다.
- 작업 영역 **Contributor** 이상 권한과 원본 테이블 읽기 권한이 필요합니다. 관리자가 **Users can create Fabric items**, **Users can create ontology (preview) items**, Copilot·Azure OpenAI 기반 AI 기능을 허용했는지 확인합니다([Ontology 테넌트 설정](https://learn.microsoft.com/en-us/fabric/iq/ontology/overview-tenant-settings)).

Ontology는 업무 개념인 **엔터티 타입**, 개념 사이의 **관계**, 원본 테이블을 연결하는 **데이터 바인딩**으로 구성됩니다. 예를 들어 `Site`는 엔터티 타입 하나이고, `gold.pms_site`의 각 행은 실제 현장 하나인 **인스턴스**입니다.

## 1. Ontology 만들기

1.  작업 영역 `zeb-p001`에서 **+ New item**을 누르고 검색 칸에 `Ontology`를 입력해 **Ontology (preview)**를 고릅니다.
2.  **Name**에 `ont_zeb`를 입력하고 **Location**이 `zeb-p001`인지 확인한 뒤 **Create**를 누릅니다.
3.  **Welcome to Ontology** 창이 나오면 오른쪽 위 **X**로 닫습니다.

**예상 결과:** 가운데에 **Get started**와 카드 3개(**Start with Ontology agent**, **Import ontology**, **Learn more**)가 보입니다. 왼쪽 **Explorer**에는 아직 엔터티 타입이 없습니다.

## 2. Ontology agent로 초안 만들기

엔터티와 관계를 하나씩 만들지 않고, **업무 목적과 질문을 Ontology agent에게 전달**해 원본을 조사하고 설계를 제안하게 합니다. 참가자는 그 제안이 질문을 지원하는지, 키·관계가 실제 데이터와 맞는지 검토합니다.

1.  **Start with Ontology agent** 카드를 누릅니다. 오른쪽에 **Ontology Agent** 창이 열립니다. 입력 칸 아래 스위치가 **Plan**인지 확인합니다. Plan은 초안·검증 단계이고 **Act**가 변경을 적용하는 단계입니다.

2.  **Say something** 칸에 아래 프롬프트를 붙여 넣고 오른쪽 아래 화살표를 눌러 보냅니다.

    ``` text
    lh_zeb Lakehouse의 gold 스키마를 조사해서 Contoso 건설의 제로에너지건축물(ZEB) 인증 컨트롤 타워 온톨로지를 설계해줘.
    목적은 공공 인증 데이터와 우리 현장 데이터를 연결해, 현장별 ZEB 예상 등급과 본인증 위험, 인증 일정, 보완안의 근거를 담당자가 따라갈 수 있게 하는 거야.
    아래 업무 질문에 필요한 엔터티, 속성, 고유 키, 관계와 데이터 바인딩을 제안하고 선택 이유를 설명해줘. 개수와 구조는 원본을 보고 판단해줘.
    - 시도·용도별 공공 ZEB 인증은 몇 건이고, 그중 4등급 이상은 몇 건인가?
    - 같은 현장의 ERP 프로젝트 번호, PMS 현장 코드, BIM 모델 번호는 무엇인가?
    - 현장의 예비인증서는 어느 설계안으로 받았고, 지금 현행 설계안은 무엇인가?
    - 현행 설계안의 에너지자립률·1차에너지소요량으로 예상 등급을 구하면 예비인증·목표 등급을 지키는가?
    - 공급사의 납품이 늦어지면 어느 발주·설비·현장의 인증 일정이 영향을 받는가? 대체 공급사는 있는가?
    - 위험 현장의 보완안은 무엇이고 비용·효과·준비 기간은 얼마인가?
    - 우리 현장과 같은 시도·용도의 공공 인증 사례는 어떤가? 설비 분야별 유효한 녹색기술 인증이 있는가?
    gold 스키마만 사용하고 ops, bronze, silver, dbo와 Files는 쓰지 마. 이름은 영어, 설명과 동의어는 한국어로 작성해줘.
    원본 열과 실제 행으로 키·관계를 검증해줘. 필요한 데이터 읽기에 실패하면 테이블이 없다고 단정하지 말고, 조회 대상과 오류 원문, 해결하지 못한 업무 질문을 보고하고 중단해. 데이터나 연결을 추측해서 만들지 마.
    먼저 Plan에서 설계 근거, 검증 결과와 미리 보기를 보여줘. 적용은 내가 검토하고 Act에서 승인한 다음에 해.
    ```

    `ops` 스키마를 빼는 이유는 05장에서 본 것처럼 `ops`가 **판단 결과**를 담기 때문입니다. Ontology에는 사실 데이터와 판단 **규칙**을 담고, 결과는 질문할 때 규칙으로 구하게 합니다.

3.  에이전트가 Lakehouse의 열과 샘플 행을 살펴보고 초안을 만든 뒤 검증할 때까지 기다립니다. 참고 시간은 3–5분입니다.

**확인할 결과:** 제안된 엔터티·키·관계·원본 테이블과 **업무 질문별 설계 근거**, 검증 결과가 있습니다. 아래 참고 설계와 비교해 **업무 범위가 빠지지 않았는지** 확인합니다. 개수나 이름이 같을 필요는 없습니다.

아래는 이 Workshop의 원본 데모에서 사용한 **참고 설계(엔터티 22개·관계 27개)**입니다. 프롬프트에 붙여 구조를 지정하지 않고, 에이전트의 제안을 검토할 때만 씁니다.

| 영역 | 엔터티 타입 (gold 테이블, 키) |
|---|---|
| 현장·코드 | `Project` (`erp_project`, `project_no`), `Site` (`pms_site`, `site_code`), `BIMModel` (`mdm_site_xref`, `bim_model_id`), `DesignVersion` (`bim_design_version`, `version_id`) |
| 인증 | `SiteCertificate` (`pms_certificate`, `cert_no`), `CertTarget` (`pms_cert_target`, `target_id`), `CertMilestone` (`pms_cert_milestone`, `milestone_id`), `ZEBGradeCriteria` (`ref_zeb_grade_criteria`, `grade_code`) |
| 설비·구매 | `Equipment` (`pms_equipment_plan`, `wbs_code`), `EquipmentCategory`, `PurchaseOrder` (`scm_purchase_order`, `po_no`), `POEvent`, `Vendor` (`scm_vendor`, `vendor_code`) |
| 보완·조치 | `ImprovementOption` (`sim_improvement_option`, `option_id`), `ActionLog` (`pms_action_log`, `action_id`) |
| 공공 인증 | `ZEBCertification`, `GSEEDCertification`, `BFCertification` (각 `pub_*`, `cert_id`), `CertifiedBuilding` (`building_key`), `GreenTechCertificate` |
| 기준 | `Region` (`ref_region`, `sido`), `BuildingUse` (`ref_building_use`, `use_group`) |

핵심 관계: `Project → BIMModel`, `Site → BIMModel`, `BIMModel → DesignVersion`, `SiteCertificate → DesignVersion`(**인증받은 설계안**), `PurchaseOrder → Equipment`(`wbs_element` = `wbs_code`), `PurchaseOrder → Vendor`, `ImprovementOption → Site`, `ZEBCertification → Region·BuildingUse·ZEBGradeCriteria`.

**업무 범위 누락이나 미해결 조회 오류가 있으면 적용하지 않고** 같은 Plan 대화에서 보완을 요청합니다.

## 3. 미리 보기와 적용

1.  답 아래 **Preview ontology**를 누릅니다. 가운데 캔버스에 초안이 열립니다. 왼쪽 아래 **Fit to screen**(네 모서리 모양)을 눌러 전체를 봅니다.

    **확인할 결과:** 위에 "You are viewing a proposed ontology from the agent. … This is a read-only view."가 보이고, 왼쪽 **Explorer**의 **AI Proposal**에 제안된 엔터티가 있습니다. 이 캔버스는 **타입과 관계의 설계도**이며 인스턴스 Graph가 아닙니다.

2.  업무 범위·원본 매핑·검증 결과에 미해결 문제가 없으면 에이전트 창의 **Switch to 'Act' + approve**를 누릅니다. 스위치가 **Act**로 바뀌고 에이전트가 초안을 적용합니다. 참고 시간은 2–3분입니다.

    **버튼이 없는 UI:** Plan 답에 텍스트 초안만 있고 **Preview ontology**·**Switch to 'Act' + approve**가 없으면, 답의 엔터티·관계 목록과 검증 결과를 먼저 검토합니다. 문제가 없을 때 직접 **Act**를 선택하고 `업무 질문과 원본 매핑을 검토한 초안을 적용해줘. gold 스키마만 사용하고 내가 검토한 엔터티·키·관계·바인딩을 유지해줘.`를 보냅니다.

**확인할 결과:** 답에 적용 완료가 표시되고, 왼쪽 **Explorer**의 **Entity Types**에 엔터티가 있습니다. **AI Proposal이 아니라 Entity Types에** 나타나는지 확인합니다.

## 4. 업무 규칙 넣기

구조만으로는 "자립률 39%면 4등급인가?"에 답할 수 없습니다. 등급 판정·본인증 조건·일정 연쇄 같은 **업무 규칙을 엔터티 설명(Description)에 넣어**, Data agent와 10장의 Foundry가 같은 규칙으로 판단하게 합니다. 원본 데모에서 이 규칙을 넣은 Ontology 연결 Data agent가 규칙·관계 질문에 가장 정확하게 답했습니다.

1.  에이전트 창의 스위치가 **Act**인지 확인합니다.
2.  아래 요청을 보냅니다. 이름·키·바인딩·관계를 바꾸는 단계가 아닙니다.

    ``` text
    아래 업무 규칙을 해당 엔터티 타입의 설명 끝에 한국어로 덧붙여줘. 아래 이름은 참고 설계의 이름이므로, 현재 온톨로지의 업무 의미와 원본 바인딩(괄호 안 gold 테이블)으로 해당 타입을 찾아줘. 대응되는 타입이 없으면 누락을 보고하고 중단해. 이름, 키, 속성, 데이터 바인딩, 관계는 바꾸지 마.
    - ZEBGradeCriteria(ref_zeb_grade_criteria): ZEB 등급은 +(ZEB+)가 가장 높고 1, 2, 3, 4, 5 순서로 낮아진다. 'N등급 이상'은 N등급과 그보다 높은 등급이다(4등급 이상 = +, 1, 2, 3, 4). 예상 등급 판정: (1) 자립률 등급 = selfsuff_pct >= selfsuff_min_pct를 만족하는 가장 높은 등급 (2) 1차에너지 등급 = primary_energy_kwh_m2y < 기준값을 만족하는 가장 높은 등급(주거용이면 primary_energy_limit_residential, 주거용 이외면 primary_energy_limit_nonresidential) (3) 최종 등급 = (1)과 (2) 중 더 높은 등급. 두 기준을 모두 충족할 필요는 없다. (4) BEMS 설치는 필수 요건이다.
    - DesignVersion(bim_design_version): version_status='현행'이 현재 설계안이다. 현장의 예상 등급은 현행 설계안의 selfsuff_pct·primary_energy_kwh_m2y에 ZEBGradeCriteria의 판정을 적용해 구한다.
    - SiteCertificate(pms_certificate): design_version_id는 인증을 받을 때 제출한 설계안이다. 예비인증을 받은 현장은 사용승인 전에 예비인증 등급 이상의 본인증을 받아야 한다. 현행 설계안의 예상 등급이 예비인증 등급보다 낮으면 본인증 위험이다. 예비인증은 설계 단계 인증, 본인증은 준공(사용승인) 무렵 인증이며 '준공 후 인증'이라고도 한다.
    - Project(erp_project): zeb_incentive가 '용적률 완화'인 프로젝트는 본인증 규칙(예비 등급 이상)이 반드시 적용된다. 주거용은 공동주택과 단독주택이고 그 밖의 용도는 주거용 이외다(ref_building_use.use_family).
    - Site(pms_site): 같은 현장의 ERP project_no, PMS site_code, BIM bim_model_id는 mdm_site_xref로 연결한다. 질문의 'D단지' 같은 이름은 일부만 일치해도 site_name이나 project_name에서 찾는다. 현장의 시도·용도는 연결한 프로젝트의 sido·use_group이며, 공공 인증과 비교할 때 같은 시도·용도를 고른다. 우리 현장은 공공 인증 데이터에 없다.
    - CertMilestone(pms_cert_milestone): 일정 순서는 1 예비인증 취득 → 2 착공 → 3 설비 설치 완료 → 4 본인증 신청 → 5 본인증 취득 → 6 사용승인이다. 미입고 발주(delivered_date 없음)가 늦어지면 새 예상 입고일 = expected_date + 지연 일수, 초과 일수 = 새 예상 입고일 − 그 현장 '설비 설치 완료' planned_date다. 초과 일수가 0보다 크면 3–6 일정이 모두 초과 일수만큼 밀리고, 0 이하이면 영향이 없다(남은 일수가 여유).
    - PurchaseOrder(scm_purchase_order): wbs_element는 Equipment의 wbs_code와 같고 vendor_code는 Vendor의 vendor_code와 같다. delivered_date가 있으면 입고 완료다.
    - Vendor(scm_vendor): is_alternative_pool=true인 공급사는 같은 category_code 설비를 대체 공급할 수 있다. 대체하면 예상 입고일 = 기준일 2026-09-30 + standard_lead_time_days다.
    - ImprovementOption(sim_improvement_option): 보완안을 적용하면 현행 설계안의 selfsuff_pct에 selfsuff_gain_pp를, primary_energy_kwh_m2y에 primary_energy_delta를 더한 값으로 예상 등급을 다시 구한다. lead_time_days는 준비 기간이며 기준일 2026-09-30부터 센다.
    - EquipmentCategory(ref_equipment_category): category_code='BEMS'가 설비 계획에 없는 현장은 ZEB 인증 필수 요건을 충족하지 못한다.
    - ZEBCertification(pub_zeb_certification): 공공 ZEB 인증 1건이다. sido는 통일한 표기(경기, 서울, 전북 등)다. cert_stage가 '본인증'이면 준공 후 인증이다.
    - GreenTechCertificate(pub_green_tech_certificate): expiry_date가 기준일 2026-09-30 이후이면 유효하다.
    - CertTarget(pms_cert_target): 녹색건축(G-SEED) 등급은 최우수 > 우수 > 우량 > 일반, BF 등급은 최우수 > 우수 > 일반 순서다.
    ```

3.  변경 요약에서 **설명만 수정**했는지 확인합니다.

**확인할 결과:** 13개 업무 개념의 설명에 규칙이 덧붙고, 3단계의 이름·키·바인딩·관계는 그대로입니다. 설명은 실행 코드가 아니라 **에이전트가 읽는 업무 맥락**입니다. 계산 정답은 07장의 정답 Notebook이 기준입니다.

## 5. 엔터티 타입과 관계 점검

생성 완료는 점검의 시작입니다. **Configure는 설계·원본 연결, Instances는 실제 데이터**를 확인하는 곳입니다.

1.  에이전트 창을 **X**로 닫습니다.

2.  **Explorer**에서 **Site**(또는 `gold.pms_site`에 연결된 타입)를 누르고 리본의 **View Entity Type details**를 누릅니다.

    **확인할 결과:** **Configure** 탭의 키가 `site_code`이고 속성의 **Data source**가 `pms_site` 열입니다. **Entity metadata**의 **Description** 끝에 4단계의 규칙이 있고, **Synonyms**에 한국어 동의어(예: `현장`)가 있습니다.

3.  **Instances** 탭을 누릅니다.

    **확인할 결과:** 현장 **8개**가 읽힙니다. `HS-D`의 이름이 `에코시티 D단지 현장`, 공정률이 `72`입니다. 에이전트가 만든 예시 값이 아니라 **바인딩한 원본 테이블의 데이터**입니다.

4.  같은 방법으로 **DesignVersion**(`gold.bim_design_version`)의 **Instances**를 엽니다.

    **확인할 결과:** 18개. `BIM-0397-V2`는 `이전`(자립률 43.5), `BIM-0397-V3`는 `현행`(자립률 38.2)입니다.

5.  **SiteCertificate**의 **Configure**에서 오른쪽 위 **Manage relationships**를 누르고, 인증서와 설계안을 잇는 관계(참고 이름 `Certificate_based_on_DesignVersion`)를 엽니다.

    **확인할 결과:** 인증서의 `design_version_id`와 설계안의 `version_id`가 연결됩니다. 이 관계가 있어야 "예비인증은 V2로 받았는데 현행은 V3"를 따라갈 수 있습니다. 방향이나 이름이 달라도 두 원본 열이 맞으면 됩니다. 확인한 뒤 아무것도 바꾸지 않고 **Cancel**을 누릅니다.

6.  `Project`·`Site`·`BIMModel`이 MDM 매핑(`mdm_site_xref`)으로, `PurchaseOrder`와 `Equipment`가 `wbs_element` = `wbs_code`로 연결되는지도 **Manage relationships**에서 확인합니다.

**점검을 마쳤으면:** 업무 질문에 필요한 구조·키·바인딩·규칙과 실제 데이터를 확인한 상태입니다. **바로 07장으로 넘어가도 됩니다.** Graph 관계 탐색까지 해 볼 때만 6단계를 진행합니다.

## 6. Graph 만들기 (선택)

Graph는 실제 인스턴스를 노드로, 연결된 인스턴스 사이의 관계를 에지로 저장합니다. 여러 단계의 관계 탐색을 해 볼 때 **Materialize**합니다. 07장의 질문 실습에 반드시 필요하지는 않습니다.

1.  리본의 **Manage graph**를 누릅니다. **Choose what to project**에서 엔터티·관계의 **Status**가 **Eligible**인지 확인합니다. **Ineligible**이나 **Not mapped**가 있으면 아래 Troubleshooting으로 원본 연결을 확인합니다.
2.  **Continue** → **Materialize**를 누릅니다. 위쪽 탭에 `ont_zeb_graph_`로 시작하는 Graph model이 열립니다. 공공 인증 행이 많아 수분–수십 분 걸릴 수 있습니다.
3.  생성이 끝나면 `ont_zeb`의 **Home**에서 **Explore graph**를 눌러 `HS-D` 현장 노드에서 설계안·인증서·설비·발주로 이어지는 관계를 펼쳐 봅니다.

Graph를 만들면 이후 `04_gold_model`이 Gold를 다시 만들 때(11장) 그래프도 자동으로 새로 고칩니다.

## 이 장의 완료 기준

- `ont_zeb`에 검토한 설계가 적용되어 있고, 위 업무 질문(공공 인증 통계, 코드 연결, 인증 설계안과 현행 설계안, 예상 등급, 일정 영향, 보완안, 공공 사례 비교)을 지원합니다. 특정 엔터티·관계 개수는 완료 기준이 아닙니다.
- 등급 판정·본인증·일정·대체 공급·보완안 규칙이 해당 엔터티의 설명에 들어 있습니다.
- `Site` 8개, `DesignVersion` 18개(D단지 V3 현행)의 실제 데이터를 읽었고, 인증서 → 설계안 관계를 확인했습니다.

## Troubleshooting

- **업무 범위가 빠진 경우(예: 보완안, 공급사, 공공 인증):** 개수가 아니라 필요한 범위의 누락이 문제입니다. 이미 적용했다면 Ontology를 삭제하지 말고 Plan 모드에서 `gold.sim_improvement_option, gold.scm_vendor를 다시 확인해서 해당 업무 질문을 지원할 엔터티·키·관계를 제안해줘. 기존 항목은 유지하고 중복 생성하지 마.`처럼 보완을 요청합니다.
- 4단계에서 대응 타입이 없다는 보고가 오면 그 업무 개념을 먼저 3단계 방식으로 추가한 뒤 규칙을 다시 넣습니다.
- **Manage graph**에서 관계가 **Not mapped**이면 관계 설정을 열어 양쪽 엔터티의 키와 **Property**의 원본 열을 확인합니다. 방향부터 뒤집지 않습니다.
- 적용을 요청했는데 변화가 없으면 입력 칸 아래 스위치가 **Act**인지 확인합니다.
- 브라우저를 새로 고치면 에이전트 대화가 사라집니다. 이미 적용한 엔터티 타입과 관계는 남아 있습니다.
- **Instances**에 데이터가 없으면 05장으로 본인 `lh_zeb`에 `gold` 테이블이 있는지, 타입의 **Data source**가 그 테이블을 가리키는지 확인합니다.
- 에이전트로 설계를 끝내지 못한 경우 관리자는 참고 설계를 본인 작업 영역에 배포할 수 있습니다([관리자 준비 가이드](../admin/README.md)의 참고 Ontology 배포).

## 공식 문서

- [Ontology agent 사용·권한·Plan/Act 모드](https://learn.microsoft.com/en-us/fabric/iq/ontology/how-to-use-ontology-agent)
- [관계 타입과 양쪽 속성·매핑 테이블](https://learn.microsoft.com/en-us/fabric/iq/ontology/how-to-create-relationship-types)
- [선택적 Graph 생성과 제한 사항](https://learn.microsoft.com/en-us/fabric/iq/ontology/how-to-use-ontology-graph)

## 다음 단계

[07. Data agent](07-data-agent.md)에서 이 Ontology를 Data agent에 연결하고 업무 질문 8개를 정답 Notebook과 비교합니다.
