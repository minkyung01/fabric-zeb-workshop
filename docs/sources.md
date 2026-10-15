# 출처와 공식 문서

## 증거 수준

- **실제 원본 읽기 관찰**: WS_ZEB item inventory, schema/table counts, bounded samples/SQL, 4 notebook definitions와 기존 Ontology의 키/관계, capacity 상태.
- **오프라인 재현**: 기존 Notebook02 deterministic synthetic fixture 기반 calculator, generated notebooks/data, 로컬 test/checker, 직접 만든 architecture 이미지.
- **공식 문서 지원**: 아래 기능 설명. 지원 문서가 해당 tenant/지역/권한에서의 실습 성공을 증명하지 않습니다.
- **실제 p01 리허설**: 공공 ZEB 9,760행과 계층별 notebook, Ontology·Direct Lake·Power BI/Copilot은 [식별자 없는 요약](../validation/rehearsal-summary.json)과 [상태 해설](../admin/validation.md)을 기준으로 합니다.
- **미완료**: p01 Teams 제안 관찰·사람 Proceed/Confirm·audit action, 선택 Foundry, 12명 리허설. 문서/그림의 경로는 이 미완료 단계를 성공으로 표시하지 않습니다.

## Microsoft Learn

- [Schema-enabled Lakehouses](https://learn.microsoft.com/en-us/fabric/data-engineering/lakehouse-schemas)
- [Fabric notebook](https://learn.microsoft.com/en-us/fabric/data-engineering/how-to-use-notebook)
- [Notebook source control/deployment](https://learn.microsoft.com/en-us/fabric/data-engineering/notebook-source-control-deployment)
- [Lakehouse Git/deployment limitations](https://learn.microsoft.com/en-us/fabric/data-engineering/lakehouse-git-deployment-pipelines)
- [OneLake shortcut security](https://learn.microsoft.com/en-us/fabric/onelake/onelake-shortcut-security)
- [Direct Lake overview](https://learn.microsoft.com/en-us/fabric/fundamentals/direct-lake-overview)
- [Power BI Copilot create reports](https://learn.microsoft.com/en-us/power-bi/create-reports/copilot-create-reports)
- [Power BI Copilot ask data questions](https://learn.microsoft.com/en-us/power-bi/create-reports/copilot-ask-data-question)
- [Copilot enable Fabric](https://learn.microsoft.com/en-us/fabric/fundamentals/copilot-enable-fabric)
- [Spark concurrency and queueing](https://learn.microsoft.com/en-us/fabric/data-engineering/spark-job-concurrency-and-queueing)
- [Ontology rules](https://learn.microsoft.com/en-us/fabric/iq/ontology/how-to-use-rules)
- [Ontology agent](https://learn.microsoft.com/en-us/fabric/iq/ontology/how-to-use-ontology-agent)
- [Ontology graph](https://learn.microsoft.com/en-us/fabric/iq/ontology/how-to-use-ontology-graph)
- [Operations agent](https://learn.microsoft.com/en-us/fabric/real-time-intelligence/operations-agent)
- [Operations agent actions](https://learn.microsoft.com/en-us/fabric/real-time-intelligence/operations-agent-actions)
- [Foundry Fabric IQ tool](https://learn.microsoft.com/en-us/azure/foundry/agents/how-to/tools/fabric-iq)

URL 경로/preview 문서는 변경될 수 있습니다. 아래 메달리온 설계 근거는 **2026-10-13 Microsoft Learn 본문을 실제 조회**했습니다. 나머지 기능별 URL과 현재 tenant/지역/권한 조건은 관리자 리허설 시 다시 확인합니다.

## 메달리온 설계 검증 2026-10-13

| 실제 조회한 공식 문서 | 확인한 근거 | 이 저장소에 반영한 설계 |
|---|---|---|
| [Implement Medallion Lakehouse Architecture in Fabric](https://learn.microsoft.com/en-us/fabric/onelake/onelake-medallion-lakehouse-architecture) | Bronze=raw, Silver=enriched, Gold=curated. 원본 보존과 단계적 품질 개선. 운영에서는 계층별 Lakehouse 및 별도 workspace 권고 | 세 계층을 Lakehouse 안의 스키마 흐름(Files → Bronze → Silver → Gold)으로 표시. 한 Lakehouse/schema 실습은 교육적 절충이며 운영 권고와 구별 |
| [Lakehouse schemas](https://learn.microsoft.com/en-us/fabric/data-engineering/lakehouse-schemas) | schema.table로 table 저장·그룹화. Notebook의 default Lakehouse가 schema-enabled이거나 default가 없어야 schema 사용 가능 | 참가자별 schema-enabled Lakehouse에 `bronze`·`silver`·`gold`; schema 이름 자체는 권한 격리 증명 아님 |
| [OneLake, the unified data lake](https://learn.microsoft.com/en-us/fabric/onelake/onelake-overview) | 통합 저장소의 동일 데이터를 여러 분석 엔진이 사용 | OneLake를 Gold 다음 단계가 아닌, Lakehouse와 전체 계층을 담는 저장 기반으로 표시 |
| [What is the SQL analytics endpoint for a lakehouse?](https://learn.microsoft.com/en-us/fabric/data-engineering/lakehouse-sql-analytics-endpoint) | Delta table에는 읽기 전용 T-SQL. 데이터 수정은 Spark. view/function/procedure 생성 가능하지만 Delta INSERT/UPDATE/DELETE 불가 | SQL은 읽기·독립 검산. Bronze/Silver/Gold 물리 table의 writer는 Spark |
| [Direct Lake overview](https://learn.microsoft.com/en-us/fabric/fundamentals/direct-lake-overview) | OneLake Delta table을 읽는 semantic model 저장 모드이며 Gold 분석 계층에 적합 | Gold → semantic model(Direct Lake) → Power BI; Silver에서 보고서로 바로 연결하지 않음 |
| [How to use notebooks](https://learn.microsoft.com/en-us/fabric/data-engineering/how-to-use-notebook) | Spark 기반 ingestion·preparation·transformation, Lakehouse 연결 | `01_bronze`·`02_silver`·`03_gold`를 각 계층의 실제 변환 책임자로 표시 |

위 기능 지원은 계층별 품질 계약을 대신하지 않습니다. [구현 대조 해설](../admin/medallion-architecture.md)은 실제 notebook/reference 코드와 16/17/15 table 범위를 기준으로 합니다. 공식 권고를 이유로 현재 없는 quarantine·append 배치·증분 pipeline·자동 동기화·물리 설비 검증을 구현된 기능처럼 표시하지 않습니다.

## 공개 source

- [ZEB 15085042](https://www.data.go.kr/data/15085042/fileData.do)
- [GSEED 15003214](https://www.data.go.kr/data/15003214/fileData.do)
- [BF 15014781](https://www.data.go.kr/data/15014781/fileData.do)
- [GreenTech 15054156](https://www.data.go.kr/data/15054156/fileData.do)
- [ZEB certification system](https://zeb.energy.or.kr/) — 기존 교육 threshold 출처 맥락, 현행 법적 적용 미검증.
- [ChipBalance teaching reference](https://github.com/SookBongnaver/MS_WS_ChipBalance) — 역할/업무 우선 학습, 독립 정답, manual Power BI→Copilot, 승인 전 근거 검토, 파일·notebook parity 검사 방식 참고. Databricks Shared clone/Unity Catalog/Serverless 및 영화 제조 데이터는 사용하지 않습니다.

본 저장소는 비공개 원본 envelope·토큰·원본 Ontology 정의를 배포하지 않습니다. 원본은 read-only 보존되었고 새 워크숍 p01의 실제 실행과 미완료 범위는 위 리허설 증거로 분리합니다. 이번 메달리온 설계 반영은 로컬 문서·그림·검사만 변경했으며 추가 cloud 실행은 하지 않았습니다.
