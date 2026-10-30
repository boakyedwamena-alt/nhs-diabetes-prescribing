-- Marts layer: analysis-ready tables, also the tables Power BI reads.
-- min_list and min_register are bound as named parameters by src/build_marts.py. Avoid the percent sign in this file.
DROP SCHEMA IF EXISTS marts CASCADE;
CREATE SCHEMA marts;

CREATE TABLE marts.dim_drug AS SELECT * FROM staging.dim_drug;

CREATE TABLE marts.fact_prescribing_month AS
SELECT s.practice_code, s.month_start, d.drug_class, d.is_newer_class,
       SUM(s.items) AS items, SUM(s.quantity) AS quantity, SUM(s.nic) AS nic
FROM staging.stg_epd s
JOIN staging.dim_drug d USING (chemical_substance)
GROUP BY 1, 2, 3, 4;
ALTER TABLE marts.fact_prescribing_month
    ADD PRIMARY KEY (practice_code, month_start, drug_class);

-- Practices come and go (mergers, closures), so attributes come from the latest month seen.
-- Practices without denominators are kept but excluded from analysis via include_in_analysis.
CREATE TABLE marts.dim_practice AS
WITH latest AS (
    SELECT DISTINCT ON (practice_code)
           practice_code, practice_name, postcode, icb_code, icb_name, region_name
    FROM staging.stg_epd
    ORDER BY practice_code, month_start DESC
),
base AS (
    SELECT l.*, pi.list_size, pi.imd_score, pi.imd_coverage,
           q.register AS diabetes_register,
           100.0 * q.register / NULLIF(COALESCE(q.list_size, pi.list_size), 0) AS diabetes_prevalence_pct
    FROM latest l
    LEFT JOIN staging.practice_imd pi USING (practice_code)
    LEFT JOIN raw.qof_diabetes q USING (practice_code)
),
flagged AS (
    SELECT base.*,
           COALESCE(list_size >= %(min_list)s AND diabetes_register >= %(min_register)s
            AND imd_score IS NOT NULL AND diabetes_prevalence_pct IS NOT NULL, false) AS include_in_analysis
    FROM base
)
SELECT f.*,
       CASE WHEN include_in_analysis
            THEN NTILE(5) OVER (PARTITION BY include_in_analysis ORDER BY imd_score DESC) END
         AS imd_quintile   -- 1 = most deprived fifth of practices, 5 = least deprived
FROM flagged f;
ALTER TABLE marts.dim_practice ADD PRIMARY KEY (practice_code);

CREATE VIEW marts.v_window AS
SELECT MAX(month_start) AS end_month,
       (MAX(month_start) - INTERVAL '11 months')::date AS start_month
FROM marts.fact_prescribing_month;

-- One row per practice over the latest 12 months in the data.
CREATE TABLE marts.mart_practice_window AS
WITH agg AS (
    SELECT f.practice_code,
           SUM(items)                                          AS total_items,
           SUM(nic)                                            AS total_nic,
           SUM(items) FILTER (WHERE drug_class <> 'Insulin')   AS non_insulin_items,
           SUM(items) FILTER (WHERE is_newer_class)            AS newer_items,
           SUM(items) FILTER (WHERE drug_class = 'Metformin')  AS metformin_items,
           SUM(items) FILTER (WHERE drug_class = 'Insulin')    AS insulin_items
    FROM marts.fact_prescribing_month f, marts.v_window w
    WHERE f.month_start BETWEEN w.start_month AND w.end_month
    GROUP BY f.practice_code
)
SELECT p.practice_code, p.practice_name, p.postcode, p.icb_code, p.icb_name, p.region_name,
       p.list_size, p.diabetes_register, p.diabetes_prevalence_pct,
       p.imd_score, p.imd_quintile, p.include_in_analysis,
       a.total_items, a.total_nic,
       COALESCE(a.non_insulin_items, 0) AS non_insulin_items,
       COALESCE(a.newer_items, 0)       AS newer_items,
       COALESCE(a.metformin_items, 0)   AS metformin_items,
       COALESCE(a.insulin_items, 0)     AS insulin_items,
       a.newer_items::numeric / NULLIF(a.non_insulin_items, 0)       AS newer_share,
       a.total_items * 1000.0 / NULLIF(p.list_size, 0)               AS items_per_1000_patients,
       a.total_items::numeric / NULLIF(p.diabetes_register, 0)       AS items_per_register_patient,
       a.total_nic / NULLIF(p.diabetes_register, 0)                  AS nic_per_register_patient
FROM marts.dim_practice p
JOIN agg a USING (practice_code);
ALTER TABLE marts.mart_practice_window ADD PRIMARY KEY (practice_code);

-- Monthly class mix by deprivation quintile (included practices only).
CREATE TABLE marts.mart_class_trend AS
WITH pop AS (
    SELECT imd_quintile, SUM(list_size) AS patients
    FROM marts.dim_practice WHERE include_in_analysis GROUP BY imd_quintile
)
SELECT f.month_start, p.imd_quintile, f.drug_class, f.is_newer_class,
       SUM(f.items) AS items,
       SUM(f.items) * 1000.0 / MAX(pop.patients) AS items_per_1000_patients
FROM marts.fact_prescribing_month f
JOIN marts.dim_practice p USING (practice_code)
JOIN pop ON pop.imd_quintile = p.imd_quintile
WHERE p.include_in_analysis
GROUP BY f.month_start, p.imd_quintile, f.drug_class, f.is_newer_class;

CREATE TABLE marts.mart_icb_summary AS
SELECT icb_code, icb_name, region_name,
       COUNT(*)                         AS practices,
       SUM(list_size)                   AS patients,
       SUM(total_items) * 1000.0 / SUM(list_size)                    AS items_per_1000_patients,
       SUM(newer_items)::numeric / NULLIF(SUM(non_insulin_items), 0) AS newer_share,
       SUM(imd_score * list_size) / SUM(list_size)                   AS mean_imd_score,
       SUM(diabetes_register) * 100.0 / SUM(list_size)               AS crude_prevalence_pct
FROM marts.mart_practice_window
WHERE include_in_analysis
GROUP BY icb_code, icb_name, region_name;
