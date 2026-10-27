-- Raw layer: data as loaded, no business logic.
CREATE SCHEMA IF NOT EXISTS raw;
CREATE SCHEMA IF NOT EXISTS staging;
CREATE SCHEMA IF NOT EXISTS marts;

-- Prescribing is the big table, so it is list-partitioned by month.
-- Partitions are created by src/ingest.py and reloaded with TRUNCATE, which makes loads idempotent.
CREATE TABLE IF NOT EXISTS raw.epd (
    year_month         integer NOT NULL,
    practice_code      text    NOT NULL,
    practice_name      text,
    postcode           text,
    icb_code           text,
    icb_name           text,
    region_name        text,
    bnf_code           text    NOT NULL,
    bnf_description    text,
    chemical_substance text,
    items              integer,
    quantity           numeric,
    nic                numeric,
    actual_cost        numeric
) PARTITION BY LIST (year_month);

CREATE TABLE IF NOT EXISTS raw.gp_lsoa (
    practice_code      text NOT NULL,
    lsoa_code          text NOT NULL,
    number_of_patients integer
);

CREATE TABLE IF NOT EXISTS raw.imd (
    lsoa_code  text PRIMARY KEY,
    imd_score  numeric,
    imd_decile integer
);

CREATE TABLE IF NOT EXISTS raw.qof_diabetes (
    practice_code text PRIMARY KEY,
    register      integer,
    list_size     integer
);

CREATE TABLE IF NOT EXISTS raw.ingest_log (
    loaded_at timestamptz DEFAULT now(),
    source    text,
    row_count bigint
);
