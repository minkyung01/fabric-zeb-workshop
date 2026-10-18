# 01. 작업 영역 준비

[목차](../README.md) \| 이전: [00. 시나리오와 실습 순서](00-scenario.md) \| 다음: [02. Bronze ① 공공 인증 데이터](02-bronze-public.md)

실습에 쓸 본인 작업 영역을 확인합니다. 이 장의 목표는 **작업 영역이 유료 용량에 있고, Lakehouse와 Notebook 7개가 준비되어 있으며, Notebook이 본인 Lakehouse를 기본으로 쓰는지 확인하는 것**입니다. 데이터 적재는 다음 장부터 합니다.

**Fabric 접속 → 작업 영역·용량 확인 → Lakehouse와 실습 파일 확인 → Notebook의 기본 Lakehouse 확인** 순서로 진행합니다.

## 시작 전 준비

- 관리자에게 받은 실습 계정과 참가자 번호(예: `p001`)
- 관리자가 준비한 본인 작업 영역 `zeb-p001`(활성 유료 Fabric 용량에 할당)과 **Contributor 이상** 권한

문서의 `p001`은 예시입니다. 화면에서는 **본인 번호의 작업 영역**을 선택합니다. 다른 참가자의 작업 영역에서는 실행하지 않습니다.

## 1. Fabric 접속과 작업 영역 확인

1.  브라우저에서 <https://app.fabric.microsoft.com>을 열고 실습 계정으로 로그인합니다.
2.  왼쪽 **Workspaces / 작업 영역**을 누르고 `zeb-p001`을 엽니다.
3.  도구 모음의 **Workspace settings / 작업 영역 설정**을 누르고 **License info / 라이선스 정보**를 엽니다.

**예상 결과:** **License mode**가 **Fabric capacity**이고 관리자가 안내한 용량 이름이 보입니다. **Trial**이나 **Pro**이면 Copilot·Operations agent 단계가 진행되지 않으므로 관리자에게 알립니다. 설정 창은 오른쪽 위 **X**로 닫습니다.

## 2. 작업 영역 항목 확인

작업 영역 목록에서 아래 항목이 있는지 확인합니다. 관리자가 미리 넣어 두었습니다.

| 항목 | 종류 | 쓰는 장 |
|---|---|---|
| `lh_zeb` | Lakehouse (같은 이름의 **SQL analytics endpoint**도 함께 보임) | 전체 |
| `01_bronze_public_ingest` | Notebook | 02 |
| `02_bronze_contoso_generate` | Notebook | 03 |
| `03_silver_conform` | Notebook | 04 |
| `04_gold_model` | Notebook | 05 |
| `05_answers` | Notebook | 07 |
| `06_risk_event` | Notebook | 09 |
| `nb_apply_decision` | Notebook | 11 (Operations agent가 실행. **직접 실행하지 않음**) |

**예상 결과:** Lakehouse 1개, SQL analytics endpoint 1개, Notebook 7개가 있습니다.

**Notebook이 없으면:** 관리자가 미리 넣지 않은 환경입니다. 관리자에게 받은 실습 파일 폴더(또는 이 저장소의 `notebooks` 폴더)의 `.ipynb` 7개를 **Import → Notebook → From this computer**로 가져온 뒤 아래 4단계에서 기본 Lakehouse를 연결합니다. Notebook 이름은 파일 이름 그대로 둡니다. `nb_apply_decision`이 `03_silver_conform`, `04_gold_model`을 이름으로 실행하기 때문입니다.

## 3. Lakehouse와 실습 파일 확인

1.  `lh_zeb`를 엽니다.
2.  왼쪽 **Explorer**에서 **Tables** 아래 스키마가 `dbo` 하나만 있는지 봅니다. **schema-enabled Lakehouse**이므로 `bronze`·`silver`·`gold`·`ops` 스키마는 Notebook이 만듭니다.
3.  **Files → workshop**을 누릅니다.

**예상 결과:** 가운데에 `sm_zeb.tmdl`, `zeb-theme.json` 두 파일이 보입니다. 08장에서 씁니다.

4.  두 파일을 PC로 내려받습니다. 파일 이름 오른쪽 **…**를 누르고 **Download / 다운로드**를 누릅니다. PC의 한 폴더(예: `Downloads\zeb`)에 원래 이름·확장자 그대로 둡니다.

**확인할 결과:** PC에 `sm_zeb.tmdl`, `zeb-theme.json`이 있습니다. 메모장으로 `sm_zeb.tmdl`을 열면 첫 줄이 `createOrReplace`입니다.

## 4. Notebook의 기본 Lakehouse 확인

Notebook은 테이블 이름을 `bronze.pub_zeb_cert`처럼 **스키마.테이블**로만 씁니다. 어느 Lakehouse에 쓰는지는 Notebook의 **기본 Lakehouse**가 정합니다.

1.  작업 영역으로 돌아가 `01_bronze_public_ingest`를 엽니다.
2.  왼쪽 **Explorer**의 **OneLake / Lakehouses** 아래에 `lh_zeb`가 있고 **기본(Default)** 표시가 있는지 확인합니다.
3.  없으면 **Add data items → From OneLake catalog**에서 **본인 작업 영역**의 **Lakehouse 아이콘** `lh_zeb`를 체크하고 **Add**를 누릅니다. 같은 이름의 SQL analytics endpoint를 고르지 않습니다. 기본 표시가 없으면 `lh_zeb`의 **…**에서 **Set as default lakehouse**를 누릅니다.
4.  나머지 Notebook 6개도 열어서 같은 방법으로 확인합니다.

**예상 결과:** Notebook 7개 모두 기본 Lakehouse가 본인 작업 영역의 `lh_zeb`입니다.

## 5. Notebook 실행 방법

다음 장부터 아래 방법으로 Notebook을 실행합니다.

- 위쪽 셀부터 **Shift+Enter**로 한 셀씩 실행하고, 각 셀 위 설명의 **예상 결과**와 비교합니다. 도구 모음의 **Run all**로 전체를 실행한 뒤 결과를 읽어도 됩니다.
- 첫 셀을 실행하면 Spark 세션이 시작됩니다. 보통 수십 초 걸리며, 용량이 바쁘면 더 걸립니다.
- `# 파라미터`가 적힌 셀은 **parameters 셀**입니다. 파이프라인·에이전트가 값을 바꿔 넘길 때 쓰는 셀이며, 실습에서는 기본값을 그대로 씁니다.
- 한 장을 마치면 도구 모음의 **Stop session / 세션 중지**로 Spark 세션을 멈춥니다. 다음 Notebook을 열면 새 세션이 시작됩니다.

## 이 장의 완료 기준

본인 작업 영역 `zeb-p001`이 Fabric 용량에 있고, `lh_zeb`와 Notebook 7개가 있으며, Notebook 7개의 기본 Lakehouse가 본인 `lh_zeb`입니다. PC에 `sm_zeb.tmdl`, `zeb-theme.json`을 내려받았습니다.

## Troubleshooting

- 작업 영역 목록에 `zeb-p001`이 없으면 로그인한 계정이 맞는지 확인하고 관리자에게 권한을 요청합니다.
- **Files → workshop**이 비어 있으면 관리자에게 파일 2개를 요청합니다. 이 저장소의 `fabric` 폴더에 같은 파일이 있습니다.
- **From this computer** Import가 막혀 있는 환경이면 관리자가 Notebook을 대신 넣습니다([관리자 준비 가이드](../admin/README.md)).

## 다음 단계

[02. Bronze ① 공공 인증 데이터](02-bronze-public.md)
