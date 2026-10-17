# Issues found while building this project, and how they were resolved

A record of what went wrong, how it was noticed and what changed. The first four items affect how far the
results can be trusted; the rest are practical lessons.

## 1. The prescribing data had moved
**Problem.** The first plan used the original NHSBSA English Prescribing Dataset (EPD). Checking the portal showed it is
retired (it covers January 2014 to June 2025) and replaced by "EPD with SNOMED code".
**Fix.** Switched to the SNOMED version and its column names (`BNF_PRESENTATION_CODE`, `BNF_PRESENTATION_NAME`,
`BNF_CHEMICAL_SUBSTANCE`). Dates can arrive as `YYYYMM` or `YYYY-MM`, and the loader handles both.
**Lesson.** Check that a dataset is current before designing around it.

## 2. Two sources used different area-code versions
**Problem.** IMD 2019 uses 2011 LSOA codes. NHS England's GP-by-LSOA files switched to 2021 codes from July 2024, so a
later file would silently fail to match many patients to a deprivation score.
**Fix.** Used the January 2024 GP file and the April 2023 to March 2024 prescribing window (which also matches QOF 2023-24).
A pipeline check fails if fewer than 95% of patients match. On the real data, 99.94% matched.
**Lesson.** Look at identifier vintages before joining datasets.

## 3. The drug classifier put every drug in "Unclassified"
**Problem.** I assumed the chemical-substance column held drug names. In the real file it holds a BNF **code**
(e.g. `0601022B0`). The classifier matched names such as "metformin", so it matched nothing. Left uncaught, the
newer-drug share would have been 0% everywhere. The data check reported 51 unclassified substances, which is how it was found.
**Why my tests missed it.** The synthetic test data copied my wrong assumption (names in that column).
**Fix.** Insulins, sulfonylureas and metformin are now identified from the BNF section in the code
(060101x, 0601021, 0601022). The rest, in section 0601023, are identified from the product names of each chemical,
including brand-only products such as Mounjaro. The test data now matches the real layout. I then checked the
15 highest-volume substances against the real data: all were in the right class.
**Remaining.** One substance (Avandamet) is unclassified, which is 1 item out of about 61 million.
**New safeguard.** A check now fails if the SGLT2 or GLP-1 classes are absent.
**Lesson.** Synthetic data can only test assumptions you know you are making. Inspect the real file's contents.

## 4. Two of my data checks were badly designed
**Problem.** (a) "At least 90% of prescribing organisations have a denominator" failed. The data contain about 1,590
organisations that are not registered GP practices (hospitals, clinics, closed practices). (b) "No unclassified drugs"
treated one rare substance the same as a major one.
**Fix.** Replaced them with volume-based checks: included practices must account for at least 98% of diabetes items
(actual: 99.46%), and unclassified drugs must be under 0.5% of items. The exclusion table is printed on every build.
**Lesson.** A failing check can be a faulty check. Look at the numbers before changing the data or the rule.

## 5. The variance-between-ICBs model did not converge
**Problem.** A mixed model produced repeated convergence warnings, and its ICC values (19.5% and 16.5%) were unreliable.
**Fix.** Replaced it with a one-way ANOVA intraclass correlation and a bootstrap that resamples ICBs, which always
converges and gives a 95% interval. Reported values: 17.5% (11.6% to 23.5%) unadjusted and 16.1% (10.0% to 21.8%) adjusted.
**Lesson.** Do not report numbers from a model that warns it has not converged.

## 6. Downloading multi-gigabyte files was unreliable
**Problem.** Each monthly EPD file is 4 to 8 GB. The server returned a temporary 503 error on one month, and a connection
dropped partway through another (about 2.7 GB of 7.2 GB), which crashed the first version of the downloader.
**Fix.** The downloader now retries with increasing waits, catches the low-level connection errors, and resumes from the
last complete row with an HTTP Range request instead of starting over. Output only appears under its final filename once the
whole file has been read and its size verified. It was tested against a local server that deliberately dropped the connection
five times and ignored a resume request once.
**Lesson.** Anything that downloads large files over a home connection needs retries and resume.

## 7. Local setup problems on Windows
* **Database login failed** (`password authentication failed for user "nhs"`). The container was running correctly, so another
  PostgreSQL on the machine was most likely answering on port 5432 (not confirmed). The project now uses port 5433 by default.
* **`ModuleNotFoundError: dotenv`.** The virtual environment was not activated in that terminal. Run `.venv\Scripts\activate` first.
* **`make` is not available on Windows.** The README lists plain `python -m ...` commands for each step.

## Design decisions worth knowing
* Only 3 of the 16 files downloaded for QOF, GP and IMD are used; the rest are other QOF tables or male/female splits.
* Practices are excluded if list size is under 1,000, the diabetes register is under 20, or deprivation/prevalence is missing.
  Exclusions are reported rather than hidden.
* The practice deprivation score is a patient-weighted mean of LSOA scores, which is how larger areas are usually summarised.
* All results are practice-level and observational. See the Limitations section of the README.
