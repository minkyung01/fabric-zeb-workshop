# 관리자 준비 가이드

[목차](../README.md)

Workshop 환경을 준비하고 정리하는 관리자용 문서입니다. 참가자는 보지 않아도 됩니다. 예시는 `p001` 기준이며 참가자마다 `pNNN`을 바꿔 반복합니다. 데이터 구조와 정답은 [데이터 설계](data-design.md)를 봅니다.

## 준비할 리소스

| 리소스 | 값 |
|---|---|
| Microsoft Fabric 용량 | 유료 F 용량. 12명 동시 실습 기준 **F64 이상 권장**(Copilot은 F2 이상이면 사용 가능). Trial 용량에서는 Copilot·Operations agent가 동작하지 않을 수 있습니다. |
| 참가자 작업 영역 | `zeb-pNNN` (참가자는 **Contributor** 이상) |
| Lakehouse | `lh_zeb` (**schemas 켬**) |
| 실습 파일 | Notebook 7개(`notebooks/*.ipynb`), `Files/workshop`에 `fabric/sm_zeb.tmdl`, `fabric/zeb-theme.json` |
| 네트워크 | Fabric Spark에서 `https://www.data.go.kr`로 나가는 HTTPS(02장). 막혀 있으면 아래 "공공데이터 대체 경로" |
| Power BI | 참가자 Pro 또는 PPU 라이선스 |
| Microsoft Teams | Teams 라이선스, 앱 **Fabric Operations Agent** 허용(10장). 참가자는 Fabric과 **같은 계정**으로 Teams(데스크톱 또는 웹)에 로그인할 수 있어야 합니다. |
| Microsoft Foundry (선택) | 09장용 Azure 구독·리소스 그룹, 프로젝트·모델 배포, Fabric IQ 인증 연결 |

## 1. Fabric 테넌트 설정

**Admin portal → Tenant settings**에서 참가자 보안 그룹에 아래 설정을 허용합니다. 설정 반영에 최대 1시간 걸릴 수 있습니다.

| 설정 | 쓰는 장 |
|---|---|
| Users can create Fabric items | 전체 |
| Users can create ontology (preview) items | 06 |
| Copilot and Azure OpenAI Service, (지역 밖 처리 필요 시) Data sent to Azure OpenAI can be processed outside your capacity's geographic region | 06–08 |
| Users can create and share Data agent item types | 07 |
| Operations agent (preview) 관련 설정, Real-Time Intelligence 항목 생성 | 10 |
| (선택) Users can use the Fabric MCP / Ontology MCP, Fabric IQ 관련 설정 | 09 |

공식 문서: [Ontology 테넌트 설정](https://learn.microsoft.com/en-us/fabric/iq/ontology/overview-tenant-settings), [Data agent 테넌트 설정](https://learn.microsoft.com/fabric/data-science/data-agent-tenant-settings), [Copilot 요구 사항](https://learn.microsoft.com/fabric/fundamentals/copilot-fabric-overview#available-regions), [Operations agent 요구 사항](https://learn.microsoft.com/fabric/real-time-intelligence/operations-agent#prerequisites).

Teams 관리 센터에서 **Fabric Operations Agent** 앱을 참가자에게 허용합니다.

## 2. 참가자 작업 영역 일괄 준비

`admin/provision.py`가 참가자마다 작업 영역·Lakehouse·Notebook·실습 파일을 준비합니다. 이미 있는 항목은 다시 만들지 않습니다. 관리자 계정의 Azure CLI 로그인을 사용하며 비밀 값을 저장하지 않습니다.

1.  관리자 PC에서 저장소 루트로 이동하고 Fabric 관리자(또는 용량 Contributor + 작업 영역 생성 권한) 계정으로 로그인합니다.

    ``` bash
    az login --tenant contoso.onmicrosoft.com
    ```

2.  참가자 목록 CSV를 만듭니다(예: `users.csv`).

    ``` text
    participant,upn
    p001,p001@contoso.com
    p002,p002@contoso.com
    ```

3.  먼저 `--dry-run`으로 만들 대상을 확인합니다.

    ``` bash
    python admin/provision.py --capacity <capacity-id> --participants p001-p012 --users users.csv --dry-run
    ```

4.  실제로 실행합니다.

    ``` bash
    python admin/provision.py --capacity <capacity-id> --participants p001-p012 --users users.csv
    ```

**확인할 결과:** 참가자마다 `create workspace`, `create lakehouse lh_zeb (schemas)`, `import notebook …` 7줄, `upload Files/workshop/…`이 출력됩니다. 참가자 작업 영역에 `lh_zeb`(+SQL analytics endpoint)와 Notebook 7개가 있고, Notebook의 기본 Lakehouse가 그 작업 영역의 `lh_zeb`입니다.

| 옵션 | 용도 |
|---|---|
| `--update-notebooks` | 이미 있는 Notebook을 저장소의 최신 버전으로 덮어씁니다(참가자 실행 결과는 남지만 셀 수정은 사라짐). |
| `--reference-ontology` | 참고 설계 Ontology를 `ont_zeb`로 배포합니다. 06장의 Ontology agent를 쓸 수 없는 환경이나, 시간이 부족한 참가자의 대체 경로입니다. 배포하면 `ont_zeb_lh_…`, `ont_zeb_graph_…`도 자동으로 생깁니다. Gold가 있어야 인스턴스가 읽히므로 **05장 이후**에 실행합니다. |
| `--role` | 참가자 권한(기본 `Contributor`) |
| `--tenant` | 여러 테넌트에 로그인한 경우 토큰을 받을 테넌트 |

**수동 준비:** 스크립트를 쓰지 않으면 작업 영역을 만들고 용량에 할당한 뒤, **New item → Lakehouse**에서 `lh_zeb`를 만들 때 **Lakehouse schemas**를 켭니다. **Import → Notebook → From this computer**로 `notebooks/*.ipynb` 7개를 가져오고, 각 Notebook에서 `lh_zeb`를 기본 Lakehouse로 연결합니다. `lh_zeb`의 **Files**에 `workshop` 폴더를 만들고 `fabric/sm_zeb.tmdl`, `fabric/zeb-theme.json`을 업로드합니다. Notebook 이름은 파일 이름 그대로 둡니다(`nb_apply_decision`이 `03_silver_conform`·`04_gold_model`을 이름으로 실행).

Notebook은 `notebooks/src/*.py`에서 만들어집니다. 소스를 고쳤다면 `python tools/build_notebooks.py`로 `.ipynb`를 다시 만들고 `--update-notebooks`로 배포합니다.

## 3. 공공데이터 다운로드

02장의 `01_bronze_public_ingest`는 공공데이터포털에서 **로그인·인증키 없이** 파일을 내려받습니다(이용허락범위 제한 없음 데이터). 실습 전에 관리자 점검용 작업 영역에서 한 번 실행해 4종 모두 `OK`인지 확인합니다.

- 여러 참가자가 동시에 내려받으면 포털의 다운로드 횟수 제한(`needCaptcha`)에 걸릴 수 있습니다. 참가자를 2–3개 조로 나눠 1–2분 간격으로 시작하게 하면 안전합니다. 제한에 걸린 참가자는 1–2분 뒤 3번 셀부터 다시 실행합니다.
- 포털이 파일을 갱신하면 행 수와 공공 통계 정답(07장 Q1·Q4·Q6, 08장 카드)이 바뀝니다. 실습 기준 파일은 ZEB `20251231` 9,760행입니다. 정답 Notebook `05_answers`는 항상 현재 데이터로 다시 계산하므로, 바뀐 경우 사전 점검에서 새 값을 확인해 강사 안내에 반영합니다.

### 공공데이터 대체 경로

Spark에서 포털에 나갈 수 없는 환경이면 관리자가 파일을 내려받아 제공합니다.

1.  공공데이터포털에서 4종의 CSV를 내려받아 이름을 데이터 ID로 바꿉니다: `15085042.csv`, `15003214.csv`, `15014781.csv`, `15054156.csv`.
2.  각 참가자 `lh_zeb`의 **Files**에 `public` 폴더를 만들고 4개 파일을 업로드합니다.
3.  참가자는 02장에서 parameters 셀의 `local_folder = ""`를 `local_folder = "Files/public"`으로 바꿔 실행합니다. 나머지 단계와 결과는 같으며, 수집 기록의 원본 이름이 `Files/public/… (관리자 제공)`으로 남습니다.

## 4. Microsoft Foundry (선택, 09장)

- 참가자별 또는 공용 Foundry 프로젝트, Agent Service와 모델을 지원하는 지역, 모델 배포와 할당량을 준비합니다.
- 참가자가 09장 1단계에서 **프로젝트를 직접 만드는 경우**, 쓸 **구독과 리소스 그룹**(예: `rg-zeb-pNNN`)과 지역을 미리 정해 알려 주고, 그 리소스 그룹에 리소스를 만들 권한(Contributor 이상)을 줍니다. 리소스 그룹은 프로젝트 만들기 창에서 새로 만들 수 없고 기존 그룹을 골라야 합니다.
- 참가자에게 프로젝트의 **Foundry User**, 연결을 만들 경우 **Foundry Project Manager** 역할을 줍니다.
- Fabric IQ 도구용 **BYO Entra 앱 또는 managed OAuth** 위임 인증 연결을 준비합니다. BYO Entra는 Power BI Service의 위임 권한 `Item.Execute.All`, `Item.Read.All`, 관리자 동의, Foundry가 제공하는 redirect URI 등록이 필요합니다([Fabric IQ 인증](https://learn.microsoft.com/en-us/azure/foundry/agents/how-to/tools/fabric-iq#authentication-and-security)).
- 사전 점검에서 확인한 동작(2026-10-19, Sweden Central): 새 프로젝트에서 에이전트를 만들면 `gpt-5`(글로벌 표준) 배포가 자동으로 잡혔고, **Fabric IQ(OneLake 카탈로그)** 도구를 추가할 때와 첫 질문에서 별도의 연결 선택·동의 요청이 나오지 않았습니다. 다만 이 점검은 테넌트 관리자 계정으로 했으므로, 참가자 계정에서는 동의(`CONSENT_REQUIRED`)나 연결 선택이 나올 수 있습니다. **참가자 계정 하나로 미리 질문 1개를 실행**해 확인합니다.
- 질문 하나에 1–4분 걸립니다. 동시에 여러 참가자가 질문하면 모델 할당량(TPM)을 확인합니다.
- 준비가 어렵다면 09장은 건너뛰도록 안내합니다. 필수 흐름(08 → 10)에는 영향이 없습니다.

## 5. 사전 점검 체크리스트

실습 전에 관리자가 참가자와 같은 이름 규칙의 작업 영역(예: `zeb-p001`)에서 교재대로 전체를 한 번 실행하고 아래 값을 확인합니다. 아래 값은 2026-10-18–19 점검(공공 파일 ZEB 20251231 기준)의 실제 결과입니다.

| 장 | 확인할 값 |
|---|---|
| 02 | `pub_zeb_cert` 9,760 / `pub_gseed_cert` 5,104 / `pub_bf_cert` 22,184 / `pub_green_tech_cert` 1,905, 실행 약 1.5분 |
| 03 | Bronze 21개, `pms_action_log` 0행 |
| 04 | Silver 21개, `certified_building` 25,362, BF `전라북도` 1,125·`전북특별자치도` 167 → `전북` |
| 05 | Gold 22개, ops 3개, 위험 1(HS-D)·주의 3·정상 4 |
| 07 | `05_answers` 8개: 경기 1,897→경남 870→경북 828 / B단지 4등급 가능 / D단지 / 30건 / D단지 +3일·A단지 여유 52일 / 9건·52.2% / Alpine 11/24 / OPT-D2 2억 3천만 원 |
| 08 | 1페이지 카드 9,760·2,732·+23.0%·45.1%, 2페이지 카드 8·1·3·0·34, 자립률 하한 미만 인증 176 |
| 09 (선택) | `fa-zeb` 답: 예비인증 V2(4등급), 현행 V3 38.2/76 → 5등급, OPT-D2 적용 41.4/72.5 → 4등급 / OPT-D6·D5 → 5등급 |
| 10 (제안) | `ops.option_eval` 11행, 이벤트 `ZEB-HS-D-20260930`, 추천 `OPT-D2` → 41.4%·4등급, `ZebRiskEvent` open 1행, Teams 카드 약 5분 뒤 도착 |
| 10 (승인 후) | `nb_apply_decision` 약 5–6분, 조치 1행, 설계안 V4 현행 41.4/72.5, D단지 4등급·정상, `open → approved → resolved`, 위험 0·주의 3·정상 5 |

Copilot·Ontology agent·Data agent·Operations agent·Teams 단계는 AI·UI 동작이므로 사전 점검에서 직접 확인하고, 화면이 바뀌었으면 강사 안내를 갱신합니다.

사전 점검에서 확인한 주의 사항:

- **SQL analytics endpoint 지연:** 승인 반영 후 15분 넘게 이전 값이 보인 경우가 있었습니다. 10장 11단계처럼 **Sync metadata from the Lakehouse**를 먼저 누르도록 안내합니다.
- **Teams 채팅:** 같은 계정으로 다른 실습의 Operations agent를 쓴 적이 있으면 **Fabric operations agent** 채팅에 예전 카드가 섞여 있습니다. 참가자에게 맨 아래 `oa_zeb` 카드를 쓰도록 안내합니다.
- **Ontology 그래프 새로 고침:** 승인 반영 중 `ont_zeb_graph_…` 새로 고침이 Monitor에 **Cancelled**로 남을 수 있습니다. 점검에서는 Data agent 답(V4·4등급)에 영향이 없었습니다.

## 6. 반복 실습과 초기화

같은 작업 영역에서 처음부터 다시 하려면:

1.  `oa_zeb`를 **Stop**합니다.
2.  `02_bronze_contoso_generate` → `03_silver_conform` → `04_gold_model`을 실행합니다. 조치 기록이 지워지고 D단지가 V3·위험으로 돌아갑니다(공공 데이터는 다시 내려받을 필요 없음).
3.  필요하면 `eh_zeb_queryset`에서 `.clear table ZebRiskEvent data`로 상태 이력을 지웁니다(지우지 않아도 `resolved` 다음의 새 `open`은 다시 알림을 만듭니다).
4.  `oa_zeb`를 **Start**하고 `06_risk_event`를 실행합니다.

## 7. 종료 후 정리

1.  참가자에게 `oa_zeb` **Stop**을 확인시킵니다(10장 13단계, 11장).
2.  참가자 작업 영역 `zeb-pNNN`을 삭제합니다. 작업 영역을 지우면 안의 모든 항목(Lakehouse·Eventhouse·Ontology·Data agent·보고서·Operations agent)이 함께 지워집니다.
3.  Foundry 프로젝트·리소스, 인증 연결을 정리합니다. 참가자별 리소스 그룹(예: `rg-zeb-pNNN`)을 썼다면 리소스 그룹째 삭제합니다.
4.  유료 Fabric 용량을 일시 중지하거나 삭제합니다.
