# 관리자: 환경·배포·12명 격리

## 현재 상태와 승인 게이트

2026-10-12 별도 승인된 **p01 한 환경**에서 실제 notebook/Files·Ontology·Direct Lake·보고서·Eventhouse·Operations Start/Stop 리허설을 수행했습니다. [식별자를 제거한 실제 리허설 요약](../validation/rehearsal-summary.json)은 이 환경에만 해당하며 나머지 11명은 프로비저닝/실행하지 않았습니다. 승인된 기존 capacity는 최종 18:42 KST ARM `state=Paused`와 Azure UI `일시 중지됨`을 확인했습니다. **승인/재개 당시 F16이었지만 최종 ARM과 콜드 재열기에서는 F64가 관찰됐습니다. 이 리허설은 SKU 변경 요청을 하지 않았고 원인/행위자를 검증하지 못했습니다. 자동 재개·SKU 복원을 하지 말고 먼저 capacity 변경 이력을 조사하십시오.** trial/SKU 변경을 전제하지 않습니다.

기본 데이터·계산은 로컬에서 재현됩니다. p01 native Ontology·Direct Lake·Copilot과 case-specific IC-B 교육 근거 measure/native 답변을 검증했습니다. 브라우저 다운로드 없이 실제 retained OneLake file을 직접 수집했고 latest 4행/원래 11개 schema/교육 날짜/승인한 hashes를 확인했습니다. 17:55 KST의 정확한 미리보기 승인 후 native Start를 실행했으나 30분 이상 관찰한 activity/정확한 Teams bot에 p01 제안이 나타나지 않았습니다. 원인은 미확정이며 native delivery 성공으로 간주하지 않습니다. 18:40 KST 실제 Stop, public `shouldRun=false`, `05_decision_log` job history 0을 확인했습니다. 권한 확대·직접 메시지 대체·05 직접 실행·사람 Proceed/Confirm 자동화는 하지 않았습니다. Foundry는 선택 확장이며 실행하지 않았습니다.

## 배치 설계

| 대상 | 구성 |
|---|---|
| 읽기 전용 참고 | 원본 WS_ZEB / lh_zeb, 원본 Ontology 및 기존 모델 |
| p01..p12 각각 | 별도 ws_zeb_pNN, schema-enabled lh_zeb_pNN, 8 notebook, ont_zeb_pNN, sm_zeb_pNN, rpt_zeb_pNN, eh_zeb_pNN/KQL, ops_zeb_pNN, 자기 audit |
| 바깥 서비스 | Teams proposal/사람 승인; 선택 Foundry Fabric IQ |

한 Lakehouse에서 participant column만 나누는 공유 실습이 아닙니다. 동일한 workspace/Lakehouse ID를 두 참가자에게 배정하지 않습니다. 같은 이름의 ID를 추정하지 말고 실제 item/workspace readback으로 확인합니다.

## 별도 승인 후 준비 절차

1. 관리자가 비공개 원본 inventory와 현재 로그인 조직을 대조한 올바른 tenant에서 workspace와 참가자 소유 Lakehouse를 만들고 schema 지원을 확인합니다. 다른 Azure CLI 계정을 자동 재사용하지 않습니다. 실제 tenant/account 식별자는 공개 kit에 넣지 않습니다.
2. 관리자가 각 workspace membership/소유/실제 Lakehouse의 workspace 소속을 확인합니다. 참가자는 자신의 item만 편집합니다. source 접근은 읽기 전용으로 제한합니다.
3. 승인된 paid capacity에 배정합니다. 원본에서 관찰된 F16/Korea Central은 **12명 concurrent Spark/AI 성공 근거가 아닙니다**. 큐·Spark pool/CU/AI 사용량을 리허설에서 확인하고 동시 실행 창을 나눕니다. “12개 모두 free parallel”을 약속하지 않습니다.
4. **승인된 참가자 수만큼** metadata readback을 evidence로 보존한 뒤 `config/targets.example.json`을 `config/targets.json`으로 복사하고 실제 대상을 입력합니다. p01-only 승인으로 나머지 11개 target을 생성/승인하지 않습니다.
   - 실제 workspace_id/lakehouse_id
   - `protected_workspace_ids` / `protected_lakehouse_ids`: 관리자가 **비공개 원본 inventory**에서 확인한 모든 보호 원본 ID를 각각 비어 있지 않은 UUID 목록으로 입력합니다. target ID를 원본 목록에 넣지 않습니다. 예제의 빈 목록은 실패하도록 설계됐으며 목록이 없거나 placeholder이면 preflight/packaging 모두 거부됩니다. 이 목록은 private `targets.json`에서 자기 대상 prepared notebook의 TARGET에 포함되며 공개 템플릿에는 실제 ID를 넣지 않습니다.
   - participant_id p01..p12, scenario_id HS-D-VE-20260930
   - 실제 name ws_zeb_pNN/lh_zeb_pNN
   - binding_verified=true와 binding_evidence_ref
   - approved_target=true
   - genuine ZEB source를 실제 검토했을 때만 `public_snapshot_reviewed=true`, `public_review_evidence_ref`=실제 retained source/hash/license 검토 증거. source가 존재한다는 사실만으로 승인을 만들지 않습니다.
   - serialized_writer_attested는 **동시에 실행되지 않는 단일 Operations action writer를 확보한 뒤에만** true
   - `platform_approval_binding_verified`, `configured_creator_actor_id`, `action_binding_evidence_ref`는 처음에는 false/null/빈문자열. 08의 실제 Notebook action 연결을 검증한 뒤 아래 절차로 설정합니다. parameter 문자열은 이 admin 설정을 덮어쓰면 안 됩니다.
5. placeholder/null/원본 ID는 도구가 거부해야 합니다. `targets.json`과 prepared definitions는 `.gitignore`로 공개 추적되지 않습니다.

```powershell
# 로컬 preview: 네트워크/배포 없음
python .\tools\prepare_distribution.py .\config\targets.json
# 정확한 검증 대상에 바인딩한 로컬 package만 생성
python .\tools\prepare_distribution.py .\config\targets.json --prepare --approved-offline-bindings
```

6. [배포 계약](../deployment/README.md)의 `deployment/prepared/pNN` notebook definition과 Files manifest를 **별도로 승인된** 관리자 배포 경로에 전달합니다. 도구는 실제 workspace/Lakehouse를 만들거나 cloud API를 부르지 않습니다. 미해결 모델/Ontology/Operations는 item names와 학습 계약이지 완료된 item payload가 아닙니다.
7. `data/synthetic/fixtures.json`을 각 Lakehouse `Files/workshop/fixtures.json`으로 공급합니다. snapshot 원천 JSON과 CSV 16개/manifest는 kit에 있으므로 관리자 검증에 사용할 수 있습니다. **공공 ZEB 필수 segment**는 [공공 준비](../data/public/README.md)에 따라 실제 bytes/hash/manifest를 `Files/workshop/public/15085042/`에 별도 공급합니다. 미취득이면 public 준비/02장 완료를 blocked로 표시합니다. 내부 계산 성공으로 이 요구를 없애지 않습니다.
8. 다운로드가 막힌 계정은 승인된 definition/Files 관리자 배포를 사용합니다. 정책 우회 브라우저 자동 다운로드, export control 무력화는 하지 않습니다.
9. 대안으로 read-only OneLake shortcut을 허용할 경우 **source permissions 자체가 쓰기/삭제를 금지해야 합니다.** shortcut이라는 사실만으로 read-only가 되지 않습니다. 같은 Fabric OneLake에 별도의 external service credential/Access Connector를 만들지 않습니다.
10. 브라우저 Save a copy 사용 시 실제 dialog의 이름/대상 위치와 default Lakehouse를 검사합니다. 원본에서 `다른 이름으로 저장`/`새 노트북으로 저장` dialog는 확인했으나 저장/실행은 하지 않았습니다.
11. 00_preflight를 먼저 실행하고 실제 runtime currentWorkspaceId/defaultLakehouseId를 approved config와 대조합니다. 대상 ID뿐 아니라 데이터에 다른 참가자 record가 없는지도 확인합니다.
12. notebook 실행 순서는 00 preflight → 01 Bronze → **06 public ZEB(02장 필수)** → 02 Silver → 03 Gold입니다. 추가 pipeline은 **선택**이며 이 순서를 유지하고 동시 활동 수를 리허설로 제한합니다. 04 snapshot은 Files만 만드는 명시 전송 준비이므로 Start 전에 준비할 수 있으나 ingest/Start/알림은 별도 승인 경계입니다. 05 log는 Teams 승인 후 action에, 07 verify는 읽기 검증에만 씁니다. graph refresh, 임의 reset, audit 삭제는 포함하지 않습니다.

## Files/Tables와 Git

Lakehouse Git/배포는 Tables/Files 데이터를 복사하지 않습니다. notebook만 복사됐다고 실습 가능으로 표시하지 마십시오. 파일 제공, default binding, Spark run, SQL endpoint sync를 각각 확인해야 합니다.

기본 notebook은 native built-in Spark를 사용합니다. standalone SparkSession builder, dbutils, Unity Catalog, Shared clone, Access Connector, serverless assumptions는 없습니다. 쓰기는 Spark Delta에서 수행하며 SQL analytics endpoint는 읽기 검증에 사용합니다.

## SQL endpoint 동기화

p01에서 Spark Delta 성공 직후 SQL catalog가 잠시 비어 있었습니다. **데이터 writer를 재실행하거나 테이블을 drop/recreate하지 않습니다.** 승인된 자기 SQL endpoint에 현행 [refreshMetadata API](https://learn.microsoft.com/en-us/rest/api/fabric/sqlendpoint/items/refresh-sql-endpoint-metadata)를 좁은 table allowlist로 실행하고 operation/result를 확인합니다.

```http
POST /v1/workspaces/{approved_workspace_id}/sqlEndpoints/{approved_endpoint_id}/refreshMetadata
Content-Type: application/json
x-ms-fabric-skill: sqldw-cli

{"recreateTables":false,"tables":[{"schema":"gold","tableNames":["site_status","option_eval","po_status","site_certificate"]}]}
```

이는 administrator metadata synchronization이며 Lakehouse data write가 아닙니다. p01에서는 public/독립 검증용 8개 table refresh가 Success였고, 이미 동기화된 Gold table은 성공 시각과 함께 NotRun을 반환했습니다. 이어서 **SELECT만** 재실행하여 public9760/9760, site8/options63/PO25/breach0를 확인했습니다. timeout에는 결과 미확인으로 표시합니다.

native Ontology Act는 자기 workspace에 Eventhouse/KQL database/GraphModel backing item을 자동 생성할 수 있습니다. 이는 별도로 만든 Operations risk Eventhouse 완료 증거가 아닙니다. 실제 item inventory와 각 binding을 함께 보존합니다.

## 실패·재실행·복구

모든 Bronze/Silver/Gold 첫 쓰기는 `errorifexists`입니다. schema 전체 table enumeration/drop/overwrite가 없습니다. 일부 table 생성 후 실패하면:

1. 즉시 stage를 중단하고 오류/생성된 **알려진 표**를 기록합니다.
2. 기존 데이터와 schema/count/hash를 읽기 검증합니다. 실패를 성공으로 덮지 않습니다.
3. 본 키트에는 자동 reset 도구가 없습니다. 관리자가 별도 승인한 **새 참가자 소유 Lakehouse**에 재바인딩하여 재현하는 경로가 안전한 기본 복구입니다. 원래 audit를 보존하며 새 대상도 ownership evidence와 preflight가 필요합니다.
4. 불가피한 기존 table reset은 별도 change approval과 명시적인 알려진 participant table allowlist만 대상으로 하십시오. audit는 삭제하지 않습니다. DROP ALL, schema enumeration loop, 자동 overwrite는 금지입니다.

## 인간 승인/신원과 audit

요청한 경로는 **Teams 사람 승인 → Operations Notebook action → audit**입니다. [08장의 실제 UI·5개 parameter·instructions](../docs/08-operations.md)와 [action contract](../operations/action-contract.json)를 그대로 사용합니다. 05는 `record_for_engineering_review`만 기록하며 설계/PO/옵션 효과를 적용하지 않습니다. 수동 Run all 또는 `human_approved=True` 입력은 승인 경로가 아닙니다.

### Action binding 검증 및 admin 구성

1. 08에서 자신의 `ops_zeb_pNN` **Actions → RecordZEBDecision → Review and create**를 확인합니다. Notebook=`05_decision_log_pNN`, workspace=자신, 매개 변수=event_id/option_set_id/baseline_hash/result_hash/approval_evidence_ref **5개 string**인지 검사합니다.
2. **Agent behavior** 수신자와 생성자가 본인 실습 계정인지 확인합니다. 생성자의 Entra object ID는 승인된 관리자가 **Microsoft Entra admin center → Users → 해당 계정 → Properties → Object ID** 등 조직의 허용된 identity 조회 방법으로 readback합니다. 입력하는 값은 실제 확인된 ID이지 임의 예시 GUID가 아닙니다. action의 workspace/Notebook/default Lakehouse/TARGET를 자기 대상으로 제한하고 다른 참가자와 original source writes를 금지합니다. 기존 관리자 계정에 더 넓은 권한이 있더라도 권한을 확대·변경하지 않으며, target binding을 확인했다고 계정의 전역 권한까지 p01로 제한됐다고 주장하지 않습니다.
3. binding readback/creator/수신자/execute 범위 확인 증거 위치를 `action_binding_evidence_ref`에 기록합니다. 증거는 실제 readback 기록이어야 하며 코드가 reference 내용의 진위를 인증해 주지 않습니다.
4. `config/targets.json`의 해당 참가자에 아래 값을 업데이트하고 **자기 05 notebook의 TARGET 셀**에도 동일 값을 저장합니다. TARGET 셀은 **parameter tag가 없어야** 하며 agent가 변경할 수 있는 parameter 목록에 포함하지 않습니다.

```python
# 실제 자신의 TARGET dictionary에서 아래 key 값만 관리자 검증 후 변경
# 실제 Object ID/증거 위치는 관리자가 얻는 필수 값이며 예시 문자열은 실행값이 아님
TARGET["platform_approval_binding_verified"] = True
TARGET["configured_creator_actor_id"] = "실제_생성자_Entra_Object_ID"
TARGET["action_binding_evidence_ref"] = "실제_binding_readback_증거_위치"
TARGET["serialized_writer_attested"] = True
```

이는 **절차상 admin gate**이지 platform-signed 승인 토큰이 아닙니다. 임의 clientflag로 인간 identity를 증명하지 않습니다. notebook의 parameter-tag 셀은 **flat5 string만** 유지합니다. 변경 후 **Save**하고 Actions의 Parameters를 다시 읽습니다. **Run all은 하지 않습니다**. 초기 prepared package에 false로 저장해둔 경우 실제 binding 검증 후 이 자기 대상 설정만 갱신합니다. 재배포는 별도 승인된 target Notebook만 대상으로 하며 source를 수정하지 않습니다.
5. Teams에서 **Proceed → Confirm details for RecordZEBDecision → Confirm**, **Action submitted**, **Monitor Succeeded**, audit row를 각각 확인합니다. 어느 단계가 없으면 승인/action 실습 미완료입니다. 해당 기능이 tenant에서 없다고 수동 실행으로 완료 처리하지 않습니다.

### Identity 제한과 운영 책임

Operations는 **creator delegated permission**으로 실행됩니다. 이것은 human approver identity를 의미하지 않습니다. 현재 제공 근거는 5개 notebook string parameter discovery/실행이며 verified approver ID나 signed approval token 전달은 확인되지 않았습니다.

따라서 notebook은 **configured creator ID + platform-action provenance**, `human_approver_identity=not_supplied_or_verified`를 기록합니다. 외부 approval evidence reference가 있으면 `externally_supplied_not_verified`, 없으면 `not_supplied_by_platform`입니다. freely supplied `human_approved`, `approved_by`, `identity_mode` flag는 validator가 거부합니다.

**중요한 미해결 보안 경계:** 동일 execute 권한을 가진 creator가 05를 직접 호출하면 notebook만으로 그 호출과 Teams 승인 action을 암호학적으로 구분할 수 없습니다. admin binding flag/parameter는 그런 proof가 아닙니다. 실습에서는 직접 호출 금지, 자기 대상 execute 범위, 실제 Teams confirmation/Monitor activity 증거를 함께 검토합니다. 운영용 trusted approval을 요구하면 플랫폼이 공급하는 서명된 승인/호출 ID 또는 별도 인증된 orchestration 검증이 필요하며 **미구현 상태**를 보고해야 합니다. 불가능한 runtime proof를 꾸며 넣지 않습니다.

한 audit table은 한 직렬 action invocation만 실행합니다. Delta MERGE는 unique constraint나 Eventhouse와의 분산 transaction이 아닙니다. 중복/충돌은 pre/post readback으로 검사하며 경쟁 writer는 켜지 않습니다. 재제출 시 parameters/evidence reference까지 동일 payload를 유지합니다.

실제 p01에서는 actor Object ID와 workspace Admin role, 자기 KQL/05 binding, 5개 string을 확인한 뒤 **05 TARGET의 admin 필드만** 갱신했습니다. updateDefinition LRO Succeeded와 후속 getDefinition에서 default Lakehouse/parameter tag/TARGET 값을 확인했고 05 job history는 **0건**입니다. `serialized_writer_attested=True`는 한 운영자·한 action으로 직렬 실행한다는 **절차상 통제**이지 서버 queue/lock/unique constraint의 실증이 아닙니다. [공개 요약](../validation/rehearsal-summary.json)의 action configuration은 비공개 실제 ledger의 binding readback을 요약하며 인간 승인 증거가 아닙니다.

## 모니터링 상태

기본 경로는 explicit snapshot→Eventhouse ingest→proposal→사람 검토→**Teams Proceed/Confirm→creator-delegated Notebook action→audit**→explicit recorded 상태 확인→Stop입니다. audit 성공이 risk/design 상태를 바꾸지 않습니다.

재시작 전 audit를 확인하고 이미 기록된 event를 제외한 latest-status view를 검증합니다. [10장의 `.set-or-append` 명시적 recorded marker](../docs/10-approval.md)는 audit readback 후 사람의 확인으로만 실행합니다. Notebook에 자동 dual-write가 없으므로 status가 자동 갱신됐다고 하지 않습니다. status sync failure는 `audit_written / status_sync_pending`으로 기록하고 Stop 후 상태 marker만 재시도합니다. 원본 audit를 삭제/중복 작성하지 않습니다.

## 제한

- 법적 기준 최신 적용, remote-meter/BEMS 해석 미검증.
- 에너지 효과 가산·옵션 배타성·실제 schedule/commissioning 미검증.
- ZEB genuine snapshot은 p01만 공급·검증; 다른 3종 미취득, 공개 Git 배포 없음.
- p01 Copilot 페이지·조회·인사이트와 IC-B 전용 교육 근거 measure의 native 답변을 실행했습니다. class/threshold는 retained synthetic fixture에서 명시적으로 넣은 case-specific 근거이며 동적 criterion table이나 법적 인증 검증은 아닙니다.
- genuine OneLake latest 4행 수집과 Operations/playbook/action 구성, 승인된 Start/Stop은 완료했습니다. native Teams 제안은 관찰되지 않았고 사람 확인·Notebook 실행·audit/recorded는 미실행입니다. 실제 native Teams card 문구/포장을 Start 전에 확인하거나 byte-for-byte 고정한 증거는 없습니다.
- 다운로드 금지 사용자 배포 및 12명 동시 성능 미검증.

검증과 화면 캡처는 [validation.md](validation.md)에서 별도로 관리합니다.
