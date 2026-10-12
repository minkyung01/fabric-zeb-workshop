# 오프라인 배포 준비 계약

`prepare_distribution.py`는 **cloud provisioning/deploy/run 기능이 없습니다**.
approved target list를 검증하고 notebook metadata와 TARGET에 같은 실제 ID를 주입한 로컬 definition package만 작성합니다.

1. 별도 승인된 관리자가 각 workspace/Lakehouse를 만들고 membership·Lakehouse workspace 소속·schema 지원을 readback합니다.
2. 실제 ID와 evidence를 비추적 `config/targets.json`에 입력합니다. 같은 이름이나 임의 GUID는 증거가 아닙니다.
3. preview로 duplicate participant/workspace/Lakehouse, 원본 ID, null/placeholder, 미승인 binding 거부를 확인합니다.
4. `--prepare --approved-offline-bindings`로 `deployment/prepared/pNN`에 바인딩된 ipynb와 native Notebook definition envelope, manifest를 작성합니다.
5. 준비 package의 Notebook definition은 API 지원 형식의 `notebook-content.ipynb` InlineBase64입니다. API 제출은 이 도구가 수행하지 않습니다. target별 검토/별도 cloud approval 이후에만 승인된 관리자 방법으로 제출합니다.
6. Files는 manifest대로 **별도 공급**합니다. Git/배포가 Lakehouse Tables/Files를 복제하지 않습니다.
7. metadata readback 및 runtime preflight가 일치할 때만 학생 실행을 허용합니다. 05는 **직접 학생 실행이 아니라** 08에서 구성한 Teams-approved Operations Notebook action으로만 실행합니다. admin approval-binding/creator 설정은 실제 연결 readback 뒤 자기 TARGET에 저장하며 5개 action string parameters와 분리합니다.

item manifest의 Ontology/model/report/Eventhouse/Operations 이름은 **만들어야 할 대상 목록**입니다. 현재 배포된 item이나 완료된 provisioning payload가 아닙니다. 학습자가 Ontology를 직접 만들고 모델/보고서를 contract와 DAX로 수동 authoring합니다. preview/runtime 기능에는 live validation gate가 있습니다.

모든 템플릿은 dependency IDs 없이 저장됩니다. source 보호 ID는 runtime 거부 상수에만 존재하며 default binding이 아닙니다. protected source lakehouse로 향하는 notebook definition을 제공하지 않습니다.

12개 target를 제공하면 각각 **8개 Notebook**의 12개 격리 package를 만들 수 있으나 concurrency/runtime/capacity 적합성을 증명하지 않습니다. Files manifest에는 기본 synthetic뿐 아니라 **필수 public ZEB bytes+manifest**를 별도 공급 대상으로 명시합니다. 아직 미취득 source를 패키지에 있다고 표시하지 않습니다.
