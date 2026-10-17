"""Map the column names in official NHS/ONS files to the names this project uses.

Official files change headers from year to year. Matching is case- and
punctuation-insensitive and accepts prefixes, so 'LSOA code (2011)' matches 'lsoacode2011'.
If a column cannot be found, a clear error lists the headers that were present so the
candidate lists below can be edited.
"""
import re

import pandas as pd


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", str(s).lower())


def apply_map(df: pd.DataFrame, mapping: dict, required: set, source: str) -> pd.DataFrame:
    normed = {_norm(c): c for c in df.columns}
    out, missing = {}, []
    for target, candidates in mapping.items():
        found = None
        for cand in candidates:
            nc = _norm(cand)
            if nc in normed:
                found = normed[nc]
                break
            hit = [orig for n, orig in normed.items() if n.startswith(nc)]
            if hit:
                found = hit[0]
                break
        if found is None:
            if target in required:
                missing.append(target)
        else:
            out[target] = df[found]
    if missing:
        raise ValueError(
            f"{source}: could not find columns for {missing}. "
            f"Headers present: {list(df.columns)}. Edit the candidate lists in src/colmap.py."
        )
    return pd.DataFrame(out)


EPD_MAP = {
    "year_month": ["YEAR_MONTH"],
    "practice_code": ["PRACTICE_CODE"],
    "practice_name": ["PRACTICE_NAME"],
    "postcode": ["POSTCODE"],
    "icb_code": ["ICB_CODE", "PCO_CODE"],
    "icb_name": ["ICB_NAME", "PCO_NAME"],
    "region_name": ["REGIONAL_OFFICE_NAME", "REGION_NAME"],
    "bnf_code": ["BNF_PRESENTATION_CODE", "BNF_CODE"],
    "bnf_description": ["BNF_PRESENTATION_NAME", "BNF_DESCRIPTION"],
    "chemical_substance": ["BNF_CHEMICAL_SUBSTANCE", "CHEMICAL_SUBSTANCE_BNF_DESCR"],
    "items": ["ITEMS"],
    "quantity": ["TOTAL_QUANTITY", "QUANTITY"],
    "nic": ["NIC"],
    "actual_cost": ["ACTUAL_COST"],
}
EPD_REQUIRED = {
    "year_month", "practice_code", "icb_code", "icb_name", "region_name",
    "bnf_code", "chemical_substance", "items", "nic",
}

GP_LSOA_MAP = {
    "practice_code": ["PRACTICE_CODE"],
    "lsoa_code": ["LSOA_CODE"],
    "number_of_patients": ["NUMBER_OF_PATIENTS"],
    "extract_date": ["EXTRACT_DATE"],
}
GP_LSOA_REQUIRED = {"practice_code", "lsoa_code", "number_of_patients"}

IMD_MAP = {
    "lsoa_code": ["LSOA code (2011)", "LSOA_CODE"],
    "imd_score": ["Index of Multiple Deprivation (IMD) Score", "IMD_SCORE"],
    "imd_decile": ["Index of Multiple Deprivation (IMD) Decile", "IMD_DECILE"],
}
IMD_REQUIRED = {"lsoa_code", "imd_score"}

QOF_MAP = {
    "practice_code": ["PRACTICE_CODE"],
    "group_code": ["GROUP_CODE", "INDICATOR_GROUP_CODE"],
    "register": ["REGISTER", "DM_REGISTER"],
    "list_size": ["PATIENT_LIST_SIZE", "PRACTICE_LIST_SIZE", "LIST_SIZE"],
}
QOF_REQUIRED = {"practice_code", "register"}
