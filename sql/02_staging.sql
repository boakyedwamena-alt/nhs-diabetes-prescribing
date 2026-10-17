-- Staging layer: filter to diabetes drugs, classify, and record what was excluded.
DROP TABLE IF EXISTS staging.dq_summary, staging.stg_epd, staging.dim_drug,
                     staging.drug_class_map, staging.practice_imd CASCADE;

-- Keyword -> class. Lowest priority number wins, so combination products
-- (e.g. dapagliflozin/metformin) go to the more specific class.
CREATE TABLE staging.drug_class_map (
    keyword    text PRIMARY KEY,
    drug_class text    NOT NULL,
    is_newer   boolean NOT NULL,
    priority   integer NOT NULL
);
INSERT INTO staging.drug_class_map VALUES
 ('liraglutide','GLP-1 / GIP agonist',true,1),('semaglutide','GLP-1 / GIP agonist',true,1),
 ('dulaglutide','GLP-1 / GIP agonist',true,1),('exenatide','GLP-1 / GIP agonist',true,1),
 ('lixisenatide','GLP-1 / GIP agonist',true,1),('tirzepatide','GLP-1 / GIP agonist',true,1),
 ('dapagliflozin','SGLT2 inhibitor',true,2),('empagliflozin','SGLT2 inhibitor',true,2),
 ('canagliflozin','SGLT2 inhibitor',true,2),('ertugliflozin','SGLT2 inhibitor',true,2),
 ('sitagliptin','DPP-4 inhibitor',false,3),('linagliptin','DPP-4 inhibitor',false,3),
 ('saxagliptin','DPP-4 inhibitor',false,3),('alogliptin','DPP-4 inhibitor',false,3),
 ('vildagliptin','DPP-4 inhibitor',false,3),
 ('insulin','Insulin',false,4),
 ('gliclazide','Sulfonylurea',false,5),('glimepiride','Sulfonylurea',false,5),
 ('glipizide','Sulfonylurea',false,5),('glibenclamide','Sulfonylurea',false,5),
 ('tolbutamide','Sulfonylurea',false,5),
 ('pioglitazone','Pioglitazone',false,6),
 ('acarbose','Other oral / injectable',false,7),('nateglinide','Other oral / injectable',false,7),
 ('repaglinide','Other oral / injectable',false,7),('pramlintide','Other oral / injectable',false,7),
 ('ozempic','GLP-1 / GIP agonist',true,1),('rybelsus','GLP-1 / GIP agonist',true,1),
 ('trulicity','GLP-1 / GIP agonist',true,1),('victoza','GLP-1 / GIP agonist',true,1),
 ('byetta','GLP-1 / GIP agonist',true,1),('bydureon','GLP-1 / GIP agonist',true,1),
 ('lyxumia','GLP-1 / GIP agonist',true,1),('mounjaro','GLP-1 / GIP agonist',true,1),
 ('xultophy','GLP-1 / GIP agonist',true,1),('suliqua','GLP-1 / GIP agonist',true,1),
 ('forxiga','SGLT2 inhibitor',true,2),('jardiance','SGLT2 inhibitor',true,2),
 ('invokana','SGLT2 inhibitor',true,2),('steglatro','SGLT2 inhibitor',true,2),
 ('xigduo','SGLT2 inhibitor',true,2),('synjardy','SGLT2 inhibitor',true,2),
 ('vokanamet','SGLT2 inhibitor',true,2),('segluromet','SGLT2 inhibitor',true,2),
 ('qtern','SGLT2 inhibitor',true,2),('glyxambi','SGLT2 inhibitor',true,2),
 ('steglujan','SGLT2 inhibitor',true,2),
 ('januvia','DPP-4 inhibitor',false,3),('trajenta','DPP-4 inhibitor',false,3),
 ('onglyza','DPP-4 inhibitor',false,3),('vipidia','DPP-4 inhibitor',false,3),
 ('galvus','DPP-4 inhibitor',false,3),('janumet','DPP-4 inhibitor',false,3),
 ('jentadueto','DPP-4 inhibitor',false,3),('eucreas','DPP-4 inhibitor',false,3),
 ('komboglyze','DPP-4 inhibitor',false,3),('incresync','DPP-4 inhibitor',false,3),
 ('metformin','Metformin',false,8);

-- Only insulins (060101) and antidiabetic drugs (060102). Excludes hypoglycaemia
-- treatments, diagnostic and monitoring items that also sit in BNF section 6.1.
CREATE TABLE staging.stg_epd AS
SELECT
    to_date(year_month::text || '01', 'YYYYMMDD') AS month_start,
    btrim(practice_code)      AS practice_code,
    btrim(practice_name)      AS practice_name,
    btrim(postcode)           AS postcode,
    btrim(icb_code)           AS icb_code,
    btrim(icb_name)           AS icb_name,
    btrim(region_name)        AS region_name,
    bnf_code,
    btrim(bnf_description)    AS bnf_description,
    btrim(chemical_substance) AS chemical_substance,
    items, quantity, nic, actual_cost
FROM raw.epd
WHERE (bnf_code LIKE '060101%' OR bnf_code LIKE '060102%')
  AND items > 0;

CREATE INDEX ON staging.stg_epd (practice_code, month_start);

-- In the SNOMED EPD the chemical-substance column holds a BNF CODE (e.g. 0601022B0), not a name, so drugs
-- are identified from the BNF section (first 7 characters of the code) and, within 6.1.2.3 "other
-- antidiabetic drugs", from the presentation names of that chemical.
--   060101x  insulins        0601021  sulfonylureas        0601022  biguanides (metformin)
CREATE TABLE staging.dim_drug AS
WITH chem AS (
    SELECT chemical_substance,
           MIN(LEFT(bnf_code, 7)) AS bnf_section,
           lower(string_agg(DISTINCT bnf_description, ' | ')) AS presentation_names
    FROM staging.stg_epd
    GROUP BY chemical_substance
)
SELECT c.chemical_substance, c.bnf_section,
       COALESCE(CASE WHEN c.bnf_section LIKE '060101%' THEN 'Insulin'
                     WHEN c.bnf_section = '0601021'    THEN 'Sulfonylurea'
                     WHEN c.bnf_section = '0601022'    THEN 'Metformin' END,
                m.drug_class, 'Unclassified')                              AS drug_class,
       COALESCE(m.is_newer AND c.bnf_section = '0601023', false)           AS is_newer_class,
       LEFT(c.presentation_names, 120)                                     AS example_names
FROM chem c
LEFT JOIN LATERAL (
    SELECT drug_class, is_newer FROM staging.drug_class_map k
    WHERE c.presentation_names LIKE '%' || k.keyword || '%'
    ORDER BY k.priority LIMIT 1
) m ON true;

-- Patient-weighted mean IMD 2019 score across the LSOAs a practice's patients live in.
CREATE TABLE staging.practice_imd AS
SELECT g.practice_code,
       SUM(g.number_of_patients) AS list_size,
       SUM(g.number_of_patients * i.imd_score)
         / NULLIF(SUM(g.number_of_patients) FILTER (WHERE i.imd_score IS NOT NULL), 0) AS imd_score,
       (SUM(g.number_of_patients) FILTER (WHERE i.imd_score IS NOT NULL))::numeric
         / NULLIF(SUM(g.number_of_patients), 0) AS imd_coverage
FROM raw.gp_lsoa g
LEFT JOIN raw.imd i USING (lsoa_code)
GROUP BY g.practice_code;

CREATE TABLE staging.dq_summary AS
SELECT 'epd_rows_loaded' AS check_name, COUNT(*)::numeric AS value FROM raw.epd
UNION ALL SELECT 'epd_rows_diabetes_kept', COUNT(*) FROM staging.stg_epd
UNION ALL SELECT 'epd_rows_excluded_non_diabetes_or_zero_items',
       (SELECT COUNT(*) FROM raw.epd) - (SELECT COUNT(*) FROM staging.stg_epd)
UNION ALL SELECT 'unclassified_substances', COUNT(*) FROM staging.dim_drug WHERE drug_class = 'Unclassified'
UNION ALL SELECT 'unclassified_items_share_pct',
       ROUND(100.0 * SUM(s.items) FILTER (WHERE d.drug_class = 'Unclassified') / SUM(s.items), 3)
       FROM staging.stg_epd s JOIN staging.dim_drug d USING (chemical_substance)
UNION ALL SELECT 'practices_in_epd', COUNT(DISTINCT practice_code) FROM staging.stg_epd
UNION ALL SELECT 'practices_without_lsoa_denominator',
       COUNT(DISTINCT practice_code) FROM staging.stg_epd
       WHERE practice_code NOT IN (SELECT practice_code FROM staging.practice_imd)
UNION ALL SELECT 'practices_without_qof_register',
       COUNT(DISTINCT practice_code) FROM staging.stg_epd
       WHERE practice_code NOT IN (SELECT practice_code FROM raw.qof_diabetes);
