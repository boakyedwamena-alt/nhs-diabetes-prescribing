# Power BI dashboard build guide

Power BI Desktop is free and runs on Windows only (Microsoft Store: "Power BI Desktop"). A `.pbix` file cannot be
created outside it, so this guide gives the steps, field names and DAX. Allow 1 to 2 hours.

Run `python -m src.export_for_powerbi` first. It writes CSVs to `data/exports/`. You need three of them:

| File | Rows | One row per | Use |
|---|---|---|---|
| `mart_practice_window.csv` | 7,910 | practice (12 months) | most visuals |
| `mart_icb_summary.csv` | 42 | ICB | geography page |
| `mart_class_trend.csv` | 481 | month x deprivation quintile x drug class | trend page |

## 1. Load the data
1. Home > Get data > Text/CSV. Load the three files, choosing **Transform Data** each time.
2. In `mart_practice_window`: filter `include_in_analysis` to **true** (this removes organisations with no denominators, as in the analysis).
3. Check data types: `imd_quintile` whole number; `newer_share`, `imd_score`, `items_per_register_patient` decimal; `month_start` date.
4. Close & Apply. No relationships are needed because each page uses one table.

## 2. Calculated columns (Table view > New column)
```DAX
IMD Group =
SWITCH ( mart_practice_window[imd_quintile],
    1, "Q1 most deprived", 2, "Q2", 3, "Q3", 4, "Q4", 5, "Q5 least deprived" )
```
Select the column, then Column tools > Sort by column > `imd_quintile`. Add the same column to `mart_class_trend`
(change the table name). In `mart_icb_summary`, the ICB names are cut off in the source data, so shorten them:
```DAX
ICB Short =
VAR n = SUBSTITUTE ( mart_icb_summary[icb_name], "NHS ", "" )
RETURN PROPER ( LEFT ( n, SEARCH ( " INTEGRAT", n, 1, LEN ( n ) + 1 ) - 1 ) )
```

## 3. Measures (Home > New measure; put them on `mart_practice_window`)
```DAX
Practices = COUNTROWS ( mart_practice_window )
Patients = SUM ( mart_practice_window[list_size] )
Newer Items = SUM ( mart_practice_window[newer_items] )
Non-insulin Items = SUM ( mart_practice_window[non_insulin_items] )
Newer Share = DIVIDE ( [Newer Items], [Non-insulin Items] )
National Newer Share = CALCULATE ( [Newer Share], ALL ( mart_practice_window ) )
Gap vs National (pp) = ( [Newer Share] - [National Newer Share] ) * 100
Items per Register Patient =
    DIVIDE ( SUM ( mart_practice_window[total_items] ), SUM ( mart_practice_window[diabetes_register] ) )
Q1 Newer Share = CALCULATE ( [Newer Share], mart_practice_window[imd_quintile] = 1 )
Q5 Newer Share = CALCULATE ( [Newer Share], mart_practice_window[imd_quintile] = 5 )
Deprivation Gap (pp, Q5 minus Q1) = ( [Q5 Newer Share] - [Q1 Newer Share] ) * 100
Outlier Practices =
    CALCULATE ( COUNTROWS ( mart_practice_window ),
                CONTAINSSTRING ( mart_practice_window[funnel_flag], "99.8" ) )
```
On `mart_class_trend`:
```DAX
Newer Share (trend) =
DIVIDE (
    CALCULATE ( SUM ( mart_class_trend[items] ), mart_class_trend[is_newer_class] = TRUE () ),
    CALCULATE ( SUM ( mart_class_trend[items] ), mart_class_trend[drug_class] <> "Insulin" )
)
```
Format Newer Share and the trend measure as percentage (Measure tools > Format > Percentage, 1 decimal).

## 4. Pages
**Page 1, Overview.** Four cards: `Practices`, `Patients`, `National Newer Share`, `Deprivation Gap (pp, Q5 minus Q1)`.
Clustered column chart: X = `IMD Group`, Y = `Newer Share` (data labels on). Second column chart: X = `IMD Group`,
Y = `Items per Register Patient`. Slicers: `region_name` and `icb_name`. Title text: "Newer diabetes drugs are less common
in more deprived practices, but total prescribing per patient is higher".

**Page 2, Geography.** Bar chart from `mart_icb_summary`: Y = `ICB Short`, X = `newer_share`, sorted descending, with colour by
`region_name`. Optional map: use a Shape Map. Download the ICB boundaries from the ONS Open Geography Portal, convert to
TopoJSON at mapshaper.org, and load it under Format > Map > Custom map. The map key must be the 3-letter NHS ICB code, which
matches `icb_code` in the data (check the boundary file has it; if not, keep the bar chart).

**Page 3, Deprivation.** Scatter chart on `mart_practice_window`: X = `imd_score`, Y = `newer_share`, Details = `practice_code`.
Add a trend line from the Analytics pane. Add a text box: "Association at practice level, not a measure of care quality."

**Page 4, Trends.** Line chart on `mart_class_trend`: X = `month_start`, Y = `Newer Share (trend)`, Legend = `IMD Group`.
Title: "The gap between the most and least deprived practices widened over 2023-24".

**Page 5, Practice explorer.** Table: `practice_name`, `icb_name`, `list_size`, `newer_share`, `funnel_flag`,
`imd_quintile`. Slicer on `funnel_flag` and `region_name`. Add a note: "Outside the funnel limits means unusual compared with
chance, not poorer care."

## 5. Finishing
* Use one colour scheme across pages. Give every chart a title that states the finding.
* View > Themes for a clean look; hide field lists and gridlines.
* Put a caveat text box on every page (see the README Limitations).
* File > Save as `diabetes_prescribing_dashboard.pbix`. Take a screenshot of each page for the repo (`docs/`).
* File > Export > PDF for a version people can read without Power BI.

## Sharing
Publishing to the web needs a Power BI Service account, which requires a work or school email (personal Gmail or Outlook
addresses are usually rejected). If you cannot publish, put the screenshots and PDF in the repo instead. Wait for the NHSBSA
reply before making anything public.
