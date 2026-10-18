# %% [markdown]
# # 05. 질문 8개의 정답 계산
#
# 07장에서 Data agent에게 물어볼 업무 질문 8개의 **정답을 Gold 데이터로 직접 계산**합니다.
# 에이전트의 답이 그럴듯해 보여도 이 Notebook의 값과 다르면 정답으로 보지 않습니다.
#
# | 번호 | 유형 | 질문 |
# |---|---|---|
# | Q1 | 집계 | 제로에너지건축물(ZEB) 인증이 가장 많은 시도 3곳과 건수를 알려줘. |
# | Q2 | 규칙 | 리버뷰 B단지는 에너지자립률이 39%입니다. 지금 설계로 ZEB 4등급을 받을 수 있나요? |
# | Q3 | 규칙 | 예비인증을 받은 현장 중에서 지금 설계대로 가면 본인증 때 문제가 될 현장은 어디야? |
# | Q4 | 용어 | 제로에너지건축물(ZEB) 인증 중에서 준공 후 인증을 받은 공동주택은 몇 건이야? |
# | Q5 | 관계 | 지열 설비 업체 Northwind가 아직 납품하지 않은 주문을 전부 21일씩 늦게 납품하면, 어느 현장의 인증 일정이 어떻게 달라져? |
# | Q6 | 공공×현장 | 경기 지역 공동주택 중 ZEB 4등급 이상 사례는 몇 건이고, 평균 에너지자립률은 D단지 현행 설계와 비교해 얼마나 차이 나? |
# | Q7 | What-if | Northwind의 납품이 21일 늦어질 때, 에코시티 D단지의 지열 히트펌프를 다른 업체로 바꾸면 인증 일정을 지킬 수 있어? |
# | Q8 | What-if | 에코시티 D단지가 VE 설계는 그대로 두고 보완안을 하나만 추가해서 예비인증 등급을 지키려면, 가장 싼 보완안은 뭐고 비용은 얼마야? |
#
# 이 Notebook은 데이터를 **읽기만 하고**, 테이블을 만들거나 바꾸지 않습니다. 전체 실행에 약 1분 걸립니다.

# %% [parameters]
as_of_date = "2026-09-30"

# %% [markdown]
# ## 0. 준비 — 등급 판정 함수
#
# ZEB 예상 등급은 **두 기준 중 더 좋은 등급**입니다.
#
# 1. 자립률 등급: `에너지자립률 >= 자립률 하한`을 만족하는 가장 좋은 등급
# 2. 1차에너지 등급: `1차에너지소요량 < 기준값`을 만족하는 가장 좋은 등급(주거용과 주거용 이외의 기준값이 다름)
# 3. 최종 등급: 1과 2 중 더 좋은 등급. 등급 순서는 `+`(ZEB+) → 1 → 2 → 3 → 4 → 5이며, 숫자가 작을수록 좋은 등급입니다.
#
# **예상 결과:** 등급 기준 6행이 출력됩니다. 4등급은 자립률 하한 40%, 주거용 1차에너지 기준 70입니다.

# %%
from datetime import date, timedelta
from pyspark.sql import functions as F

AS_OF = date.fromisoformat(as_of_date)
G = lambda t: spark.table(f"gold.{t}")
O = lambda t: spark.table(f"ops.{t}")

criteria = [r.asDict() for r in G("ref_zeb_grade_criteria").collect()]
RANK = {"+": 0, "1": 1, "2": 2, "3": 3, "4": 4, "5": 5}
LABEL = {0: "ZEB+", 1: "1등급", 2: "2등급", 3: "3등급", 4: "4등급", 5: "5등급", 6: "인증 기준 미달"}


def zeb_rank(selfsuff_pct, primary_energy, residential):
    limit = "primary_energy_limit_residential" if residential else "primary_energy_limit_nonresidential"
    by_ss = min([RANK[c["grade_code"]] for c in criteria if selfsuff_pct >= c["selfsuff_min_pct"]], default=6)
    by_pe = min([RANK[c["grade_code"]] for c in criteria if primary_energy < c[limit]], default=6)
    return min(by_ss, by_pe), by_ss, by_pe


answers = []
for c in sorted(criteria, key=lambda c: RANK[c["grade_code"]]):
    print(f"{c['grade_name']:<5} 자립률 ≥ {c['selfsuff_min_pct']:>5}%  1차에너지 < {c['primary_energy_limit_residential']:>5}(주거) / {c['primary_energy_limit_nonresidential']:>5}(주거 이외)")

# %% [markdown]
# ## Q1. ZEB 인증이 가장 많은 시도 3곳
#
# 공공 ZEB 인증(`gold.pub_zeb_certification`)을 시도별로 셉니다. 시도는 Silver에서 표기를 맞춘 값입니다.
#
# **예상 결과:** 3행. 실습 기준 파일(2025-12-31 기준)에서는 **경기 1,897건 → 경남 870건 → 경북 828건**입니다.

# %%
q1 = G("pub_zeb_certification").groupBy("sido").count().orderBy(F.desc("count")).limit(3)
display(q1)
answers.append(("Q1", " → ".join(f"{r.sido} {r['count']:,}건" for r in q1.collect())))

# %% [markdown]
# ## Q2. 리버뷰 B단지는 4등급을 받을 수 있는가
#
# 현재 설계안의 자립률과 1차에너지소요량으로 두 기준의 등급을 각각 구합니다. 공동주택이므로 주거용 기준값을 씁니다.
#
# **예상 결과:** **받을 수 있다.** 자립률 39% → 자립률 기준 5등급, 1차에너지 65 < 70 → 1차에너지 기준 4등급 → 최종 **4등급**. BEMS도 계획되어 있습니다.

# %%
s = O("site_status").where("site_code = 'IC-B'").first()
rank, by_ss, by_pe = zeb_rank(s.selfsuff_pct, s.primary_energy_kwh_m2y, s.use_family == "주거용")
print(f"{s.site_name}: 현행 {s.current_version_code} 자립률 {s.selfsuff_pct}% · 1차에너지 {s.primary_energy_kwh_m2y} · {s.use_family}")
print(f"  자립률 기준 {LABEL[by_ss]}, 1차에너지 기준 {LABEL[by_pe]} → 예상 {LABEL[rank]} (ops.site_status: {s.forecast_zeb_label}), BEMS 계획 {s.has_bems}")
answers.append(("Q2", f"{'받을 수 있다' if rank <= 4 and s.has_bems else '받을 수 없다'} — 자립률 기준 {LABEL[by_ss]}, 1차에너지 기준 {LABEL[by_pe]} → {LABEL[rank]}"))

# %% [markdown]
# ## Q3. 본인증 때 문제가 될 현장
#
# 예비인증을 받은 현장은 사용승인 전에 **예비인증 등급 이상**의 본인증을 받아야 합니다. 현재 설계안의 예상 등급이 예비인증 등급보다 낮은 현장을 찾습니다.
#
# **예상 결과:** 1행. **에코시티 D단지 현장(HS-D)** — 예비인증 4등급, 현행 VE 반영안(V3) 예상 5등급. 리버뷰 B단지는 1차에너지 기준으로 4등급을 유지하므로 해당하지 않습니다.

# %%
q3 = (O("site_status").where("prelim_zeb_grade IS NOT NULL AND grade_risk = '예비 등급 미달'")
      .select("site_code", "site_name", "current_version_code", "selfsuff_pct", "primary_energy_kwh_m2y", "prelim_zeb_grade", "forecast_zeb_label"))
display(q3)
answers.append(("Q3", ", ".join(f"{r.site_name}({r.site_code}) 예비 {r.prelim_zeb_grade}등급 → 예상 {r.forecast_zeb_label}" for r in q3.collect())))

# %% [markdown]
# ## Q4. 준공 후 인증을 받은 공동주택
#
# 업무에서 **준공 후 인증은 본인증**, 준공 전 인증은 예비인증을 뜻합니다. 용도는 Silver에서 맞춘 `use_group = 공동주택`으로 거릅니다.
#
# **예상 결과:** 실습 기준 파일에서 **30건**입니다.

# %%
q4 = G("pub_zeb_certification").where("cert_stage = '본인증' AND use_group = '공동주택'").count()
print(f"본인증 공동주택: {q4:,}건")
answers.append(("Q4", f"{q4:,}건"))

# %% [markdown]
# ## Q5. Northwind 지열 납품이 21일씩 늦어지면
#
# 아직 입고되지 않은 Northwind(`V-30452`) 발주의 예상 입고일에 21일을 더하고, 그 현장의 **설비 설치 완료 계획일**과 비교합니다.
# 계획일을 넘긴 일수만큼 설치 완료 → 본인증 신청 → 본인증 취득 → 사용승인이 모두 밀립니다. 넘기지 않으면 남은 일수만큼 여유가 있습니다.
#
# **예상 결과:** 2행. **에코시티 D단지만 3일 지연**(새 입고일 2026-12-03 > 설치 완료 계획일 2026-11-30 → 이후 일정 모두 +3일).
# 에코시티 A단지는 여유가 52일 남아 영향이 없습니다.

# %%
delay = 21
q5 = (O("po_status").where("vendor_code = 'V-30452' AND NOT is_delivered")
      .withColumn("new_expected_date", F.date_add("expected_date", delay))
      .withColumn("over_days", F.datediff("new_expected_date", "install_deadline"))
      .select("site_code", "po_no", "expected_date", "new_expected_date", "install_deadline", "over_days")
      .orderBy("site_code"))
display(q5)
answers.append(("Q5", ", ".join(f"{r.site_code} {'+' + str(r.over_days) + '일 지연' if r.over_days > 0 else '영향 없음(여유 ' + str(-r.over_days) + '일)'}"
                                for r in q5.collect())))

# %% [markdown]
# ## Q6. 경기 공동주택 4등급 이상 사례와 D단지 비교
#
# '4등급 이상'은 4등급과 **그보다 좋은 등급**(+, 1, 2, 3, 4)입니다. 숫자가 4 이상이라는 뜻이 아닙니다.
#
# **예상 결과:** 실습 기준 파일에서 **9건, 평균 자립률 52.2%**. D단지 현행 설계 38.2%는 **14.0%p 낮습니다.**

# %%
q6 = (G("pub_zeb_certification").where("sido = '경기' AND use_group = '공동주택' AND grade_code IN ('+','1','2','3','4')")
      .agg(F.count("*").alias("cases"), F.round(F.avg("selfsuff_pct"), 1).alias("avg_selfsuff_pct")).first())
hsd = O("site_status").where("site_code = 'HS-D'").first()
print(f"경기 공동주택 4등급 이상: {q6.cases}건, 평균 자립률 {q6.avg_selfsuff_pct}%")
print(f"D단지 현행 {hsd.current_version_code}: {hsd.selfsuff_pct}% → 차이 {q6.avg_selfsuff_pct - hsd.selfsuff_pct:.1f}%p")
answers.append(("Q6", f"{q6.cases}건, 평균 {q6.avg_selfsuff_pct}% — D단지 {hsd.selfsuff_pct}%보다 {q6.avg_selfsuff_pct - hsd.selfsuff_pct:.1f}%p 높음"))

# %% [markdown]
# ## Q7. D단지 지열 히트펌프 공급사를 바꾸면
#
# 대체 공급이 가능한(`is_alternative_pool = true`) 지열(GEO) 공급사를 찾고, **기준일에 새로 발주**하면 표준 납기만큼 지나서 입고된다고 보고 계산합니다.
#
# **예상 결과:** **지킬 수 있음.** Alpine 지열(`V-30977`, 표준 납기 55일) → 2026-11-24 입고, 설치 완료 계획일 2026-11-30보다 6일 여유.

# %%
deadline = O("po_status").where("wbs_element = 'HS-D-GEO'").first().install_deadline
q7 = (G("scm_vendor").where("category_code = 'GEO' AND is_alternative_pool")
      .withColumn("new_expected_date", F.date_add(F.lit(AS_OF), F.col("standard_lead_time_days")))
      .withColumn("install_deadline", F.lit(deadline))
      .withColumn("slack_days", F.datediff("install_deadline", "new_expected_date"))
      .select("vendor_code", "vendor_name", "standard_lead_time_days", "new_expected_date", "install_deadline", "slack_days"))
display(q7)
answers.append(("Q7", ", ".join(f"{r.vendor_name} {r.new_expected_date} 입고 → {'지킬 수 있음(여유 ' + str(r.slack_days) + '일)' if r.slack_days >= 0 else '못 지킴'}"
                                for r in q7.collect())))

# %% [markdown]
# ## Q8. D단지가 보완안 하나로 예비인증 등급을 지키는 가장 싼 방법
#
# D단지 보완안 6개를 **하나씩** 현재 설계안(V3)에 더해 예상 등급을 다시 계산하고, 예비인증 4등급 이상이 되는 안 중 비용이 가장 낮은 안을 고릅니다.
# 준비 기간(`lead_time_days`)이 설비 설치 완료 계획일 전에 끝나는지도 함께 봅니다.
#
# **예상 결과:** 6행 중 4등급이 되는 안은 3개(D1·D2·D4)이고, 그중 가장 싼 안은 **OPT-D2 주차장 캐노피 태양광(2억 3천만 원)**입니다.
# 적용하면 자립률이 41.4%(40% 이상)가 되어 4등급을 유지합니다. 더 싼 D6(5천만 원)·D5(6천만 원)는 하나만 적용하면 5등급이라 해당하지 않습니다.
# 09장에서 Operations agent가 추천하는 보완안도 같은 기준으로 계산합니다.

# %%
rows = []
for o in G("sim_improvement_option").where("site_code = 'HS-D'").orderBy("cost_krw").collect():
    ss = round(hsd.selfsuff_pct + o.selfsuff_gain_pp, 1)
    pe = round(hsd.primary_energy_kwh_m2y + o.primary_energy_delta, 1)
    rank, _, _ = zeb_rank(ss, pe, hsd.use_family == "주거용")
    ready = AS_OF + timedelta(days=o.lead_time_days)
    rows.append((o.option_id, o.option_name, o.cost_krw, ss, pe, LABEL[rank], rank <= int(hsd.prelim_zeb_grade), ready, ready <= deadline))
q8 = spark.createDataFrame(rows, "option_id string, option_name string, cost_krw long, selfsuff_pct double, primary_energy double, "
                                 "expected_grade string, keeps_prelim_grade boolean, ready_date date, ready_before_install boolean")
display(q8)
best = q8.where("keeps_prelim_grade AND ready_before_install").orderBy("cost_krw").first()
answers.append(("Q8", f"{best.option_id} {best.option_name}, {best.cost_krw:,}원 → 자립률 {best.selfsuff_pct}% {best.expected_grade}"))

# %% [markdown]
# ## 정답 요약
#
# 07장에서 Data agent의 답을 이 표와 비교합니다. 표현은 달라도 되지만 **대상·수치·결론**이 같아야 정답으로 봅니다.

# %%
display(spark.createDataFrame(answers, "question string, answer string"))
