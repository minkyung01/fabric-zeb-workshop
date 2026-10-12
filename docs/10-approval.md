# 10. Teams 인간 승인 → Notebook 결정 로그 → 확인 → Stop

## 업무 목적
검토한 **동일 event/option/baseline/result**를 사람의 Teams 확인 뒤 Operations action으로 기록합니다. 수동 `human_approved=True` 입력이나 Run all을 승인 경로로 쓰지 않습니다.

## 시작 전 준비
[08](08-operations.md)의 실제 Notebook action/Teams proposal 완료, native/SQL 근거 검토 완료, 선택 Foundry는 사용했다면 검토 완료. 생성자의 자기 대상 delegated 실행 권한 및 단일 직렬 action writer가 검증되어야 합니다. 플랫폼이 verified human approver ID를 Notebook에 제공하는 지원은 확인되지 않았습니다.

## 실행 순서
1. 제안에서 **RecordZEBDecision**과 HS-D/`OPT-D5+OPT-D6`를 확인합니다. V2 인증서는 V3 인증이 아니며, energy-feasible는 공학 검증 완료가 아니라는 점을 다시 검토합니다.
2. queryset의 HS-D snapshot에서 event_id/baseline_hash/result_hash를 읽습니다. native evidence와 [정답](../data/reference-answers.md)에 대조합니다. 자신의 **07_verify_readonly_pNN**을 열고 TARGET/default Lakehouse를 확인 후 **Run all**합니다. 이것은 실제 Silver에서 독립 계산하고 4개 identifier 및 Gold/audit를 읽기 출력하는 검증 notebook이며 승인·쓰기·조치 제출을 하지 않습니다. 출력 hash와 snapshot이 다르면 **중단**합니다. approval Notebook은 직접 실행하지 않습니다.

3. 검토자가 Teams 제안의 **Proceed**를 누릅니다. **Confirm details for RecordZEBDecision**에서 5개 parameter를 확인합니다.
   - event_id/baseline_hash/result_hash는 자신의 실제 snapshot과 일치
   - option_set_id=`OPT-D5+OPT-D6`
   - approval_evidence_ref: 실제 Teams/message/approval 증거 위치가 이미 있으면 입력; 제공받지 못했으면 빈 문자열. 임의 승인자 이름·ID·가짜 증거로 채우지 않습니다.
4. 다르면 **Cancel**. 일치하면 사람이 **Confirm**합니다. **Action submitted**는 제출일 뿐 완료가 아닙니다. Notebook 실행은 agent 생성자의 delegated permission으로 진행됩니다. 해당 tenant UI가 approval_evidence_ref의 빈 문자열 default를 허용하지 않고 실제 reference도 없는 경우 **feature constraint/blocked**로 보고합니다. 가짜 reference로 채워 실행 성공을 꾸미지 않습니다.
5. Fabric 왼쪽 **Monitor**에서 `05_decision_log_pNN` 실행을 열고 상태 **Succeeded / 성공**을 확인합니다. 실패하면 error/binding/parameters를 읽고 Stop합니다. 수동 Run all로 실패를 덮지 않습니다.
6. 자신의 SQL endpoint 또는 별도 읽기 검증 Notebook에서 다음을 확인합니다.

```sql
SELECT decision_id,participant_id,scenario_id,site_code,option_set_id,
       decision,approval_provenance,configured_creator_actor_id,
       execution_principal_verification,invocation_route_verification,human_approver_identity,
       approval_evidence_ref,approval_evidence_status,payload_hash
FROM audit.decision_log;
SELECT site_code,current_version_id,grade_rank,risk
FROM gold.site_status WHERE site_code='HS-D';
```

첫 확인은 결정 1행. decision=`record_for_engineering_review`.
approval_provenance=`operations_action_creator_delegated_platform_confirmation_required`.
human_approver_identity=`not_supplied_or_verified`, invocation_route_verification=`notebook_cannot_verify_platform_origin`. configured creator는 administrator binding의 actor ID이지 notebook에서 검증한 runtime 사람 identity가 아닙니다. 이 row만으로 실제 Teams-origin 호출을 증명하지 않습니다.
reference가 있으면 `externally_supplied_not_verified`, 없으면 `not_supplied_by_platform`입니다. 이 표기가 인간 승인 검증을 대체하지 않습니다. **Teams 확인 및 Monitor activity 증거를 외부 validation 기록에 함께 보존**합니다.

7. 같은 parameters를 동일 직렬 action 경로로 다시 제출한 경우 같은 payload는 1행 유지해야 합니다. 다른 option/result/evidence의 같은 event key는 conflict로 거부하며 기존 audit를 보존합니다. 테스트는 별도 리허설 승인 후 수행합니다. 중복 writer 동시 실행은 지원하지 않습니다.
8. audit 1행과 Monitor 성공을 확인한 뒤 **명시적 Eventhouse 상태 동기화**를 수행합니다. 아래 쿼리의 `pNN`, `검증한64자리event_id`를 실제 확인된 값으로 바꾸고 자기 queryset에서 **Run**합니다. notebook은 자동 이중쓰기를 하지 않습니다.

```kql
.set-or-append WorkshopRiskSnapshot <|
WorkshopRiskSnapshot
| where participant_id == 'pNN' and scenario_id == 'HS-D-VE-20260930'
| where site_code == 'HS-D' and event_id == '검증한64자리event_id'
| summarize arg_max(status_time, *) by participant_id, scenario_id, event_id
| where event_state == 'open'
| extend status_time = now(), event_state = 'recorded'
| project event_id, participant_id, scenario_id, site_code, baseline_hash, risk,
          progress_as_of, event_state, status_time, recommended_option_set_id, result_hash
```

이것은 **결정 기록됨** marker이며 설계/risk가 해결됐다는 뜻이 아닙니다. latest status query에서 HS-D가 recorded이고 다른 3개 risk는 open인지 확인합니다. 같은 marker 재실행은 latest가 recorded면 0행 추가입니다.
9. status sync가 실패하면 audit는 보존하고 **Stop**합니다. `audit_written / status_sync_pending`을 외부 리허설 기록에 남깁니다. audit를 다시 생성하지 말고 상태 query/marker만 재시도합니다. Eventhouse와 Delta는 단일 transaction이 아닙니다.
10. Operations agent toolbar의 **Stop**을 누르고 다시 열었을 때 **Start**가 보이는지 확인합니다. 반복 open 알림을 방치하지 않습니다.

## 확인할 결과
실제 Teams Proceed/Confirm → action 제출 → Monitor 성공 → decision 1행 → recorded 상태 확인 → Stop입니다. HS-D는 여전히 V3/grade5/danger, 설비/PO는 unchanged입니다. 사람 검토 증거와 creator-executed invocation provenance를 **서로 구분**합니다.

## 완료 기준
위 승인/action 실행/저장/상태/Stop 증거가 모두 있습니다. parameter 문자열이나 admin binding flag만으로 인간 승인 완료를 증명하지 않습니다. platform 기능/권한 실패로 수동 Notebook만 실행했다면 요청한 기본 경로는 **미완료**입니다.

## 다음 단계
[11. 마무리](11-finish.md). 별도 trusted-human-identity 통합과 공학/법적 적용은 후속 보안·업무 검토 범위입니다.
