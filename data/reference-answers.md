# 독립 계산 정답과 가정

**TRAINING ONLY.** 법적 인증 판정이나 에너지 시뮬레이션 검증 결과가 아닙니다. 전체 결과는 [reference_answers.json](reference_answers.json), calculator는 [reference.py](../tools/reference.py), 독립 읽기 query는 [reference_checks.sql](../sql/reference_checks.sql)입니다.

## 1. 설계와 인증서는 버전으로 연결

| 항목 | HS-D 제출안 | HS-D 현행안 |
|---|---|---|
| project/site/BIM | CT-24-0189 / HS-D / BIM-0397 | 동일 |
| version_id | BIM-0397-V2 | BIM-0397-V3 |
| version date | 2024-08-09 | 2026-07-15 |
| SS (%) | 43.5 | 38.2 |
| PE (kWh/㎡·년) | 69 | 76 |
| PV (kW) | 530 | 380 |
| 교육 energy grade | 4 | 5 |

`ZEB-P-2024-0831`, `2024-08-30`, 예비 4등급은 **V2**를 참조합니다. V3 인증 취득을 의미하지 않습니다. V3 변경 사유는 원가절감 VE 태양광 축소입니다.

## 2. rank와 OR/strict 비교

| grade/rank | SS 최소 | 주거 PE strict 상한 | 비주거 PE strict 상한 |
|---|---:|---:|---:|
| + / 0 | 120 | -10 | -70 |
| 1 | 100 | 10 | -30 |
| 2 | 80 | 30 | 10 |
| 3 | 60 | 50 | 50 |
| 4 | 40 | 70 | 90 |
| 5 | 20 | 90 | 130 |
| fail / 6 | 충족 경로 없음 | | |

각 경로의 최상 rank를 구한 뒤 `MIN(SS경로, PE경로)`를 사용합니다. SS=`>=`, PE=`<`입니다. 교육값의 출처 맥락은 기존 generator 기준표이며 **현행 규정 적용을 검증한 표가 아닙니다**.

- HS-D V3: SS38.2→5, 주거 PE76→5 →5.
- V2: SS43.5→4, PE69→4 →4.
- IC-B: SS39→5, PE65→4 →4. AND나 SS만 사용하면 틀립니다.
- SS39/PE70은 5입니다. PE70은 4등급의 strict `<70` 경로를 충족하지 않습니다.
- D1은 SS43.5/PE70이므로 PE 경로가 아니라 **SS 경로로** 4입니다.

## 3. 모든 현장

HS-A4/normal, IC-B4/normal, SN-C3/caution(BEMS 계획 없음),
HS-D5/danger(예비4 하락), SJ-E3/caution(BF 우수<최우수 목표),
BS-F2/normal, JJ-G3/normal, MP-H5/caution(목표4).
총 8, non-normal 4, danger 1입니다. BEMS 계획 flag는 인증 이행 실증이 아니며 remote meter를 자동 충분조건으로 쓰지 않습니다.

## 4. HS-D 옵션과 독립 부분집합

| ID | SS gain %p | PE delta | cost 원 | lead 일 |
|---|---:|---:|---:|---:|
| OPT-D1 | 5.3 | -6.0 | 420,000,000 | 60 |
| OPT-D2 | 3.2 | -3.5 | 230,000,000 | 45 |
| OPT-D3 | 1.4 | -1.5 | 280,000,000 | 75 |
| OPT-D4 | 2.1 | -4.0 | 340,000,000 | 50 |
| OPT-D5 | 1.0 | -2.0 | 60,000,000 | 30 |
| OPT-D6 | 0.9 | -1.8 | 50,000,000 | 20 |

非空 조합 63개. `SS=38.2+Σgain`, `PE=76+Σdelta`, `cost=Σcost`,
`parallel_lead=MAX(lead)`라는 **가산/병렬 가정**입니다.

최저 비용 energy-feasible: **D5+D6**, SS40.1, PE72.2, 110m, 30일.
D2 단독: 41.4/72.5, 230m, 45일. D6 단독: 39.1/74.2로 부족합니다.

모든 결과에 `decision_feasible=false`, blocker=`INTERACTION_EXCLUSIVITY_AND_SCHEDULE_UNVERIFIED`.
효과 간 상호작용/배타성, 설계 변경·승인, 실제 착수·조달·설치·시운전, 법적 BEMS/인증 조건은 입력에 없습니다. 이 결과만으로 작업/발주 승인하지 않습니다.

## 5. 일정과 구매

HS-D 설치 완료2026-11-30, 신청2027-01-15, 취득2027-03-01, 사용승인2027-03-31.
PO4500031202(HS-D GEO) 예상2026-11-12로 현재 마감 초과가 아닙니다.
25개 PO 모두 설치 마감 초과 0입니다.
유일한 원천 PO event는 IC-B ENV 예상일 +5일이며 effective ETA에 반영해도 마감 초과가 아닙니다.

## 6. 승인 후에도 변하지 않는 것

기본 action은 결정 기록뿐입니다. HS-D current design V3/rank5/danger,
구매 발주, 설비 plan은 바뀌지 않습니다. 같은 event 같은 payload는 1행,
다른 payload는 conflict로 거부합니다.
결정 key는 participant/scenario/event 기반이며 새 baseline은 새 event가 됩니다.
Teams 사람 Proceed/Confirm 뒤 Operations Notebook action이 creator delegated permission으로 실행됩니다. Notebook은 admin 구성의 creator ID와 action binding evidence를 기록하지만 verified human approver identity라고 주장하지 않습니다. 실제 외부 evidence reference는 `externally_supplied_not_verified`, 없으면 `not_supplied_by_platform`으로 기록합니다. 클라이언트 `human_approved`/`approved_by` flag는 거부합니다. 인간 검토의 실제 증거는 Teams confirmation/Monitor activity에서 따로 보존합니다.
