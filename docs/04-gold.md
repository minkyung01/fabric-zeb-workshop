# 04. Gold와 독립 계산으로 현재 등급 검증하기

## 업무 목적
AI의 설명을 믿기 전에 실제 설계 행과 교육 기준으로 등급을 계산합니다.

## 시작 전 준비
Silver 완료. [읽기 SQL](../sql/reference_checks.sql), [계산 해설](../data/reference-answers.md)을 엽니다. 기준은 법적 현행 적용 검토가 완료되지 않은 **잠정 교육 reference**입니다.

## 실행 순서
1. `03_gold`를 실행합니다. 같은 참가자의 Silver에서 현행/제출안을 읽고 Gold 15개 table을 만듭니다. graph refresh나 Ops 삭제는 없습니다.
2. `gold.site_status`의 actual 8행과 `gold.option_eval`의 actual 63행을 확인합니다. 열 개수와 행 개수를 혼동하지 않습니다.
3. SQL endpoint에서 `reference_checks.sql`의 첫 쿼리를 실행합니다. Gold의 저장된 grade가 아니라 Silver와 threshold를 사용합니다.
4. rank는 `+ = 0`, `1..5`, 탈락 `6`입니다. SS 하한은 `>=`, PE 상한은 **strict `<`**. 두 경로의 더 좋은(minimum) rank를 사용합니다.
5. HS-D 인증서 쿼리로 V2의 `43.5/69`와 현행 V3의 `38.2/76`을 비교합니다.
6. IC-B `39/65`를 계산합니다. SS 경로 5, PE 경로 4 → 최종 4입니다.
7. `gold.po_status`에서 `deadline_breach`를 집계하고 0인지 확인합니다. IC-B 이벤트의 +5일은 반영되지만 설치 마감을 넘지 않습니다.

Spark 성공 직후 SQL에서 새 schema/table이 보이지 않으면 writer를 다시 실행하지 않습니다. 관리자가 [SQL metadata 동기화 절차](../admin/environment.md#sql-endpoint-동기화)를 수행한 뒤 **읽기 쿼리만** 재시도합니다.

## 확인할 결과
| 현장 | 교육 등급 rank | risk |
|---|---:|---|
| HS-A | 4 | normal |
| IC-B | 4 | normal |
| SN-C | 3 | caution — planned BEMS 없음 |
| HS-D | 5 | danger — 예비 4보다 낮음 |
| SJ-E | 3 | caution — BF 우수/목표 최우수 |
| BS-F | 2 | normal |
| JJ-G | 3 | normal |
| MP-H | 5 | caution — 목표 4 |

## 완료 기준
독립 계산 8개가 Gold와 일치하고, 인증서/현행 설계가 구분되며 PO 25개 중 설치 마감 초과 0개를 확인했습니다. 원격 계량만으로 BEMS 의무를 충족했다고 주장하지 않습니다.

## 다음 단계
[05. VE 조합](05-options.md).
