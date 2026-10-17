"""Run staging and marts SQL, then print the data-quality summary."""
import pandas as pd

from src.config import MIN_DIABETES_REGISTER, MIN_LIST_SIZE, SQL_DIR
from src.db import get_engine, run_sql_file


def main() -> None:
    run_sql_file(SQL_DIR / "02_staging.sql")
    run_sql_file(SQL_DIR / "03_marts.sql",
                 {"min_list": MIN_LIST_SIZE, "min_register": MIN_DIABETES_REGISTER})
    dq = pd.read_sql("SELECT * FROM staging.dq_summary", get_engine())
    print(dq.to_string(index=False))
    un = pd.read_sql("SELECT d.chemical_substance, d.bnf_section, d.example_names, SUM(s.items) AS items "
                     "FROM staging.dim_drug d JOIN staging.stg_epd s USING (chemical_substance) "
                     "WHERE d.drug_class = 'Unclassified' GROUP BY 1,2,3 ORDER BY 4 DESC", get_engine())
    print("\nUnclassified substances:", "none" if un.empty else "")
    if not un.empty:
        print(un.to_string(index=False))
    cls = pd.read_sql("SELECT drug_class, COUNT(*) AS substances FROM marts.dim_drug GROUP BY 1 ORDER BY 2 DESC", get_engine())
    print("\nDrug classes found:"); print(cls.to_string(index=False))
    exc = pd.read_sql("""SELECT CASE WHEN list_size IS NULL THEN '1 no GP registration record (non-GP organisations, closed practices)'
        WHEN diabetes_register IS NULL THEN '2 no QOF diabetes register' WHEN list_size < %(a)s THEN '3 list size too small'
        WHEN diabetes_register < %(b)s THEN '4 diabetes register too small' WHEN imd_score IS NULL THEN '5 no IMD score'
        ELSE '6 included' END AS reason, COUNT(*) AS organisations, SUM(total_items) AS diabetes_items
        FROM marts.mart_practice_window GROUP BY 1 ORDER BY 1""", get_engine(),
        params={"a": MIN_LIST_SIZE, "b": MIN_DIABETES_REGISTER})
    exc["pct_of_items"] = (100 * exc.diabetes_items / exc.diabetes_items.sum()).round(2)
    print("\nOrganisations and prescribing volume by inclusion:"); print(exc.to_string(index=False))
    inc = pd.read_sql("SELECT COUNT(*) FILTER (WHERE include_in_analysis) AS included, COUNT(*) AS total "
                      "FROM marts.dim_practice", get_engine())
    print("\nPractices included in analysis:", inc.to_dict("records")[0])


if __name__ == "__main__":
    main()
