# Power BI dashboard: build notes

This document describes how the five-page Power BI report is built: data files, model, measures, page layouts and design conventions.
It is written so the report can be rebuilt or audited. Power BI Desktop (free, Windows only) is required. Every figure below was checked
against the real data; section 9 lists the reference values the finished report should show.

## 0. Files
The files are produced by `python -m src.export_for_powerbi` followed by `python -m src.make_dashboard_files`. The second command creates four
small, clean files in `data/exports/` that load into Power BI with no repair steps (the raw marts cause type errors because
whole numbers are stored as `1.0` and the first rows are blank):

| File | Rows | One row per |
|---|---|---|
| `dashboard_practice.csv` | 6,248 | analysed GP practice |
| `dashboard_icb.csv` | 42 | ICB |
| `dashboard_trend.csv` | 60 | month x deprivation quintile (newer-drug share) |
| `dashboard_class.csv` | 481 | month x quintile x drug class |

`powerbi/theme.json` is the colour and font theme.

## 1. Load
Home > Get data > Text/CSV, load all four files with **Load** (not Transform). Open **Table view** and confirm:
`list_size`, `imd_quintile`, `total_items` are whole numbers; `newer_share`, `imd_score` are decimals; `month_start` is a date;
`imd_group`, `region`, `outlier_status` are text. If any are wrong, fix with Column tools > Data type.

## 2. Theme
View > Themes > Browse for themes > choose `theme.json`. If Power BI rejects it, skip it and set colours by hand:
navy `#1D4E89`, red `#C44536`, greys `#B8C0CC`, page background `#F4F6F8`, font Segoe UI.

## 3. Model
Model view. Create one relationship by dragging `dashboard_icb[icb_code]` onto `dashboard_practice[icb_code]`: one-to-many,
single direction (ICB filters practice). Leave `dashboard_trend` and `dashboard_class` unrelated (England-wide).
Sort columns: select `imd_group` in each table, Column tools > Sort by column > `imd_quintile`.
Then Home > Enter data, name the table `_Measures`, Load. Put every measure below on it (create each with Home > New measure).

## 4. Measures
```DAX
Practices = COUNTROWS ( dashboard_practice )
Patients = SUM ( dashboard_practice[list_size] )
Newer Items = SUM ( dashboard_practice[newer_items] )
Non-insulin Items = SUM ( dashboard_practice[non_insulin_items] )
Newer Share = DIVIDE ( [Newer Items], [Non-insulin Items] )
National Newer Share = CALCULATE ( [Newer Share], REMOVEFILTERS ( dashboard_practice ) )
Items per Register Patient =
    DIVIDE ( SUM ( dashboard_practice[total_items] ), SUM ( dashboard_practice[diabetes_register] ) )
Q1 Share = CALCULATE ( [Newer Share], dashboard_practice[imd_quintile] = 1 )
Q5 Share = CALCULATE ( [Newer Share], dashboard_practice[imd_quintile] = 5 )
Deprivation Gap (pp) = ( [Q5 Share] - [Q1 Share] ) * 100
Outlier Practices =
    CALCULATE ( COUNTROWS ( dashboard_practice ), dashboard_practice[outlier_status] <> "Not an outlier" )
Trend Share = DIVIDE ( SUM ( dashboard_trend[newer_items] ), SUM ( dashboard_trend[non_insulin_items] ) )
Trend Gap (pp) =
    ( CALCULATE ( [Trend Share], dashboard_trend[imd_quintile] = 5 )
    - CALCULATE ( [Trend Share], dashboard_trend[imd_quintile] = 1 ) ) * 100
```
Formats: `Newer Share`, `National Newer Share`, `Q1 Share`, `Q5 Share`, `Trend Share` = Percentage, 1 decimal.
`Deprivation Gap (pp)` and `Trend Gap (pp)` = decimal, 1 place. `Patients` = whole number, thousands separator.

## 5. Page setup (applies to every page)
Format page > Canvas settings: Type = 16:9 (1280 x 720). Position values below are in pixels
(Format visual > General > Properties > Size and Position: X, Y, Width, Height). The tabs are named Overview, Geography,
Deprivation, Trends, Practices.

**Header (every page).** Text box at X 24, Y 12, W 900, H 40: "Diabetes prescribing across English GP practices, 2023-24"
(Segoe UI Semibold 24, colour #1B2A41). Second text box X 24, Y 50, W 900, H 24 with the page's takeaway (12 pt, #5C6B7A).
Insert > Buttons > Navigator > Page navigator, X 920, Y 16, W 336, H 36.

**Footer (every page).** Text box X 24, Y 664, W 1232, H 44, 9 pt grey: "Practice-level, observational data. Associations are not
causes and do not measure care quality. Source: NHSBSA English Prescribing Dataset (EPD) with SNOMED Code; NHS England Digital (GP registrations,
QOF 2023-24); MHCLG English Indices of Deprivation 2019. NHSBSA Copyright 2025. Contains information from NHS England, licenced under
the current version of the Open Government Licence. Contains public sector information licensed under the Open Government Licence v3.0.
Independent analysis, not endorsed by NHSBSA, NHS England or MHCLG." The NHSBSA and
NHS England wordings are licence conditions and are reproduced exactly (including NHS England's spelling "licenced").

**Slicers (Overview, Geography, Deprivation).** Dropdown style. Region = `dashboard_icb[region]` at X 24, Y 84, W 300, H 40.
ICB = `dashboard_icb[icb_short]` at X 336, Y 84, W 300, H 40. Sync them across pages (View > Sync slicers).

## 6. Pages

### Page 1 Overview. Takeaway: "Newer drugs are used less in more deprived practices, though total prescribing per patient is higher."
Cards, Y 136, H 84, W 296, X = 24, 336, 648, 960: `Practices`, `Patients` (label "Registered patients": it is list size, not people with diabetes), `Newer Share` (label "Newer-drug share"), `Deprivation Gap (pp)`
(label "Gap, least vs most deprived (points)"). Charts, Y 236, H 420, W 400, X = 24, 440, 856:
1. **Clustered column.** X = `dashboard_practice[imd_group]`, Y = `Newer Share`. Axis from 0 to 35%. Data labels on, 1 decimal.
   Colour Q1 `#C44536`, Q5 `#1D4E89`, Q2 to Q4 `#B8C0CC` (Format > Columns > Colors, pick each category). Title:
   "Newer-drug share by practice deprivation".
2. **Clustered column.** X = `imd_group`, Y = `Items per Register Patient`. Same colours, labels on. Title:
   "Diabetes items per patient on the register".
3. **100% stacked column** from `dashboard_class`. X = `imd_group`, Y = `items`, Legend = `drug_class`. Add a visual-level filter
   `drug_class` is not Insulin (Filters pane). Title: "What non-insulin diabetes prescribing consists of (England)".
   This table is not linked to the Region/ICB slicers, so select each slicer in turn, then Format > Edit interactions, and switch **only this chart** to "None". Leave the other charts and cards on Filter, then test: pick an ICB and confirm both column charts and all four cards change together.
   Set the series colours so only the two newer classes stand out: SGLT2 inhibitor `#2A9D8F`, GLP-1 / GIP agonist `#E9A23B`, and greys for the rest (Format > Columns > Colors). Also exclude `Unclassified` in the visual filter (it is one row). Do not reuse red or navy here: they mean Q1 and Q5 elsewhere.

### Page 2 Geography. Takeaway: "Where a practice is matters: ICB averages range from 19.6% to 30.3%."
1. **Clustered bar** (X 24, Y 136, W 740, H 520). Axis = `dashboard_icb[icb_short]`, Values = `dashboard_icb[newer_share]`
   (Sum is fine, one row per ICB). Sort descending by `newer_share`. Colour by rule (Format > Bars > Colors > fx > Rules):
   `vs_national_pp` greater than 0 = `#1D4E89`, less than or equal to 0 = `#C44536`. Font size 9. Data labels on.
   Title: "Newer-drug share by ICB (blue = above England, red = below)".
2. **Clustered bar** (X 780, Y 136, W 476, H 250). Axis = `dashboard_practice[region]`, Values = `Newer Share`, sorted descending.
   Title: "By NHS region".
3. **Table** (X 780, Y 402, W 476, H 254). `dashboard_icb`: `icb_short`, `practices`, `mean_imd_score`, `crude_prevalence_pct`.
   Title: "ICB context".
   Set `mean_imd_score` and `crude_prevalence_pct` to Don't summarize, and turn Totals off (Format visual > Table > Totals), because a total of averages is meaningless.

### Page 3 Deprivation. Takeaway: "A modest gradient, with large variation between practices at any deprivation level."
1. **Scatter** (X 24, Y 136, W 740, H 520). X Axis = `dashboard_practice[imd_score]`, Y Axis = `dashboard_practice[newer_share]`,
   Values = `practice_code` (called Details in older versions). **Set X and Y to Average** (click the arrow beside each field in its bucket):
   when Values is filled in, Power BI requires a summarization on X and Y, and "Don't summarize" gives the error
   "Can't display this visual: Remove Values to display x- and y-axis pairs". Each practice code is on one row, so the average is the
   practice's own value. (Alternative: remove Values, keep Don't summarize, and put `practice_name` in Tooltips.)
   Analytics pane > Trend line on. Title: "Each dot is a GP practice".
   Add a small text box: "England-wide adjusted odds ratio 0.97 per 10 IMD points (95% CI 0.96 to 0.99)". It is fixed text, so it must say England-wide: it does not respond to the Region/ICB slicers.
2. **Card** (X 780, Y 136, W 476, H 84): `Outlier Practices`, label "Practices far outside the expected range (99.8% limits)".
3. **Stacked bar** (X 780, Y 236, W 476, H 420). Axis = `dashboard_practice[icb_short]`, Legend = `outlier_status`, Values = the `Practices` measure.
   Do not use the `Outlier Practices` measure here: its filter overrides the legend and every segment would show the combined total.
   Filters pane: `outlier_status` is not "Not an outlier"; Top N = 12 on `icb_short` by `Practices`. Colours: High `#1D4E89`, Low `#C44536`.
   Title: "ICBs with the most outlier practices (top 12, ties included)". (Top N keeps ties, so 13 ICBs can show; 34 of 42 ICBs have at least one outlier.)

### Page 4 Trends. Takeaway: "Newer-drug use rose everywhere, but faster where deprivation is lowest."
Select every visual and set Edit interactions so the region/ICB slicers do not affect them (trend data are England-wide). Add a note saying so.
1. **Line chart** (X 24, Y 100, W 740, H 556). X = `dashboard_trend[month_start]` (use the date, not the hierarchy), Y = `Trend Share`,
   Legend = `imd_group`. Colour Q1 `#C44536` and Q5 `#1D4E89` with thick lines; Q2 to Q4 thin greys. Title: "Newer-drug share by month".
2. **Line chart** (X 780, Y 100, W 476, H 270). X = `month_start`, Y = `Trend Gap (pp)`. Data labels on first and last points. Title:
   "Gap between least and most deprived (points)".
3. **Text box** (X 780, Y 386, W 476, H 270), 12 pt: "Q1 (most deprived) rose from 23.0% to 25.8%. Q5 (least deprived) rose from 25.3% to 29.2%.
   The gap widened from 2.3 to 3.4 points. GLP-1 supply problems in 2023-24 may affect all practices."

### Page 5 Practices. Takeaway: "Look up any practice. Outside the limits means unusual, not poorer care."
**Table** (X 24, Y 136, W 1232, H 520): `practice_code` (first, so every row is unique), `practice_name`, `icb_short`, `region`, `list_size`, `imd_score`, `newer_share`, `items_per_register_patient`,
`outlier_status`. Rename the headers "Registered patients" (list_size) and "Diabetes items per register patient". Add a search slicer (Slicer > ... > Search) on `practice_name` at X 24, Y 84, W 300, H 40, and a dropdown slicer on `outlier_status`.
Set `imd_score`, `newer_share` and `items_per_register_patient` to Don't summarize and turn Totals off.
Conditional formatting: `outlier_status` text colour via rules (High = navy, Low = red).

## 6b. Measure or column?
* **Measure** whenever a visual summarises many practices: cards, bars, lines, columns. Averaging the `newer_share` column would give a tiny
  practice the same weight as a huge one. The measures add items up first, then divide.
* **Column** for axes, legends, slicers and anything showing one row per practice or ICB (the scatter, the tables, the ICB bar chart).
  In tables, set those number columns to Don't summarize and turn Totals off. In the scatter chart use Average instead (see Page 3).
* **`items`, `list_size`, `newer_items`** are counts, so Sum is correct. **`imd_score`, `newer_share`, `prevalence_pct`** are never summed.
* Do not put a measure that uses CALCULATE on a column (`Outlier Practices`, `Q1 Share`, `Q5 Share`, `Trend Gap (pp)`) in a visual that also
  has that same column on its axis or legend, because the measure overrides it.

## 7. Design conventions
- Every chart title states the finding; hide axis titles that repeat the chart title.
- Axis and label fonts 11 pt grey; gridlines very light; no 3D, no pie charts; bar and column axes start at zero.
- Same colours for the same things on every page (Q1 red, Q5 navy).
- Model view: hide `icb_code` and other columns nobody will use; View > Page view > Fit to page.
- Add alt text to every chart, table, card and slicer (Format > General > Alt text), stating the finding, not just the chart type. Set the tab order (View > Selection pane) to follow reading order.
- Check each page for missing data warnings (a yellow triangle) and for overlapping visuals.

## 8. Saving and sharing
The report is saved as `diabetes_prescribing_dashboard.pbix`, with a PDF export and one screenshot per page in `docs/`.
Publish to web makes the report open to anyone with the link and cannot be restricted afterwards; the data are public aggregates. It needs a work or school account, otherwise share the PDF and screenshots.
The four CSV files are loaded from a neutral local folder (`C:\nhs-diabetes\dashboard\`) rather than a personal user folder, so the saved .pbix does not embed local folder names and can be re-pointed with Home > Transform data > Data source settings > Change Source.

## 9. Display names

Labels were renamed in the visuals only (Rename for this visual). The model, DAX and CSV files keep the original names.

| Where | Field in the model | Label shown |
|---|---|---|
| Overview cards | `_Measures[Newer Share]` | Newer-drug share |
| Overview cards | `_Measures[Patients]` | Registered patients |
| Overview cards | `_Measures[Deprivation Gap (pp)]` | Gap, least vs most deprived (points) |
| Geography, ICB context table | `dashboard_icb[icb_short]` | ICB |
| Geography, ICB context table | `dashboard_icb[practices]` | Practices |
| Geography, ICB context table | `dashboard_icb[mean_imd_score]` | Mean IMD |
| Geography, ICB context table | `dashboard_icb[crude_prevalence_pct]` | Prevalence % |
| Practices table | `dashboard_practice[practice_code]` | Practice code |
| Practices table | `dashboard_practice[practice_name]` | Practice |
| Practices table | `dashboard_practice[icb_short]` | ICB |
| Practices table | `dashboard_practice[region]` | Region |
| Practices table | `dashboard_practice[list_size]` | Registered patients |
| Practices table | `dashboard_practice[imd_score]` | Deprivation (IMD) |
| Practices table | `dashboard_practice[newer_share]` | Newer-drug share |
| Practices table | `dashboard_practice[items_per_register_patient]` | Diabetes items per register patient |
| Practices table | `dashboard_practice[outlier_status]` | Outlier status |
| Slicers | `dashboard_icb[icb_short]`, `dashboard_icb[region]` | ICB, Region |
| Slicers | `dashboard_practice[practice_name]`, `dashboard_practice[outlier_status]` | Practice, Outlier status |

"Registered patients" appears twice with different scope: on the Overview card it is the sum of list size across the filtered practices, and in the Practices table it is one practice's list size.

## 10. Reference values (checked against the data)
| Check | Expected |
|---|---|
| Practices / Patients | 6,248 / 63.0 million (63,003,275) |
| National newer-drug share | 25.4% |
| Newer share by group, Q1 / Q2 / Q3 / Q4 / Q5 | 24.3% / 24.5% / 25.7% / 26.1% / 27.1% |
| Deprivation gap | 2.8 points |
| Items per register patient, Q1 to Q5 | 16.9 / 16.3 / 15.0 / 14.7 / 14.2 |
| Outlier practices | 137 (83 high, 54 low) |
| Highest ICB | Hampshire and Isle of Wight 30.3%; then Somerset 30.2%, Dorset 30.2% |
| Lowest ICB | South East London 19.6%; then North East London 21.4%, Norfolk and Waveney 22.1% |
| Regions | London 22.6% lowest, South East 28.2% highest |
| Trend, Q1 first to last month | 23.0% to 25.8% |
| Trend, Q5 first to last month | 25.3% to 29.2% |
| Trend gap, first to last month | 2.3 to 3.4 points |
| Non-insulin class mix (England) | Metformin 48.0%, SGLT2 20.3%, DPP-4 13.2%, sulfonylurea 12.1%, GLP-1/GIP 5.2% |

If a number differs, check the relationship in step 3, the filters on the visual, and the measure's number format first.

## 11. Troubleshooting
| Symptom | Fix |
|---|---|
| Trend chart axis shows only 2023 and 2024, subtitle says "by Year" | In the X-axis bucket, click the arrow beside `month_start` and choose `month_start`, not Date Hierarchy. The gap chart should then read 2.3 and 3.4 |
| Items-per-patient bars all the same height, axis shows 0.33 | The Y axis maximum was copied from the percentage chart. Clear it (Auto), keep minimum 0 |
| Shares show as 0.30 instead of 30% | Table view > select the `newer_share` column > Column tools > Format > Percentage, 1 decimal (do it in all three tables) |
| Card shows "6K" | Format > Callout value > Display units > None |
| Grey subtitles show field names ("Sum of x by y") | Format > General > Title > Subtitle: turn off or enter custom text |
| Axis labels or legend cut off | Shorten labels (`"Q" & imd_quintile`), move legend to Bottom, smaller font, or widen the chart |
| Navigator buttons show "Ove...", "Geo..." | Make the navigator wider (for example X 700, W 556) or reduce its font size |
| Line colours do not match their groups | Format > Lines > Colors, set per series: Q1 red, Q5 navy, Q2 to Q4 greys |
