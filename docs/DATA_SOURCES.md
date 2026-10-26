# Data sources and how to place the files

All four are free and open (Open Government Licence). Links were checked on 17 October 2026.

## Recommended window (chosen so the sources line up)
* **Prescribing:** April 2023 to March 2024 (12 months)
* **QOF:** 2023-24, which covers the same April 2023 to March 2024 year
* **GP patients by LSOA:** January 2024 snapshot
* **Deprivation:** English Indices of Deprivation 2019

Why this window: from July 2024 NHS England's GP LSOA files switched to 2021 LSOA codes, but IMD 2019
uses 2011 LSOA codes. The January 2024 extract is the last era that matches IMD 2019 cleanly, and
`python -m src.checks` (or `make checks`) fails if fewer than 95% of patients match.

## 1. Prescribing: NHSBSA English Prescribing Dataset (EPD) with SNOMED code
* Dataset page: https://opendata.nhsbsa.net/dataset/english-prescribing-dataset-epd-with-snomed-code
* Files are named `epd_snomed_YYYYMM.csv`, about 17 million rows per month. **Do not download them all by hand.**
* Use the script, which streams each month and keeps only diabetes rows (BNF 0601):
  `python -m src.download_epd` (writes `data/raw/epd/epd_YYYYMM.csv`, skips months already present)
* The older "EPD" without SNOMED codes is **retired** (covers Jan 2014 to Jun 2025), so use the SNOMED version.
* Direct links for the window (pattern `.../906115a6-4155-44be-8b81-f8e83cebfb84/resource/<id>/download/epd_snomed_YYYYMM.csv`):
  the ids are in `RESOURCES` inside `src/download_epd.py`.
* **Reuse conditions (from the dataset page, checked 22 October 2026):**
  - include the exact statement "NHSBSA Copyright 2025" (omitting it is a breach of the licence; re-check the year on the dataset page before reuse);
  - cite the dataset as: NHS Business Services Authority. "English Prescribing Dataset (EPD) with SNOMED Code" NHS Business Services Authority Open Data.
    Accessed [date]. URL: https://opendata.nhsbsa.net/dataset/english-prescribing-dataset-epd-with-snomed-code;
  - the licence is the Open Government Licence v3.0.
* **NHS England Digital files (GP registrations, QOF).** Their terms and conditions (section 8) release the content under the Open Government Licence.
  If you combine or adapt it you must state: "Contains information from NHS England, licenced under the current version of the Open Government Licence".
  Do not use NHS England logos or branding, and do not imply endorsement. Checked 22 October 2026.
* **IMD 2019.** GOV.UK states all content is available under the Open Government Licence v3.0 unless otherwise stated, with Crown copyright (checked 22 October 2026).
* Caveats on the page that matter here: no Patient Group Direction supplies and no dental prescribing; hospital prescribing only under
  cost-centre codes; BNF and SNOMED codes can change between monthly files; tagged experimental.

## 2. Patients registered at each GP practice, by LSOA (list size and deprivation)
* Publication page (January 2024): https://digital.nhs.uk/data-and-information/publications/statistical/patients-registered-at-a-gp-practice/january-2024
* Direct file: https://files.digital.nhs.uk/A0/3479F2/gp-reg-pat-prac-lsoa-male-female-Jan-24.zip
* The zip holds all-persons, male and female LSOA files. Save **`gp-reg-pat-prac-lsoa-all.csv`** as `data/raw/gp_lsoa.csv` (the male and female files are not needed).
* Checked against the real file: 872,885 rows, 6,325 practices, extract date 01Jan2024, about 63.1 million patients.
  Columns: `PUBLICATION, EXTRACT_DATE, PRACTICE_CODE, PRACTICE_NAME, LSOA_CODE, SEX, NUMBER_OF_PATIENTS`.

## 3. Diabetes prevalence: QOF 2023-24
* Publication page: https://digital.nhs.uk/data-and-information/publications/statistical/quality-and-outcomes-framework-achievement-prevalence-and-exceptions-data/2023-24
* Raw CSV zip: https://files.digital.nhs.uk/DA/975A29/QOF2324.zip (9 MB)
* Use **`PREVALENCE_2324.csv`** from the zip, saved as `data/raw/qof_diabetes.csv`. Checked against the real file:
  columns are `PRACTICE_CODE, GROUP_CODE, REGISTER, PATIENT_LIST_TYPE, PRACTICE_LIST_SIZE`; the loader keeps
  `GROUP_CODE = DM`, which gives 6,267 practices, one row each, all with list type `17OV` (patients aged 17+).
* The other files in the zip (achievement by region, indicator and geography mappings) are not needed.

## 4. Deprivation: English Indices of Deprivation 2019, File 7
* Page: https://www.gov.uk/government/statistics/english-indices-of-deprivation-2019
* Direct CSV (9 MB, no conversion needed): https://assets.publishing.service.gov.uk/media/5dc407b440f0b6379a7acc8d/File_7_-_All_IoD2019_Scores__Ranks__Deciles_and_Population_Denominators_3.csv
* Save as `data/raw/imd.csv`. England only. Checked: 32,844 LSOAs.
* **Match check (real data):** 99.94% of GP patients live in LSOAs found in IMD 2019. The unmatched codes are Welsh
  (`W01...`) or placeholders; 12 of 6,325 practices fall below 95% coverage (mostly border practices).

## Final folder layout
```
data/raw/
  epd/epd_202304.csv ... epd_202403.csv
  gp_lsoa.csv
  qof_diabetes.csv
  imd.csv
```
Then, on any system: `python -m src.ingest --source data/raw`, `python -m src.build_marts`, `python -m src.checks`, `python -m src.analysis`, `python -m src.export_for_powerbi` (or, with `make`: `make ingest marts checks analyse export`)

## Things to record in your README
* The window above and why the sources were matched this way.
* That QOF uses a 17+ denominator and list size comes from one quarterly snapshot.
* The NHSBSA copyright statement and citation (see the README, Attribution and licence).
