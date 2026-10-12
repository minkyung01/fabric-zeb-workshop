# 관리자 필수 준비: 공공 ZEB CSV snapshot 확보

내부 계산은 SYNTHETIC fixture만으로 재현되지만 **실제 공공 ZEB ingestion은 02장의 필수 segment**입니다. ZEB `20251231` 실제 bytes를 보존하여 2026-10-12 p01 Bronze/Silver 각 **9,760행**을 검증했습니다. 다른 참가자의 공급·실행까지 완료된 것은 아닙니다. [manifest](manifest.json)의 다른 3종 count/date는 원본 읽기 관찰값이며 미취득 상태입니다. GSEED/BF/GreenTech는 관리자 reference이고 student 정제 범위는 ZEB입니다.

| ID | 기관/데이터 | 원본 snapshot label | 관찰 행 | 실제 인증일 범위 |
|---|---|---|---:|---|
| 15085042 | 한국에너지공단 ZEB | 20251231 | 9760 | 2017-06-16~2025-12-31 |
| 15003214 | 한국부동산원 GSEED | 20251231 | 5104 | 2015-01-08~2025-12-30 |
| 15014781 | 한국장애인고용공단 BF | 20260630 | 22185 | 2008-10-30~2026-06-30 |
| 15054156 | 한국산업기술진흥원 GreenTech | 20260626 | 1905 | 2016-11-03~2025-12-18 |

원본 Notebook01 다운로드 흐름(포털 fileData 페이지→download metadata→limit check→CSV)을 표준 urllib로 재작성하여 승인된 ZEB 다운로드를 실제 실행했습니다. 실제 bytes·encoding·hash·download manifest는 비공개 staged 영역에 불변 provenance로 보존하고, 이후 live 검증의 공개 범위는 [식별자를 제거한 리허설 요약](../../validation/rehearsal-summary.json)에 기록합니다. 원본 CSV와 상세 다운로드 증거는 공개하지 않습니다.

공식 포털에서 2026-10-12 **이용허락범위 제한 없음**을 확인했습니다. 이는 kit의 재라이선스나 모든 배포 목적에 대한 승인이 아닙니다. 실제 공급은 승인된 p01 OneLake Files에만 했고, staged raw 파일은 Git 추적/공개 배포에서 제외했습니다.

```powershell
# 오프라인 status/preview만 (네트워크 없음)
python .\tools\fetch_public.py --dataset 15085042
# 별도 public-source 다운로드 승인 후에만 사용
python .\tools\fetch_public.py --dataset 15085042 --fetch --approved-public-source
```

실제 다운로드는 bytes를 `data/public/staged/15085042/source.csv`에 보존하고 manifest에 hash/name/file ID/encoding/headers/actual count/retrieval time을 기록합니다. 다른 데이터도 `--dataset`으로 선택할 수 있으나 기본 public 학습 경로는 ZEB만 정제합니다.

- HTML/captcha/잘못된 CSV·small response·변경 snapshot label은 **실패/중단**합니다. synthetic 대체를 제공하지 않습니다.
- 포털 UI/API가 바뀌었으면 관리자 수동 승인 다운로드를 사용합니다. captcha/export policy를 우회하지 않습니다.
- 기존 snapshot은 덮어쓰지 않습니다. 새 label이면 새 기준 정답을 승인받고 notebook의 label/mapping을 수정해야 합니다.
- 제공 기관/포털의 **현행 이용 조건·attribution**을 다시 확인합니다. 기존 source가 “제한 없음”이라고 표기했어도 kit가 새로운 license를 부여하지 않습니다.
- GreenTech raw에는 사업자등록번호가 포함될 수 있습니다. 본 기본 경로는 GreenTech를 배포/정제하지 않으며 실제 파일 공유 전에 목적에 불필요한 필드와 정책을 검토하십시오.

승인한 ZEB bytes+manifest를 참가자 `Files/workshop/public/15085042/`에 공급합니다. `06_public_zeb`의 PUBLIC_SNAPSHOT_APPROVED는 **실제 관리자 source 검토 후에만** true로 바꿉니다. input hash/필드/actual count/date parse를 검증합니다. 숫자06은 파일 식별 번호이며 **02장 안에서 실행하는 필수 public segment**입니다.

포털에서 승인 label 파일이 더 이상 제공되지 않거나 blocked 계정에 관리자 공급을 할 수 없으면 **공공 source blocker를 사용자/코디네이터에게 보고**합니다. 다른 label을 쓸 때는 실제 파일 hash/count/date 범위 및 mapping을 검토하여 새 snapshot 승인을 받고 manifest/notebook label을 함께 수정해야 합니다. 내부 계산 연습으로 기본 public 요구를 임의 축소하지 않습니다.

public certified buildings는 가상 내부 site와 동일 건물 데이터가 아닙니다. 지역/용도별 맥락 비교만 하며 이름을 이용한 동일 건물 join을 만들지 않습니다.
