# 09. 선택 확장: Foundry Fabric IQ 근거 검토

## 업무 목적
외부 Foundry의 Fabric IQ 도구 결과를 추가 근거로 검토합니다. 기본 과정은 Foundry 없이 끝낼 수 있습니다.

## 시작 전 준비
Teams proposal은 아직 승인하지 않았습니다. 관리자에게 preview 기능, 외부 서비스 연결/consent, 비용, cross-region 처리, 본인 대상 read-only 권한을 **별도 승인**받아야 합니다. 본 단계의 실제 tool/runtime 성공은 아직 검증되지 않았습니다.

## 실행 순서
1. 관리자에게 **별도 승인·준비된 Foundry project/model deployment**를 받습니다. project **에이전트 빌드 → 빌드 시작 → 에이전트 만들기**, 이름=`fa-zeb-pNN`, 상호 작용 모드=`텍스트` → **만들기**. project/connection 미준비면 “선택 확장 미실행”으로 표시하고 [10](10-approval.md)으로 갑니다. 본 실습이 Azure subscription/지역/모델/권한을 자동 선택하거나 생성하지 않습니다.
2. Playground **지침**에 `내 ont_zeb_pNN의 Fabric IQ 도구 결과만 근거로 사용하고 Teams 승인 전에 수치/키/제약을 검토한다. 승인/거절/조치 실행을 하지 않는다.`를 입력합니다. **도구 → 추가 → 도구 추가 → 구성됨 → Fabric IQ(OneLake 카탈로그) → 도구 추가**, **키워드로 필터링**에 `ont_zeb_pNN`, 위치=자신의 workspace를 확인 → **추가**. 관리자 준비 BYO Entra/managed OAuth 연결을 선택하고 승인된 읽기 계정으로 인증/consent합니다. 웹 검색 도구는 **⋮ → 제거**하고 **저장**합니다. UI/도구가 없으면 선택 단계 blocked이며 비슷한 다른 도구를 있다고 가정하지 않습니다.
3. 다음 prompt를 사용합니다.

```text
Use the approved participant ontology only. For HS-D, identify the submitted
design version of ZEB-P-2024-0831 and the current design version.
Return entity keys, bound source evidence, SS/PE/PV values and limitations.
Compare the proposed OPT-D5+OPT-D6 engineering-review decision to Gold evidence.
Do not approve or execute any action. Do not claim business-rule execution.
```

4. 질문 답 아래 **추적 → ont_zeb_pNN: ask_ontology**(실제 server label을 확인)를 선택하고 **입력/출력**에서 tool name·대상 Ontology·반환 entity keys·근거 행/값·오류를 읽습니다. 필요 시 `mcp_list_tools`에서 실제 tool 발견을 확인합니다. business rules가 `ask_ontology` 응답에 반영된다고 보장하지 않습니다.
5. [독립 SQL](../sql/reference_checks.sql)과 비교합니다. V2/V3 오연결이나 PE 조건 오류가 있으면 답변을 신뢰하지 않습니다.
6. Teams로 돌아가며, Foundry 호출 성공을 인간 승인으로 간주하지 않습니다.

## 확인할 결과
기본 경로와 같은 `V2→V3`, `4→5`, `D5+D6 110m` 근거가 비교됩니다. 외부 결과가 틀리면 오류를 표시하고 수정 검토하며 자동 승인하지 않습니다. 별도 외부 자원을 이 오프라인 키트 작성 단계에서 만들거나 호출하지 않았습니다.

## 완료 기준
확장 실행 시 tool evidence와 대상·수치 대조가 존재합니다. 미실행도 기본 과정 완료를 막지 않으며 라이선스/지역/권한/비용 blocker를 정직하게 남깁니다.

## 다음 단계
[10. Teams 사람 승인과 결정 로그](10-approval.md).
