# Issues found while building this project, and how they were resolved

A record of what went wrong, how it was noticed and what changed. The first four items affect how far the
results can be trusted; the rest are practical takeaways.

## 1. The prescribing data had moved
**Problem.** The first plan used the original NHSBSA English Prescribing Dataset (EPD). Checking the portal showed it is
retired (it covers January 2014 to June 2025) and replaced by "EPD with SNOMED code".
**Fix.** Switched to the SNOMED version and its column names (`BNF_PRESENTATION_CODE`, `BNF_PRESENTATION_NAME`,
`BNF_CHEMICAL_SUBSTANCE`). Dates can arrive as `YYYYMM` or `YYYY-MM`, and the loader handles both.
**Takeaway.** A dataset's current status is checked before the design is built around it.

## 2. Two sources used different area-code versions
**Problem.** IMD 2019 uses 2011 LSOA codes. NHS England's GP-by-LSOA files switched to 2021 codes from July 2024, so a
later file would silently fail to match many patients to a deprivation score.
**Fix.** Used the January 2024 GP file and the April 2023 to March 2024 prescribing window (which also matches QOF 2023-24).
A pipeline check fails if the median practice has under 95% of its patients matched to an IMD score. On the real data, 99.94% of patients matched overall (median practice coverage 99.98%).
**Takeaway.** Identifier vintages are compared before datasets are joined.

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
Residual risk. Drugs in BNF section 0601023 are classified by matching product names, so a renamed or new product could be misclassified without triggering the class-absent check. The 15 highest-volume substances were checked by hand, and the unclassified-volume check (under 0.5% of items) would catch a large failure but not a small one. Also noted: Xultophy (insulin degludec with liraglutide) is classified as a GLP-1 / GIP agonist because it sits in section 0601023 and the GLP-1 keywords take priority, whereas Suliqua (insulin glargine with lixisenatide) sits in the insulin section and is excluded from the non-insulin items.
**Takeaway.** Synthetic data can only test the assumptions already being made, so the real file's contents are inspected directly.

## 4. Two of my data checks were badly designed
**Problem.** (a) "At least 90% of prescribing organisations have a denominator" failed. The data contain about 1,590
organisations that are not registered GP practices (hospitals, clinics, closed practices). (b) "No unclassified drugs"
treated one rare substance the same as a major one.
**Fix.** Replaced them with volume-based checks: included practices must account for at least 98% of diabetes items
(actual: 99.46%), and unclassified drugs must be under 0.5% of items. The exclusion table is printed on every build.
**Takeaway.** A failing check can be a faulty check, so the numbers are examined before the data or the rule is changed.

## 5. The variance-between-ICBs model did not converge
**Problem.** A mixed model produced repeated convergence warnings, and its ICC values (19.5% and 16.5%) were unreliable.
**Fix.** Replaced it with a one-way ANOVA intraclass correlation and a bootstrap that resamples ICBs, which does not depend on an iterative fit and gives a 95% interval. The adjusted value is the same calculation applied to the residuals of a linear fit on deprivation, prevalence and list size (region is not adjusted for). Reported values: 17.5% (11.6% to 23.5%) unadjusted and 16.1% (10.0% to 21.8%) adjusted.
**Takeaway.** Numbers from a model that warns it has not converged are not reported.

## 6. Downloading multi-gigabyte files was unreliable
**Problem.** Each monthly EPD file is 4 to 8 GB. The server returned a temporary 503 error on one month, and a connection
dropped partway through another (about 2.7 GB of 7.2 GB), which crashed the first version of the downloader.
**Fix.** The downloader now retries with increasing waits, catches the low-level connection errors, and resumes from the
last complete row with an HTTP Range request instead of starting over. Output only appears under its final filename once the
whole file has been read and its size verified. It was tested against a local server that deliberately dropped the connection
five times and ignored a resume request once.
**Takeaway.** Large downloads over a home connection need retries and resume.

## 7. Local setup problems on Windows
* **Database login failed** (`password authentication failed for user "nhs"`). The container was running correctly, so another PostgreSQL on the machine was most likely answering on port 5432 (not confirmed). The project now uses port 5433 by default.
* **`ModuleNotFoundError: dotenv`.** The virtual environment was not activated in that terminal; activating it (`.venv\Scripts\activate`) resolved the error.
* **`make` is not available on Windows.** The README lists plain `python -m ...` commands for each step.

## 8. Licence and citation conditions
**Problem.** I drafted the attribution as "NHSBSA Copyright 2023-24" without checking the dataset page. NHSBSA's dataset page requires the exact statement
"NHSBSA Copyright 2025" and a specific citation format, and says omitting the statement breaches the licence. The dashboard footer also lacked it.
**Fix.** Read the page (checked 22 October 2026) and updated the README (Attribution and licence), the data-source notes and the dashboard footer text. A check of the other three sources found that NHS England Digital's terms require their own attribution statement ("Contains information from NHS England,
licenced under the current version of the Open Government Licence") when their data is combined or adapted. It was added to the README and the dashboard footer.
The IMD page is under the Open Government Licence v3.0 with Crown copyright and needs no extra wording.
**Takeaway.** Licence conditions are taken from the source page and quoted exactly, not from memory.

## Design decisions worth knowing
* Only 3 of the 16 files downloaded for QOF, GP and IMD are used; the rest are other QOF tables or male/female splits.
* Practices are excluded if list size is under 1,000, the diabetes register is under 20, or deprivation/prevalence is missing.
  Exclusions are reported rather than hidden.
* The practice deprivation score is a patient-weighted mean of LSOA scores, which is how larger areas are usually summarised.
* Of 6,325 practices in the GP registration file, 5 have no diabetes prescribing in the data. Of the other 6,320, 54 have no QOF diabetes record, 17 have a list size under 1,000 and 1 has a register under 20, leaving 6,248. The 12 practices with under 95% IMD coverage are kept, with scores based on matched patients.
* All results are practice-level and observational. See the Limitations section of the README.
