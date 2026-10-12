-- Read-only SQL analytics endpoint; run ONLY against owned participant Lakehouse.
-- This independently computes ranks, rather than trusting the Gold grade column.
WITH current_design AS (
    SELECT x.site_code, d.version_id, d.selfsuff_pct, d.primary_energy_kwh_m2y,
           p.main_use, d.pv_kw
    FROM silver.mdm_site_xref x
    JOIN silver.erp_project p ON p.project_no=x.project_no
    JOIN silver.bim_design_version d ON d.bim_model_id=x.bim_model_id
    WHERE d.version_status=N'현행'
), ranks AS (
    SELECT d.site_code, MIN(CASE WHEN g.grade_code='+' THEN 0
                               ELSE CAST(g.grade_code AS int) END) AS grade_rank
    FROM current_design d
    JOIN silver.ref_zeb_grade_criteria g
      ON d.selfsuff_pct >= g.selfsuff_min_pct
      OR d.primary_energy_kwh_m2y < CASE WHEN d.main_use=N'공동주택'
               THEN g.primary_energy_limit_residential ELSE g.primary_energy_limit_nonresidential END
    GROUP BY d.site_code
)
SELECT d.site_code,d.version_id,d.selfsuff_pct,d.primary_energy_kwh_m2y,
       COALESCE(r.grade_rank,6) AS independently_computed_rank
FROM current_design d LEFT JOIN ranks r ON d.site_code=r.site_code
ORDER BY d.site_code;

-- Certificate identity must be kept separate from current design.
SELECT c.cert_no,c.cert_date,c.design_version_id AS submitted_version,
       submitted.selfsuff_pct AS submitted_ss,submitted.primary_energy_kwh_m2y AS submitted_pe,
       current_d.version_id AS current_version,current_d.selfsuff_pct AS current_ss,
       current_d.primary_energy_kwh_m2y AS current_pe
FROM silver.pms_certificate c
JOIN silver.bim_design_version submitted ON submitted.version_id=c.design_version_id
JOIN silver.mdm_site_xref x ON x.site_code=c.site_code
JOIN silver.bim_design_version current_d ON current_d.bim_model_id=x.bim_model_id AND current_d.version_status=N'현행'
WHERE c.site_code='HS-D' AND c.cert_type='ZEB';

SELECT COUNT_BIG(*) AS actual_rows FROM gold.site_status;
SELECT COUNT_BIG(*) AS option_set_rows FROM gold.option_eval;
SELECT TOP (5) option_set_id,selfsuff_pct,primary_energy_kwh_m2y,cost_krw,
       parallel_lead_days,energy_feasible,decision_feasible,block_reason
FROM gold.option_eval WHERE energy_feasible=1 ORDER BY cost_krw,option_set_id;

-- Independent HS-D additive subset enumeration from Silver, not Gold option_eval.
-- The six bit positions are a fixed explicit training option mapping.
WITH bits AS (
    SELECT * FROM (VALUES ('OPT-D1',1),('OPT-D2',2),('OPT-D3',4),
                          ('OPT-D4',8),('OPT-D5',16),('OPT-D6',32)) b(option_id,bit_value)
), nums AS (
    SELECT * FROM (VALUES(0),(1),(2),(3),(4),(5),(6),(7)) n(v)
), masks AS (
    SELECT a.v + 8*b.v AS mask FROM nums a CROSS JOIN nums b WHERE a.v+8*b.v>0
), base AS (
    SELECT CAST(d.selfsuff_pct AS decimal(12,4)) ss,
           CAST(d.primary_energy_kwh_m2y AS decimal(12,4)) pe
    FROM silver.bim_design_version d
    JOIN silver.mdm_site_xref x ON x.bim_model_id=d.bim_model_id
    WHERE x.site_code='HS-D' AND d.version_status=N'현행'
), combinations AS (
    SELECT m.mask,
        STRING_AGG(CAST(o.option_id AS varchar(max)),'+') WITHIN GROUP (ORDER BY o.option_id) option_set_id,
        b.ss+SUM(CAST(o.selfsuff_gain_pp AS decimal(12,4))) ss,
        b.pe+SUM(CAST(o.primary_energy_delta AS decimal(12,4))) pe,
        SUM(o.cost_krw) cost_krw,MAX(o.lead_time_days) parallel_lead_days
    FROM masks m
    JOIN bits bit ON (m.mask & bit.bit_value)>0
    JOIN silver.sim_improvement_option o ON o.option_id=bit.option_id AND o.site_code='HS-D'
    CROSS JOIN base b
    GROUP BY m.mask,b.ss,b.pe
)
SELECT TOP (5) *,CAST(0 AS bit) AS engineering_decision_feasible
FROM combinations WHERE ss>=40 OR pe<70 ORDER BY cost_krw,option_set_id;
