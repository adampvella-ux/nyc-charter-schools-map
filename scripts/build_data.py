"""Build the NYC charter school map data.

Joins the official NYSED charter school roster (which schools exist) with
NCES geocoded school locations (where they are), and writes:

  data/charter_schools.geojson   mapped schools, loaded by index.html
  data/charter_schools.csv       same records as a flat table
  data/unmapped_schools.csv      roster schools with no published location yet

Usage:  python scripts/build_data.py
Needs:  pandas, openpyxl
"""
from __future__ import annotations

import difflib
import json
import re
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
OUT = ROOT / "data"

ROSTER_FILE = RAW / "nys-charter-school-directory-2025-09-02.xlsx"
LOCATIONS_FILE = RAW / "nces-public-school-locations-2024-25-NY.csv"

# NYSED county name -> borough, and NCES county name -> NYSED county name
BOROUGH = {"New York": "Manhattan", "Kings": "Brooklyn", "Bronx": "Bronx",
           "Queens": "Queens", "Richmond": "Staten Island"}
NCES_COUNTY = {f"{c} County": c for c in BOROUGH}

# Pairs the automatic matcher can't resolve because one source abbreviates
# or truncates the name, or lists a different county. Checked by hand.
# NYSED name -> NCES name
MANUAL_BY_NCES_NAME = {
    "Achievement First Legacy Charter School": "ACHIEVEMENT FIRST LEGACY CHARTER SCHOOL",
    "AECI II:  NYC Charter High School for Computer Engineering and Innovation": "AECI II:  NYC CHARTER HS",
    "Atmosphere Academy Public Charter School": "ATMOSPHERE ACADEMY PUBLIC CHARTER SCHOOL",
    "Bronx Global Learning Institute for Girls Charter School, the Shirley Rodrguez-Remeneski School": "BGLIG-SHIRLEY RODRIGUEZ-REMENESKI CS",
    "Collegiate Academy for Mathematics and Personal Awareness Charter School": "COLLEGIATE ACADEMY-MATH-PERSONAL AWA",
    "Ember Charter School for Mindful Education, Innovation and Transformation": "EMBER CHARTER SCHOOL",
    "New York City Charter High School for Architecture, Engineering & Construction Industries": "NYC CHARTER HS - AECI",
    "South Bronx Charter School for International Cultures and the Arts": "SOUTH BRONX CHARTER SCHOOL",
}

ROMAN_OR_NUMBER = re.compile(r"\b(i{1,3}|iv|vi{0,3}|ix|x|\d+)\b")


def norm(name: str) -> str:
    """Normalize a school name so the two sources' spellings line up."""
    s = name.lower().replace("&", " and ")
    s = re.sub(r"\(the\)|\bthe\b", "", s)
    s = re.sub(r"[^a-z0-9 ]", " ", s)
    swaps = {"charter school": "", "charter": "", "cs": "", "academy": "acad",
             "preparatory": "prep", "school": "sch", "high": "hs", "for": "",
             "of": "", "and": "", "international": "intl"}
    for old, new in swaps.items():
        s = re.sub(rf"\b{old}\b", new, s)
    return " ".join(s.split())


def load_roster() -> pd.DataFrame:
    df = pd.read_excel(ROSTER_FILE, header=1, dtype={"SED Code": str, "Institution ID": str})
    df = df[df["Region"] == "New York City"].copy()
    df["key"] = df["Charter School Name"].map(norm)
    return df


def load_locations() -> pd.DataFrame:
    df = pd.read_csv(LOCATIONS_FILE, dtype=str)
    df = df[df["NMCNTY"].isin(NCES_COUNTY)].copy()
    # In NCES each NY charter school is its own tiny LEA; the 32 community
    # districts and other DOE units are large LEAs. 3600127 is a small DOE
    # unit for hospital schools, not a charter.
    lea_size = df["LEAID"].map(df["LEAID"].value_counts())
    df = df[(lea_size <= 3) & (df["LEAID"] != "3600127")].copy()
    df["county"] = df["NMCNTY"].map(NCES_COUNTY)
    df["key"] = df["NAME"].map(norm)
    return df


def match(roster: pd.DataFrame, locs: pd.DataFrame) -> pd.Series:
    """Return the NCES row index for each roster row (or None)."""
    by_name = {v: k for k, v in locs["NAME"].items()}
    result = {}
    for i, school in roster.iterrows():
        name = school["Charter School Name"]
        if name in MANUAL_BY_NCES_NAME:
            result[i] = by_name[MANUAL_BY_NCES_NAME[name]]
            continue
        pool = locs[locs["county"] == school["County"]]
        exact = pool[pool["key"] == school["key"]]
        if len(exact) == 1:
            result[i] = exact.index[0]
            continue
        # Fuzzy fallback, but only when trailing numerals agree, so
        # "South Bronx Classical V" never matches "South Bronx Classical IV".
        best = max(pool.index, key=lambda j: difflib.SequenceMatcher(
            None, school["key"], pool.at[j, "key"]).ratio())
        score = difflib.SequenceMatcher(None, school["key"], pool.at[best, "key"]).ratio()
        same_suffix = ROMAN_OR_NUMBER.findall(school["key"]) == ROMAN_OR_NUMBER.findall(pool.at[best, "key"])
        result[i] = best if score >= 0.85 and same_suffix else None
    matched = pd.Series(result)
    dupes = matched.dropna()[matched.dropna().duplicated()]
    if len(dupes):
        raise SystemExit(f"Two roster schools matched one location: {dupes.tolist()}")
    return matched


def title_address(s: str) -> str:
    """'116 E 169TH ST-4TH FL' -> '116 E 169th St-4th Fl'."""
    return re.sub(r"[A-Za-z]+", lambda m: m.group(0).lower() if m.start() and s[m.start() - 1].isdigit()
                  else m.group(0).capitalize(), s)


def main() -> None:
    roster, locs = load_roster(), load_locations()
    roster["nces_row"] = match(roster, locs)

    mapped, unmapped = [], []
    for _, s in roster.iterrows():
        rec = {
            "name": s["Charter School Name"].replace("  ", " ").strip(),
            "borough": BOROUGH[s["County"]],
            "district": s["School District"],
            "year_opened": int(s["Year Opened"]),
            "authorizer": s["Authorizer"],
            "sed_code": s["SED Code"],
        }
        if pd.isna(s["nces_row"]):
            unmapped.append(rec)
            continue
        loc = locs.loc[s["nces_row"]]
        rec.update({
            "address": f"{title_address(loc['STREET'])}, {loc['CITY'].title()}, NY {loc['ZIP']}",
            "nces_id": loc["NCESSCH"],
            "lat": round(float(loc["LAT"]), 6),
            "lon": round(float(loc["LON"]), 6),
        })
        mapped.append(rec)

    features = [{
        "type": "Feature",
        "geometry": {"type": "Point", "coordinates": [r["lon"], r["lat"]]},
        "properties": {k: v for k, v in r.items() if k not in ("lat", "lon")},
    } for r in mapped]
    geo = {
        "type": "FeatureCollection",
        "metadata": {
            "roster": "NYSED Charter School Directory, as of 2025-09-02 (2025-26 school year)",
            "locations": "NCES EDGE Public School Locations 2024-25",
            "mapped": len(mapped),
            "unmapped": len(unmapped),
        },
        "features": features,
    }
    (OUT / "charter_schools.geojson").write_text(json.dumps(geo, indent=1))
    pd.DataFrame(mapped).sort_values("name").to_csv(OUT / "charter_schools.csv", index=False)
    pd.DataFrame(unmapped).sort_values("name").to_csv(OUT / "unmapped_schools.csv", index=False)
    print(f"NYC charter schools on roster: {len(roster)}")
    print(f"  mapped:   {len(mapped)}")
    print(f"  unmapped: {len(unmapped)} (opened after the 2024-25 location data)")


if __name__ == "__main__":
    main()
