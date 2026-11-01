# Diabetes Prescribing and Health Inequalities in England

[![CI](https://github.com/boakyedwamena-alt/nhs-diabetes-prescribing/actions/workflows/ci.yml/badge.svg)](https://github.com/boakyedwamena-alt/nhs-diabetes-prescribing/actions/workflows/ci.yml)

**Question:** Is the share of non-insulin diabetes prescribing that is newer drugs (SGLT2 inhibitors and GLP-1 / GIP agonists) lower in more deprived GP practices in England, and how much does it vary between practices and Integrated Care Boards (ICBs) once deprivation, diabetes prevalence and practice size are taken into account?

**At a glance:** in 2023-24, GP practices in more deprived areas prescribed a slightly smaller share of the newer diabetes drugs (24.3% against 27.1% in the least deprived practices), although they issued more diabetes items per patient overall. Variation between practices was much larger than that gap: the middle half of practices ranged from 21% to 29%, about as widely within every deprivation fifth as overall. ICB averages ranged from 19.6% to 30.3% (unadjusted; the middle half of ICBs from 24% to 28%), and about one sixth of the practice-level variation sat between ICBs. The deprivation gap widened over the year (2.3 points in April 2023 to 3.4 in March 2024). These are practice-level patterns from public data. They do not show that any patient received worse care.

`PostgreSQL` `Python` `statsmodels` `Power BI` `GitHub Actions`

> **Status:** analysis complete on real data (April 2023 to March 2024).

## Headline findings
* Newer diabetes drugs (SGLT2 inhibitors and GLP-1 / GIP agonists) were **25.4%** of non-insulin diabetes prescribing.
  The share was **24.3% in the most deprived fifth of practices and 27.1% in the least deprived**.
* After adjusting for diabetes prevalence, practice size and NHS region, each 10-point rise in practice deprivation was
  associated with **3% lower odds** of a newer-drug item (odds ratio 0.97, 95% CI 0.96 to 0.99). Real, but modest.
* Overall prescribing volume went the other way: **16.9 diabetes items per patient on the register in the most deprived
  fifth versus 14.2 in the least deprived**.
* Practices vary far more than chance alone would give (overdispersion factor 89, which also reflects repeat prescribing), and about **one sixth of the variation sits between ICBs** (16%, 95% CI 10% to 22%, after adjusting for deprivation, prevalence and list size; NHS region is not adjusted for), which deprivation barely changes.
* ICB averages range from **19.6% to 30.3%** (unadjusted); the middle half of ICBs spans 23.9% to 28.0%, against a 2.8-point gap between deprivation fifths.
* The gap between the most and least deprived fifths **widened over the year** (2.3 points in April 2023 to 3.4 in March 2024, comparing single months), because newer drugs grew faster where deprivation was lowest.

![Overview page of the Power BI dashboard: newer-drug share and items per patient by practice deprivation fifth, and the mix of non-insulin diabetes drugs](docs/dashboard_overview.png)
*The Overview page of the Power BI dashboard. All five pages are shown in the [Dashboard](#dashboard) section.*

## Key terms
| Term | Meaning here |
|---|---|
| **Newer drugs** | SGLT2 inhibitors and GLP-1 / GIP agonists, two classes of diabetes medicine that NICE guidance targeted at people with cardiovascular, kidney or obesity-related needs (see "Why this matters") |
| **Newer-drug share** | Newer-drug items as a percentage of all non-insulin diabetes items a practice prescribed |
| **Diabetes items per patient** | Diabetes prescription items (insulins and antidiabetic drugs, BNF 060101 and 060102) issued in 12 months, divided by the number of patients on the practice's diabetes register. An overall measure of prescribing volume, separate from the drug mix |
| **Diabetes register** | The patients a practice has recorded as having diabetes, from the Quality and Outcomes Framework (QOF) prevalence data. It is smaller than the practice list |
| **ICB** | Integrated Care Board: the NHS organisation that plans and funds local services. There are 42 in England |
| **IMD** | Index of Multiple Deprivation 2019, an official measure of how deprived a small area is. A higher score means more deprived. A practice's score is the average across its patients' home areas |
| **LSOA** | Lower layer Super Output Area: a small census area of roughly 1,500 people, the unit at which IMD is published |
| **Deprivation fifth (quintile)** | Practices ranked by deprivation and split into five equal groups. Q1 is the most deprived and Q5 the least |
| **Odds ratio** | How much the odds of an item being a newer drug change for a given change in deprivation. 0.97 per 10 IMD points means 3% lower odds |
| **Funnel plot** | A chart comparing each practice with the national share, allowing for how much it prescribes. Practices beyond the limits are unusual, which is not the same as poorer care |
| **ICC** | Intraclass correlation: the share of variation that lies between ICBs and not between practices within the same ICB |

## Why this matters
NICE guidance on type 2 diabetes in adults ([NG28](https://www.nice.org.uk/guidance/ng28)) recommended SGLT2 inhibitors for some adults with chronic kidney disease (November 2021 update) and, from its February 2022 drug-treatment update, that an SGLT2 inhibitor be offered to people with established atherosclerotic cardiovascular disease or chronic heart failure and considered for people at high cardiovascular risk ([update information](https://www.nice.org.uk/guidance/ng28/chapter/Update-information)). GLP-1 receptor agonists were limited to later triple therapy in specific circumstances, including some people with obesity. These recommendations applied throughout the study window; NICE issued a further medicines update in February 2026.

NICE's [implementation advice on health inequalities](https://www.nice.org.uk/guidance/ng28/resources/implementation-advice-health-inequalities-in-type-2-diabetes-15609044701) names deprivation as a source of inequality and recommends monitoring uptake across population groups. If uptake is lower where deprivation is higher, that is a potential inequality; if it varies widely between ICBs after adjustment for deprivation, prevalence and practice size, that is variation worth examining. This project measures both, using public data only. It cannot say whether any variation is unwarranted, because clinical eligibility data (kidney function, cardiovascular disease, BMI) are not available.

## Data (all free and open)
| Source | Used for |
|---|---|
| NHSBSA English Prescribing Dataset (EPD) with SNOMED code, BNF 6.1, Apr 2023 to Mar 2024 | items by practice, month and drug (cost is loaded but not analysed) |
| NHS England Digital: patients registered at GP practices by LSOA | list size and practice deprivation (via patient-weighted LSOA scores) |
| NHS England Digital: QOF 2023-24 diabetes register | diabetes prevalence |
| English Indices of Deprivation 2019 (IMD) | deprivation score per LSOA |

Details, expected file names and the reasons for the chosen study window are in [`docs/DATA_SOURCES.md`](docs/DATA_SOURCES.md).

## Architecture
```mermaid
flowchart LR
  A[NHSBSA EPD] --> I
  B[GP patients by LSOA] --> I
  C[QOF diabetes] --> I
  D[IMD 2019] --> I
  I[Python ingest\nidempotent, partitioned] --> R[(raw)]
  R --> S[(staging\nfilter, classify)]
  S --> M[(marts\npractice, window, ICB, trend)]
  M --> P[Python analysis\nGLM, funnel, ICC]
  M --> B2[Power BI]
  P --> F[figures and flags]
```

**PostgreSQL design.** `raw.epd` is list-partitioned by month; each month is reloaded by truncating its partition, so
re-running never duplicates rows. Staging filters to insulins (BNF 060101) and antidiabetic drugs (060102), dropping
hypoglycaemia, diagnostic and monitoring items that share BNF section 6.1. Marts have a fact table at
practice x month x drug class, plus a 12-month practice table, an ICB summary and a class-by-quintile trend.
`staging.dq_summary` records what was excluded rather than dropping rows silently.

## Methods
* **Outcome:** newer-drug share = SGLT2 + GLP-1/GIP items as a share of non-insulin diabetes items, latest 12 months.
  Also items per diabetes-register patient, as an overall volume measure.
* **Drug classes:** the class comes from the BNF code of the chemical substance: section 060101x is insulin, 0601021 sulfonylureas and 0601022 metformin. Within 0601023 (other antidiabetic drugs) it comes from matching generic and brand names in the product descriptions (for example dapagliflozin or Forxiga, semaglutide or Ozempic, tirzepatide or Mounjaro). Where a product matches more than one name, the most specific class wins (GLP-1 / GIP agonist, then SGLT2 inhibitor, then DPP-4 inhibitor), so dapagliflozin with metformin counts as an SGLT2 inhibitor. Only products in section 0601023 can be flagged as newer drugs. The non-insulin denominator is every other class (metformin, sulfonylureas, DPP-4 inhibitors, pioglitazone, other, unclassified). The name list is maintained by hand, so a new brand-only product would stay unclassified until added; the checks fail if unclassified items reach 0.5%. One substance (Avandamet, about 1 item in 61 million) is unclassified.  
* **Deprivation:** patient-weighted mean IMD 2019 score across the LSOAs a practice's patients live in.
  Quintile 1 = most deprived fifth of included practices.
* **Inclusion:** list size at least 1,000; diabetes register at least 20; deprivation and prevalence available.
  Excluded practices are counted and reported, not hidden.
* **Models:**
  * **Newer-drug share:** a binomial GLM on newer vs other non-insulin items, with ICB-clustered robust standard errors, adjusted for diabetes prevalence, log list size and NHS region.
  * **Volume:** an OLS model on log items per register patient, with the same adjustment and clustering.
  * **Variation between ICBs:** a one-way ANOVA intraclass correlation (ICC) on each practice's newer-drug share, unweighted and floored at zero. The adjusted version uses the residuals from a linear (OLS) fit on deprivation, prevalence and list size. It does not adjust for region, so it includes differences between NHS regions. The 95% interval is a percentile bootstrap that resamples ICBs (500 resamples, fixed seed). A mixed model was tried first but did not converge; see [`docs/ISSUES_AND_FIXES.md`](docs/ISSUES_AND_FIXES.md).
* **Funnel plot:** overdispersion-adjusted limits (Spiegelhalter 2005, *Statistics in Medicine* 24:1185-1202) around the national share. The overdispersion factor is the mean of squared z-scores, winsorised at the 10th and 90th percentiles and floored at 1, and it widens the limits by the same multiple at every practice size. Practices outside the 99.8% limits are flagged as outliers (the 137 reported); the 95% limits are also stored for the dashboard. Overdispersion is expected, so unadjusted limits would flag most practices.

## Run it
Works on Windows, macOS and Linux. It needs Python 3.12, Docker (Docker Desktop on Windows or macOS, Docker Engine on Linux) and about 15 GB of free disk space for the
intermediate files. `make` is optional: Windows does not include it, and every `make` target below has a plain `python -m ...` equivalent that behaves the same on every system.

**1. Set up** (run from the repository folder)

| | Create and activate the virtual environment |
|---|---|
| Windows, PowerShell | `python -m venv .venv` then `.venv\Scripts\Activate.ps1` (if scripts are blocked, run `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` first) |
| Windows, Command Prompt | `python -m venv .venv` then `.venv\Scripts\activate.bat` |
| macOS / Linux | `python3 -m venv .venv` then `source .venv/bin/activate` |

On Windows, use `py -3.12 -m venv .venv` if `python` is not found. Then, on every system:
```bash
pip install -r requirements.txt
docker compose up -d db           # PostgreSQL 16 on localhost:5433 (keep Docker running)
```

**2. Try it first on synthetic data** (no downloads, under a minute; results are NOT real). These commands are the same on every system:
```bash
python -m src.make_demo_data
python -m src.ingest --source data/demo
python -m src.build_marts
python -m src.checks
pytest -q
```
To also run the analysis and export on the demo data, send the output to separate folders so real results are never overwritten:

| | Demo analysis and export |
|---|---|
| macOS / Linux | `make demo` runs step 2 and this analysis and export (run `make test` for the unit tests), or: `OUTPUT_DIR=outputs/demo EXPORT_DIR=data/demo/exports python -m src.analysis` then the same prefix before `python -m src.export_for_powerbi` |
| Windows, PowerShell | `$env:OUTPUT_DIR="outputs/demo"; $env:EXPORT_DIR="data/demo/exports"`, then `python -m src.analysis` and `python -m src.export_for_powerbi`, then `Remove-Item Env:OUTPUT_DIR, Env:EXPORT_DIR` |
| Windows, Command Prompt | `set OUTPUT_DIR=outputs/demo` and `set EXPORT_DIR=data/demo/exports`, then `python -m src.analysis` and `python -m src.export_for_powerbi`, then `set OUTPUT_DIR=` and `set EXPORT_DIR=` |

> **Warning:** the demo loads synthetic data into the *same* PostgreSQL database as the real data and replaces the tables. Run the demo before loading
> real data, or point it at a separate database with `DATABASE_URL`, and re-run the real pipeline afterwards.

**3. Run it on the real data.** The commands below are the same on every system.
1. Put the three reference files in `data/raw/` as described in [`docs/DATA_SOURCES.md`](docs/DATA_SOURCES.md)
   (`gp_lsoa.csv`, `qof_diabetes.csv`, `imd.csv`).
2. Download the prescribing months (streams and keeps diabetes rows only; resumable, several hours in total):
   `python -m src.download_epd`
3. Load, build, check, analyse, export:
```bash
python -m src.ingest --source data/raw
python -m src.build_marts
python -m src.checks            # all 10 checks must pass before you trust the analysis
python -m src.analysis
python -m src.export_for_powerbi
python -m src.make_dashboard_files   # small clean CSVs for Power BI
```
4. Build the dashboard from [`powerbi/README.md`](powerbi/README.md).

If something fails, see [`docs/ISSUES_AND_FIXES.md`](docs/ISSUES_AND_FIXES.md), which records the problems met while
building this and how they were solved. Common ones: activate the virtual environment first, and keep Docker running.

## Results

### Part 1: deprivation and diabetes prevalence (real data, QOF 2023-24)
This part uses only the reference data (GP registrations, deprivation and QOF), before any prescribing is added. Run it with `make profile`, or on any system `python -m src.ingest --source data/raw --reference-only` followed by `python -m src.profile_reference`.

**Sample.** **6,248 of the 6,325 practices** in the GP registration file are included. 58 have no QOF diabetes register, and 19 of the remaining 6,267 have fewer than 1,000 registered patients, fewer than 20 people on the diabetes register, or no deprivation score. The patient-weighted deprivation score was available for almost every patient (median practice coverage 99.98%). 12 practices have under 95% coverage; they are kept, with scores based on the patients who matched an LSOA. Across the included practices, crude diabetes prevalence is 7.7%.

**By deprivation quintile** (1 = most deprived; [`outputs/results/prevalence_by_deprivation_quintile.csv`](outputs/results/prevalence_by_deprivation_quintile.csv)):

| Deprivation quintile | Practices | Mean IMD score | Crude diabetes prevalence (aged 17+) |
|---|---|---|---|
| 1 (most deprived) | 1,250 | 41.6 | 9.25% |
| 2 | 1,249 | 28.5 | 8.22% |
| 3 | 1,250 | 21.4 | 7.63% |
| 4 | 1,249 | 15.3 | 7.23% |
| 5 (least deprived) | 1,250 | 9.8 | 6.42% |

Mean IMD score is the average of practices' patient-weighted IMD 2019 scores in each fifth (higher means more deprived). Quintiles here are cut in pandas on practice rank and cover every GP-file practice that meets the inclusion rules. Part 2 uses SQL NTILE on practices that also have diabetes prescribing data, so group sizes and a few memberships differ slightly.

Practice-level rank correlation between deprivation and prevalence is 0.51 (Spearman). These are **crude** rates: the data have no age breakdown, and deprived areas are not simply older or younger, so the gradient mixes real differences with age structure. Treat it as the context for the prescribing analysis, not as a standalone finding.

![Scatter plot of crude diabetes prevalence against practice deprivation, with a rising straight-line fit from about 6% in the least deprived practices to about 12% in the most deprived](outputs/figures/00_prevalence_vs_deprivation.png)

*Red line: straight-line fit. Prevalence is crude (no age adjustment), and each dot is one practice.*

### Part 2: newer-drug prescribing (real data, April 2023 to March 2024)
**Sample.** Of the 6,325 practices in the GP registration file, 5 have no diabetes prescribing in the data. Of the other 6,320, 54 had no QOF diabetes register, 17 had under 1,000 patients and 1 had a diabetes register under 20 (each counted once, in that order); none lacked a deprivation score. That leaves 6,248 GP practices in 42 ICBs, which account for 99.5% of diabetes prescribing in the data. A further 1,590 prescribing organisations with no GP registration record (mostly non-GP prescribers and closed practices) carry 0.4% of items.

**By deprivation quintile** (1 = most deprived; [`outputs/results/by_deprivation_quintile.csv`](outputs/results/by_deprivation_quintile.csv)):

| Quintile | Practices | Newer-drug share of non-insulin items | Diabetes items per register patient |
|---|---|---|---|
| 1 (most deprived) | 1,250 | 24.3% | 16.9 |
| 2 | 1,250 | 24.5% | 16.3 |
| 3 | 1,250 | 25.7% | 15.0 |
| 4 | 1,249 | 26.1% | 14.7 |
| 5 (least deprived) | 1,249 | 27.1% | 14.2 |

![Scatter plot of newer-drug share against practice deprivation for 6,248 practices, with a trend line falling from about 27% in the least deprived practices to about 24% at an IMD score of 30, then flat; individual practices range from about 10% to 40% at any deprivation level](outputs/figures/01_newer_share_vs_deprivation.png)
*"GLP-1" on the axis includes GIP agonists (tirzepatide), as in the rest of this README.*

The smoothed trend falls from about 27% in the least deprived practices to about 24% around an IMD score of 30, then flattens. So the average association in the models below is driven mainly by the less-to-moderately deprived end, and the models, which assume a constant effect, summarise it with one number. The trend is small relative to the spread of individual practices, which is why deprivation explains little of the practice-to-practice variation. Above an IMD score of about 55 there are few practices, so the trend there is less certain.

**Models** ([`outputs/results/results.json`](outputs/results/results.json); standard errors clustered by ICB):

| Question | Result |
|---|---|
| Odds of a newer-drug item per 10 IMD points, adjusted | OR 0.97 (95% CI 0.96 to 0.99, p < 0.001) |
| Diabetes items per register patient per 10 IMD points, adjusted | +4.3% (95% CI 2.0% to 6.6%) |
| Share of practice-level variance in newer-drug share lying between ICBs | 17.5% (95% CI 11.6% to 23.5%) unadjusted; 16.1% (10.0% to 21.8%) after adjusting for deprivation, prevalence and list size |

Across the 31.8-point gap in mean IMD score between the most and least deprived fifths (41.6 against 9.8, from the Part 1 table), the odds ratio compounds to
about 0.91 (calculated from the per-10-point estimate, not a separate model). The volume result means practices in
deprived areas issued more diabetes items per patient with diabetes, which could reflect more complex disease or more
drugs per person, and is not evidence of better or worse care.

**Practice variation.** The middle half of practices (25th to 75th percentile of raw practice shares, which include some chance variation) had a newer-drug share between 21.2% and 29.2%, a spread of 8.0 points, and the spread within each deprivation fifth was similar (7.6 to 8.2 points). The middle half of ICBs ranged from 23.9% to 28.0%. A funnel plot with overdispersion-adjusted limits (factor 89.0) flags **137 practices (2.2%)**
outside the 99.8% limits: 83 above and 54 below the national share. Practices are unusual in clusters rather than at random:
high outliers are concentrated in Mid and South Essex (9), Hampshire and Isle of Wight (8), Kent and Medway (6) and
Lancashire and South Cumbria (6); low outliers in West Yorkshire (14), North East London (14), North East and North Cumbria (7)
and South East London (5). That points to ICB-level or local factors such as formularies, guidance or population mix, but
these data cannot say which. Clusters are not always one-directional: West Yorkshire has 14 low outliers and 3 high ones, which suggests wide variation between practices as well as an ICB-level effect. The full list is in [`outputs/results/funnel_flags.csv`](outputs/results/funnel_flags.csv).

![Funnel plot of newer-drug share against non-insulin diabetes items for each practice, with the national share at 25.4% and practices outside the 99.8% limits in red](outputs/figures/02_funnel_plot.png)

*Dashed red lines: 99.8% limits. Dotted grey lines: 95% limits. Limits allow for overdispersion (factor 89). Red points are unusual practices, not necessarily poorer care.*

**Over time.** The newer-drug share rose in every quintile: from 23.0% in April 2023 to 25.8% in March 2024 in the most deprived fifth and from 25.3% to 29.2% in the least deprived. Comparing those single months, the gap widened from 2.3 to 3.4 percentage points. (The 2.8-point gap in the quintile table pools all twelve months.)

![Line chart of monthly newer-drug share for each deprivation fifth, April 2023 to March 2024, rising in every group from about 23% to 26% in the most deprived and from about 25% to 29% in the least deprived](outputs/figures/03_trend_by_quintile.png)

*Q1 is the most deprived fifth and Q5 the least. The rise steepens in early 2024 in every group; these data cannot say why.*

**Geography.** ICB averages (total newer-drug items divided by total non-insulin items across the ICB's included practices, so larger practices count for more) range from 19.6% (South East London) to 30.3% (Hampshire and Isle of Wight), a spread of
10.7 points. By NHS region, London is lowest (22.6%) and the South East highest (28.2%). These are unadjusted descriptions;
they are not the adjusted estimates above, and the data cannot say why ICBs differ.

## Dashboard
A five-page Power BI report (`powerbi/`, build notes with DAX in [`powerbi/README.md`](powerbi/README.md)) lets readers explore the results by region and ICB.
Screenshots of each page are below. Report file: [`powerbi/diabetes_prescribing_dashboard.pbix`](powerbi/diabetes_prescribing_dashboard.pbix). Open it in Power BI Desktop, then use Home > Transform data > Data source settings > Change Source to point the four data sources at your own copies of `dashboard_*.csv` (written to `data/exports/` by `python -m src.make_dashboard_files`).

| | |
|---|---|
| ![Overview](docs/dashboard_overview.png) | ![Geography](docs/dashboard_geography.png) |
| ![Deprivation](docs/dashboard_deprivation.png) | ![Trends](docs/dashboard_trends.png) |
| ![Practices](docs/dashboard_practices.png) | |

## What this means for decision-makers
Intended readers: ICB medicines-optimisation and health-inequalities teams, NHS England regional teams and primary care networks.

* **The scale is material, not trivial.** If the most deprived fifth of practices had the newer-drug share of the least deprived fifth, they would have issued about **308,000 more newer-drug items** in the year (11.5% more than they did, 2.3% of all newer-drug items nationally). If the 17 ICBs below the England share had matched it, the difference would be about **581,000 items** (4.3% of all newer-drug items nationally). These are
  *illustrations of scale*, not targets: whether higher use would be clinically appropriate cannot be judged from these data.
* **Geography is a large source of difference.** The ICB scenario (about 581,000 items) is roughly twice the size of the deprivation scenario (about 308,000), but the two are not like-for-like: one lifts 17 ICBs to the England average, the other lifts one fifth of practices to the level of another fifth, and the ICB figures are unadjusted, so they partly reflect differences in deprivation and population mix (across the 42 ICBs, mean deprivation and newer-drug share are moderately correlated, Spearman -0.49). Deprivation does not explain everything: London ICBs are low whether they are among the more deprived (North East London ranks 9th most deprived of 42, South East London 13th) or among the less deprived (South West London ranks 36th). The largest single gaps are North East London (about 107,000 items), South East London (84,000), North East and North Cumbria (70,000) and West Yorkshire (59,000). Together, North East London, South East London and South West London account for about 39% of the ICB gap.
* **Variation is not confined to a few hotspots.** Six ICBs hold 47% of the 137 outlier practices, but 34 of 42 ICBs have at least one. About 84% of practice-level variation lies *within* ICBs (after adjustment), so an ICB-wide message alone would not reach most of it. Practice-level peer comparison is the natural tool.
* **The gap is growing.** The gap between the least and most deprived fifths widened from 2.3 to 3.4 percentage points between April 2023 and March 2024, because uptake rose faster where deprivation was lowest. Monitoring it monthly would show whether it narrows.
* **Higher volume per patient in deprived areas** (16.9 versus 14.2 items per patient on the register) could reflect more complex disease,
  more drugs per person, or differences in how patients are coded or reviewed. These data cannot say which. It is worth understanding before reading
  anything into the newer-drug gap.

The scenario figures in this section are produced by `python -m src.scenarios`.

**Suggested uses.** Use the funnel plot to prioritise which practices or ICBs to look at first, never to judge them. Before any review, add
clinical eligibility information (kidney function, cardiovascular disease, BMI) that is not in these data. For the ICB clusters, check local
formularies, guidance, shared-care pathways with specialist clinics, and supply problems in 2023-24.

## Further work
* **Adjust for clinical need.** The QOF files include practice-level registers for conditions such as chronic kidney disease, coronary heart
  disease, heart failure and obesity. Adding them to the models would test how much of the pattern reflects eligibility. This is the most
  valuable next step.
* **Add age structure.** NHS England publishes registered patients by age; age-standardising prevalence would improve the context analysis.
* **Sensitivity checks.** Repeat the analysis with SGLT2 inhibitors alone, with different practice-size thresholds, without the 12 practices with under 95% IMD coverage, and with a longer period. Repeat the volume model without the prevalence term (see Limitations), and try an additive random-effects version of the funnel plot.
* **Costs.** NHSBSA changed its actual-cost methodology in April 2024, so a cost analysis needs a later window and care with comparisons.
* **Ethnicity** is not available at practice level in these sources, which limits what can be said about inequalities beyond deprivation.

## Limitations

**Study design**
* **Ecological and observational.** Practice-level patterns do not describe individual patients, and association is not cause.
* **Prescribing is not need.** Eligibility for newer drugs depends on kidney function, cardiovascular disease, BMI and other factors that are not in these data. Differences may reflect case mix.
* **Newer drugs are not always better drugs for every patient.** The share is a measure of uptake, not of appropriateness.
* **Funnel outliers are unusual, not "bad".** Coding, shared-care arrangements and specialist clinics can explain them.
* **Supply effects.** GLP-1 shortages during 2023-24 affect prescribing independently of practice behaviour. The window is one year, so these results describe that year only.
* **Guidance changed after the study window.** NICE issued a medicines update to NG28 in February 2026. These results describe prescribing in 2023-24 under the February 2022 drug-treatment recommendations and should not be read as a comparison with current guidance.
* **Off-label and weight-loss use.** During the 2023-24 GLP-1 shortage some diabetes-licensed GLP-1 and GIP products may have been prescribed off-label for weight loss. The data cannot separate these items from use in diabetes, so the GLP-1/GIP share may be overstated in some practices.

**Data and definitions**
* **Items are not patients.** The outcome counts prescription items, so the share reflects how often and for how long items are issued as well as how many people take each drug.
* **Denominators and timing.** List size and deprivation come from a single LSOA extract (January 2024, all ages), while QOF reflects the 2023-24 year and uses a 17+ denominator. The QOF list is a median of about 82% of the LSOA list size, so crude prevalence and items per register patient are approximations.
* **Type of diabetes.** The QOF register covers all diabetes in people aged 17 and over and does not separate type 1 from type 2, so the denominator includes people with type 1 diabetes.
* **No age adjustment.** The data have no age breakdown, so prevalence is crude and deprivation may partly stand in for age structure.
* **Age of the deprivation data.** IMD 2019 is based on indicators from before 2019, so it may not reflect deprivation in 2023-24, especially in areas that have changed quickly. It covers England only and uses 2011 LSOAs.
* **Low-coverage practices.** 12 practices have under 95% of their patients matched to an IMD score. They are kept, with scores based on the matched patients.
* **Practice changes.** Mergers and closures mean some organisations lack denominators and are excluded (1,590 organisations, 0.4% of diabetes items).
* **Scope of the prescribing data.** The EPD excludes medicines supplied under Patient Group Directions and dental prescribing, and includes hospital prescribing only when issued under cost-centre codes. NHSBSA also notes that BNF and SNOMED codes for a product can change over time, and tags the dataset as experimental. Items, not costs, are analysed, so the April 2024 change to actual-cost methodology does not affect these results.
* **Insulin and GLP-1 combinations.** Xultophy (insulin degludec with liraglutide, 17,837 items, about 0.1% of newer-drug items) is in BNF section 0601023 and counts as a newer drug. Suliqua (insulin glargine with lixisenatide, 1,095 items) is in the insulin section and is excluded from the non-insulin items. The two are treated differently; the volumes are small.

**Statistics**
* **Items are not independent.** The funnel plot and overdispersion factor treat each prescription item as an independent event, but one patient receives many items over the year. The factor of 89 therefore reflects both real practice differences and repeat prescribing, so "varies more than chance" is a relative measure, not an exact one. The regression standard errors are clustered by ICB, which partly allows for this.
* **ICC.** It is calculated on each practice's raw newer-drug share, which includes some chance variation, especially for small practices. Given the size of the overdispersion, the effect is probably small and would make the ICC slightly low. It is also unweighted, so every practice counts equally, and the adjusted version does not adjust for NHS region, so it includes differences between regions.
* **Shared denominator in the volume model.** Items per register patient and diabetes prevalence both depend on the diabetes register, so they are mechanically linked, and the volume model adjusts for prevalence. Treat the +4.3% as approximate.

## Attribution and licence
**Code:** MIT Licence (see [`LICENSE`](LICENSE)). The data, and results derived from them, carry the attributions below.

**NHSBSA Copyright 2025.**

Contains information from NHS England, licenced under the current version of the Open Government Licence.

Contains public sector information licensed under the
[Open Government Licence v3.0](https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/).

This is an independent project. It is not endorsed or approved by NHSBSA, NHS England or the Ministry of Housing, Communities and
Local Government, and it uses none of their logos or branding.

Prescribing data: NHS Business Services Authority. "English Prescribing Dataset (EPD) with SNOMED Code". NHS Business Services Authority
Open Data. Accessed 17 October 2026. URL: https://opendata.nhsbsa.net/dataset/english-prescribing-dataset-epd-with-snomed-code

Other sources: NHS England Digital, *Patients Registered at a GP Practice* (January 2024) and *Quality and Outcomes Framework 2023-24*
(published under the Open Government Licence through NHS England Digital's terms and conditions, section 8, which set the NHS England
statement above); Ministry of Housing, Communities and Local Government, *English Indices of Deprivation 2019* (GOV.UK: all content under
the Open Government Licence v3.0 unless otherwise stated; Crown copyright). This repository contains analysis code
and aggregated results only; it does not redistribute the source files. This project follows the dataset page's caveats, citation wording and the Open Government Licence.

## Issues and fixes
The problems found while building this project (a retired dataset, mismatched area codes, a classifier bug caught by a data check, badly designed checks, an unreliable model, failed downloads, and a licence-attribution correction) are written up in [`docs/ISSUES_AND_FIXES.md`](docs/ISSUES_AND_FIXES.md).

## Repo layout
```
sql/        01_schema, 02_staging, 03_marts
src/        config, db, colmap, ingest, build_marts, checks, profile_reference, analysis, scenarios, stats, export_for_powerbi, make_dashboard_files, download_epd, make_demo_data
tests/      unit tests for the funnel and ICC statistics
LICENSE     MIT licence for the code
powerbi/    the Power BI report (.pbix), build notes with DAX, and theme
docs/       data sources, issues found and how they were fixed, dashboard screenshots
.github/    CI: runs tests and the full demo pipeline against Postgres
```

## Author
Emmanuel Dwamena, MSc Data Analytics (Distinction), BSc Biomedical Science. [LinkedIn](https://linkedin.com/in/emmanuel-dwamena)
