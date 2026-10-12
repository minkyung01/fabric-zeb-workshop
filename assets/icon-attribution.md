# 구성도 아이콘 출처

[전체 구성](../README.md#전체-구성)

이 구성도는 [MS_WS_ChipBalance](https://github.com/SookBongnaver/MS_WS_ChipBalance)의 구성도 표현 방식(업무 판단 단계, 공식 제품 아이콘, 제품 경계, 정제·근거·사람 승인 흐름)을 참고하여 **건설 ZEB 업무의 Fabric 전용 경로**로 새로 작성했습니다. Databricks·Genie·Work IQ 경로는 사용하지 않습니다.

아이콘은 각 제품을 설명하는 아키텍처 문서 용도로 공식 배포 원본을 그대로 사용합니다. 색상·비율·방향을 변경하지 않았으며, 아이콘·제품 상표의 권리는 Microsoft에 있습니다. 아래 공식 페이지의 사용 조건을 따릅니다.

| 파일 (`icons/`) | 공식 배포 원본 |
|---|---|
| `fabric.svg` | Fabric `fabric_48_color.svg` |
| `onelake.svg` | Fabric `one_lake_48_color.svg` |
| `lakehouse.svg` | Fabric `lakehouse_64_item.svg` |
| `notebook.svg` | Fabric `notebook_64_item.svg` |
| `semantic-model.svg` | Fabric `semantic_model_64_item.svg` |
| `power-bi.svg` | Fabric `power_bi_48_color.svg` |
| `eventhouse.svg` | Fabric `event_house_64_item.svg` |
| `operations-agent.svg` | Fabric `operations_agent_64_item.svg` |
| `ontology.svg` | Fabric `ontology_64_item.svg`, 공식 npm 배포본 8.2.0 |
| `foundry.svg` | Azure v24 `035746832-icon-service-AI-Foundry.svg` |
| `foundry-agent.svg` | Azure v24 `038470523-icon-service-Foundry-Agent-Service.svg` |
| `teams.svg` | Microsoft Fluent UI `teams_48x1.svg` |

- [Microsoft Fabric icons 및 사용 조건](https://learn.microsoft.com/en-us/fabric/fundamentals/icons) · [공식 Icons.zip v6.1.0](https://raw.githubusercontent.com/microsoft/fabric-samples/main/docs-samples/Icons.zip) · [공식 @fabric-msft/svg-icons 배포본](https://www.npmjs.com/package/@fabric-msft/svg-icons)
- [Microsoft Azure architecture icons 및 사용 조건](https://learn.microsoft.com/en-us/azure/architecture/icons/)
- [Microsoft Teams 공식 제품 SVG](https://res-1.cdn.office.net/files/fabric-cdn-prod_20230815.002/assets/brand-icons/product/svg/teams_48x1.svg)

Eventhouse·OneLake는 공식 zip에서, 나머지는 원본 출처를 기록한 MS_WS_ChipBalance의 `assets/icons/`에서 동일 bytes를 가져왔습니다.

## 편집·재생성

`tools/build_architecture.py`의 한 장면에서 SVG·Excalidraw·scene JSON을 함께 생성합니다. 공식 SVG 아이콘은 두 편집 형식에 data URL로 내장되어 외부 다운로드 없이 표시됩니다. `tools/render_architecture.ps1`은 별도의 도형을 다시 그리지 않고 **그 SVG 자체**를 Microsoft Edge의 격리된 로컬 세션으로 1900×1460 PNG에 렌더링합니다. 클라우드와 학습용 Fabric 브라우저에는 접근하지 않습니다.

Excalidraw는 <https://aka.ms/excalidraw>에서 편집할 수 있습니다. PNG·SVG·Excalidraw는 개념 구성도이며, 실제 실행 화면·성공 증거가 아닙니다. 실행 상태는 [실제 리허설 검증](../admin/validation.md)에 따로 기록합니다.
