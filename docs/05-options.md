# 05. 63개 조합을 비교하되 공학 검증을 가장하지 않기

## 업무 목적
최저 비용 에너지 충족안과 실제로 승인 가능한 시공안을 구분합니다.

## 시작 전 준비
HS-D 현행 baseline `38.2%, PE76` 및 target rank4, 옵션 D1..D6를 확인합니다. [정답](../data/reference-answers.md)과 [63개 결과 JSON](../data/reference_answers.json)을 참고합니다.

## 실행 순서
1. `gold.improvement_option`의 HS-D 6행을 조회하고 SS gain은 `%p`, PE delta는 가산값, 비용은 원임을 확인합니다.
2. 비어 있지 않은 부분집합은 `2^6-1=63`입니다. `gold.option_eval`의 option_set_id는 정렬된 option ID들의 `+` 연결입니다.
3. energy_feasible=true 조합을 cost_krw 오름차순으로 조회합니다.

```sql
SELECT TOP (5) option_set_id,selfsuff_pct,primary_energy_kwh_m2y,cost_krw,
       parallel_lead_days,decision_feasible,block_reason
FROM gold.option_eval WHERE energy_feasible=1 ORDER BY cost_krw,option_set_id;
```

4. 직접 계산합니다: D5+D6 SS `38.2+1.0+0.9=40.1`, PE `76-2.0-1.8=72.2`, cost `60m+50m=110m`, 병렬 lead `MAX(30,20)=30일`.
5. D1 단독은 PE70으로 `<70`을 충족하지 않지만 SS43.5로 OR 조건을 충족합니다. D2 단독은 SS41.4/PE72.5, 230m/45일입니다.
6. 질문을 작성합니다.

```text
OPT-D5+OPT-D6가 최저 비용인 것은 어떤 가정 아래인가?
상호작용/배타성, 효과 검증, 설계 승인, 조달/설치/시운전 기간,
BEMS/본인증 조건 중 확인되지 않은 항목을 각각 표시하라.
최저 비용을 "공학 검증 완료" 또는 "자동 일정 확정"으로 표현하지 마라.
```

7. 설치 `2026-11-30`, 신청 `2027-01-15`, 취득 `2027-03-01`, 사용승인 `2027-03-31`을 참고하되 `MAX lead`를 완전한 schedule로 사용하지 않습니다.

## 확인할 결과
최저 비용 **가산 에너지 충족**안은 D5+D6이며 모든 조합의 `decision_feasible=false`입니다. 기본 입력에는 옵션 상호작용·배타성·실제 착수/시운전 검증이 없습니다. 이 누락은 판단을 막는 blocker입니다.

## 완료 기준
경계값 PE70의 strict 비교와 63개 조합을 설명하고, “공학 검토용 결정”만 기록할 수 있음을 이해합니다.

## 다음 단계
[06. Ontology와 native agent 근거 검토](06-ontology.md).
