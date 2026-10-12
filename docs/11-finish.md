# 11. 결과와 미완료 항목을 정직하게 남기기

## 업무 목적
재현 가능한 데이터·계산·검토·결정을 전달하면서 local 테스트와 live 성공을 구분합니다.

## 시작 전 준비
실제로 수행한 단계만 표시합니다. 오프라인 키트 검증과 Fabric 학생 리허설은 다릅니다. [검증 체크리스트](../admin/validation.md)를 엽니다.

## 실행 순서
1. 본인 workspace/Lakehouse binding, fixture hash, **필수 public ZEB snapshot hash/manifest/실제 ingestion**, 내부+public Bronze/Silver counts, Gold 8/63/25 결과를 정리합니다. public bytes 미제공이면 02는 blocked입니다.
2. HS-D V2/V3 증거와 IC-B OR 반례, PE70 strict 경계를 설명합니다.
3. 수동 report 첫 페이지와 **Copilot 둘째 페이지 생성/데이터 질문/인사이트 요청**의 실제 응답, fields/measures 검사 및 저장·재열기 결과를 남깁니다. 기능 unavailable/error면 해당 stage 미완료이며 수동 대안으로 완료 처리하지 않습니다.
4. native Ontology key/binding과 Plan evidence 검토를 확인합니다. materialized graph의 갱신 시점이 불명확하면 제한으로 적습니다.
5. Operations ingest/snapshot/proposal/**Teams Proceed/Confirm → creator-delegated Notebook action → audit → 명시적 recorded status → Stop**의 실제 수행 여부·증거를 기록합니다. 인간 approval identity는 notebook에서 검증되지 않으며 Teams/Monitor 증거와 실행 provenance를 분리합니다. 화면이 없으면 screenshot이 있다고 하지 않습니다.
6. Foundry는 선택이며 미실행 시 “optional not run”으로 적습니다.
7. 로컬 저장소에서 아래 검사로 배포 파일과 정답을 다시 확인합니다.

```powershell
python -m unittest discover -s tests -v
python .\tools\check_kit.py
```

8. 관리자에게 공공 source 미취득, 법적 기준 미검토, 공학/일정 blocker, Copilot/Operations/Teams/Foundry runtime 및 12명 concurrency 미검증을 전달합니다.
9. notebook session과 agent가 종료되었는지 확인합니다. capacity pause/재개는 사용자 승인 받은 관리자가 수행하며 학생이 임의로 조작하지 않습니다.

## 확인할 결과
결정 로그는 실제 조치가 아니라 검토 기록입니다. 공학 검증/법적 인증, 위험 해결, 고객 시스템 통합, 자동 OneLake→Gold/Eventhouse 동기화 성공을 주장하지 않습니다.

## 완료 기준
자신이 한 일과 못 한 일을 분리해 보고했습니다. live 미완료 항목을 local PASS로 덮지 않았습니다. 원본과 다른 참가자 환경이 변경되지 않았습니다.

## 다음 단계
관리자가 [리허설 승인 및 체크](../admin/validation.md)를 수행합니다. 추가 실제 시스템/Foundry 통합은 별도 설계·권한·비용 승인 대상입니다.
