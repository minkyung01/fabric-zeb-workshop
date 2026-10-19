# 11. 승인과 반영

[목차](../README.md) \| 이전: [10. Foundry agent (선택)](10-foundry-agent.md) \| 다음: [12. 마무리](12-finish.md)

근거를 확인했으니 담당자로서 결정합니다. Teams에서 `OPT-D2`를 승인하면 Operations agent가 `nb_apply_decision`을 실행해 **조치를 기록하고, Silver·Gold를 다시 계산**합니다. 이 장의 목표는 **승인 한 번이 데이터 전체에 어떻게 반영되는지** 따라가 확인하는 것입니다.

| 순서 | 일어나는 일 | 확인할 곳 |
|---|---|---|
| 1 | 담당자가 Teams에서 **Proceed → Confirm** | Teams |
| 2 | `bronze.pms_action_log`에 `apply_options` 조치 1행, Eventhouse에 `approved` | Lakehouse, Eventhouse |
| 3 | `03_silver_conform`이 조치를 읽어 <b>설계안 V4(조치 반영안)</b>를 만들고 `현행`으로 바꿈 | Lakehouse |
| 4 | `04_gold_model`이 예상 등급·현장 상태를 다시 계산 | `ops.site_status` |
| 5 | D단지 위험이 해소되면 Eventhouse에 `resolved` | Eventhouse |
| 6 | 보고서·Data agent에서 바뀐 결과 확인, 에이전트 Stop | Power BI, Data agent, Operations agent |

**시작 전:** 09장에서 Teams 제안을 받고 **승인을 보류한 상태**여야 합니다. `oa_zeb`가 시작 상태이고, `nb_apply_decision`의 기본 Lakehouse가 본인 `lh_zeb`입니다.

## 1. Teams에서 승인

1.  Teams의 **Fabric operations agent** 채팅에서 09장의 제안을 엽니다.
2.  **Proceed**를 누릅니다.
3.  **Confirm details for ApplyZebOption**에서 값을 확인합니다.

    | 매개 변수 | 확인할 값 |
    |---|---|
    | `event_id` | `ZEB-HS-D-20260930` |
    | `option_id` | `OPT-D2` |

4.  값이 맞으면 **Confirm**을 누릅니다. 다르면 **Cancel**을 누르고 09장 6단계의 이벤트를 다시 확인합니다.

**예상 결과:** **Action submitted** 메시지가 옵니다. **접수 메시지가 완료를 뜻하지는 않습니다.** Notebook이 Silver·Gold를 다시 계산하는 데 약 5–8분 걸립니다.

## 2. 실행 완료 확인

1.  Fabric 왼쪽 **Monitor**에서 `nb_apply_decision`의 실행 기록을 엽니다.
2.  상태가 **Succeeded / 성공**이 될 때까지 기다립니다. 실행 중에는 `03_silver_conform`, `04_gold_model`이 차례로 실행됩니다.

**예상 결과:** `nb_apply_decision`이 **Succeeded**입니다. 실행 기록을 열면 마지막 셀에 다음과 비슷한 줄이 있습니다.

``` text
에코시티 D단지 현장: 현행 V4(조치 반영안) 자립률 41.4% · 1차에너지 72.5 → 예상 4등급, 상태 정상
ZEB-HS-D-20260930: ZebRiskEvent에 resolved 추가
```

## 3. Eventhouse 상태 이력 확인

`eh_zeb_queryset`에서 아래 쿼리를 실행합니다.

``` text
ZebRiskEvent
| project status_time, event_id, event_status, forecast_grade, selfsuff_pct, recommended_option_id
| order by status_time asc
```

**예상 결과:** 같은 `ZEB-HS-D-20260930`의 3행이 시간 순서로 있습니다.

| event_status | forecast_grade | selfsuff_pct | 뜻 |
|---|---|---|---|
| `open` | 5등급 | 38.2 | 09장에서 보낸 위험 |
| `approved` | 5등급 | 38.2 | 담당자 승인 직후(아직 재계산 전) |
| `resolved` | **4등급** | **41.4** | 재계산 후 위험 해소 |

Operations agent는 `event_status`가 `open`으로 바뀔 때만 알리므로, `approved`·`resolved` 행으로는 알림을 다시 보내지 않습니다.

## 4. Lakehouse 반영 확인

SQL analytics endpoint `lh_zeb`에서 **New SQL query**로 아래 쿼리를 실행합니다. 결과가 바로 보이지 않으면 1–2분 뒤 다시 실행합니다(메타데이터 동기화 지연).

``` sql
SELECT action_id, site_code, action_type, detail_json, approved_by, source_system
FROM bronze.pms_action_log;

SELECT version_code, version_name, version_date, selfsuff_pct, primary_energy_kwh_m2y, change_note, version_status
FROM gold.bim_design_version
WHERE bim_model_id = 'BIM-0397'
ORDER BY version_code;

SELECT site_name, current_version_code, selfsuff_pct, primary_energy_kwh_m2y,
       forecast_zeb_label, grade_basis, grade_risk, risk_level
FROM ops.site_status
WHERE site_code = 'HS-D';
```

**예상 결과:**

- **조치 기록 1행:** `ACT-ZEB-HS-D-20260930`, `HS-D`, `apply_options`, `{"option_ids": ["OPT-D2"], "event_id": "ZEB-HS-D-20260930"}`, 승인자 `<에이전트를 만든 계정> (Teams 승인)`, 출처 `Operations agent`
- **설계안 4행:** V1·V2·V3는 `이전`, 새 **V4 `조치 반영안`**은 자립률 `41.4`, 1차에너지 `72.5`, 변경 내용 `보완안 적용: 주차장 캐노피 태양광(+90kW)`, 상태 **`현행`**. 기존 V3는 지워지지 않고 `이전`으로 남습니다.
- **현장 상태:** 현행 `V4`, 예상 **4등급**, 등급 근거 `에너지자립률`, 등급 위험 `정상`, 상태 **`정상`**

설비 계획(`gold.pms_equipment_plan`)에도 `HS-D-OPT-D2`(주차장 캐노피 태양광, 2억 3천만 원, 설계안 V4)가 추가됩니다. 이 모든 변경은 **실습 데이터 안의 기록과 재계산**이며 실제 설계 변경·발주는 아닙니다.

## 5. 보고서와 Data agent로 다시 확인

1.  `rpt_zeb`를 엽니다. 숫자가 바뀌지 않았으면 브라우저를 새로 고칩니다. 그래도 같으면 `sm_zeb`의 **Model view**에서 **Refresh → Data**를 실행한 뒤 보고서를 다시 엽니다.

    **예상 결과:** `02 현장 컨트롤 타워`의 카드가 현장 수 `8`, 위험 현장 **`0`**, 주의 현장 `3`, 설치 지연 발주 `0`입니다. 표의 에코시티 D단지 행이 `V4`, `41.4`, `72.5`, `4등급`, **`정상`**입니다.

2.  `da_zeb`의 **Test data agent**에서 **Clear chat** 후 `에코시티 D단지의 현행 설계안과 예상 ZEB 등급은? 예비인증 등급을 지키나?`를 묻습니다.

    **예상 결과:** 현행 **V4(조치 반영안)**, 자립률 41.4%·1차에너지 72.5 → 4등급, 예비인증 4등급을 지킴. 07장 Q3을 다시 물으면 본인증 위험 현장이 **없다**고 답해야 합니다.

## 6. 감시 멈추기

`oa_zeb`로 돌아가 도구 모음의 **Stop**을 누릅니다. 에이전트는 멈추기 전까지 약 5분마다 조회하며 용량을 씁니다.

**예상 결과:** 도구 모음에 **Start**가 보입니다.

## 이 장의 완료 기준

- Teams에서 `OPT-D2`를 승인했고 `nb_apply_decision`이 **Succeeded**입니다.
- `ZebRiskEvent`에 `open` → `approved` → `resolved` 이력이 있습니다.
- `bronze.pms_action_log`에 조치 1행, `gold.bim_design_version`에 현행 **V4**, `ops.site_status`에서 D단지가 **4등급·정상**입니다.
- 보고서의 위험 현장이 `0`이고 Data agent가 V4 기준으로 답합니다.
- `oa_zeb`가 **Stop** 상태입니다.

여기에 남긴 것은 **담당자의 승인과 그에 따른 데이터 재계산**입니다. 실제 설계 변경·발주를 실행한 것은 아닙니다.

## Troubleshooting

- `Action submitted` 뒤 Monitor에 실행 기록이 없으면 2–3분 기다립니다. 계속 없으면 `ApplyZebOption`이 **Action connected**인지 09장 4단계를 확인합니다.
- **Failed**이면 Monitor에서 실패한 셀을 확인합니다.
  - `option_id=… 추천 보완안과 다릅니다`: Confirm 단계에서 값이 바뀐 경우입니다. 추천안과 다른 값은 기록하지 않습니다.
  - `상태 'resolved'에서는 승인을 반영할 수 없습니다`: 이미 반영된 이벤트입니다. 3–4단계로 결과만 확인합니다.
  - `03_silver_conform`·`04_gold_model`을 찾지 못하는 오류: Notebook 이름이 바뀌었는지 확인합니다. 두 Notebook은 같은 작업 영역에 원래 이름으로 있어야 합니다.
- 실패 후 다시 시도할 때는 Teams의 같은 제안을 다시 승인하거나, `nb_apply_decision`을 열어 기본 매개 변수로 **Run all**합니다. 조치 기록은 같은 이벤트에 대해 한 번만 추가되므로 중복되지 않습니다.
- 3단계에서 `approved`만 있고 `resolved`가 없으면 재계산 후에도 D단지가 위험인 경우입니다. 마지막 셀의 사유를 확인합니다.
- 보고서 값이 바뀌지 않으면 Semantic model의 **Refresh → Data**를 실행합니다. Direct Lake는 새로 고침으로 최신 Delta 버전을 다시 읽습니다.
- 실습을 처음부터 다시 하려면 `02_bronze_contoso_generate` → `03_silver_conform` → `04_gold_model` 순서로 실행합니다. 조치 기록이 지워지고 D단지가 다시 V3·위험 상태가 됩니다.

## 다음 단계

[12. 마무리](12-finish.md)
