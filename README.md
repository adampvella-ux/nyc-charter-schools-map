# NYC Charter Schools Map

An interactive map of New York City's charter schools for the 2025–26 school year.

**Live map:** `https://<your-username>.github.io/nyc-charter-schools-map/`

- **281 schools mapped** across all five boroughs, out of 299 on the state roster
- Search by name or address, and filter by borough or authorizer
- Click any school for its address, community school district, year opened and authorizer
- Download the cleaned data as [CSV](data/charter_schools.csv) or [GeoJSON](data/charter_schools.geojson)

## Data sources

| What | Source | As of |
|---|---|---|
| Which schools exist | [NYSED Charter School Directory](https://www.nysed.gov/charter-schools/charter-schools-directory) (Excel) | Sep 2, 2025 (2025–26 roster) |
| Where they are | [NCES EDGE Public School Locations 2024–25](https://data-nces.opendata.arcgis.com/datasets/nces::public-school-locations-2024-25) | 2024–25 school year |

The state directory is the official list of charter schools, but it has no addresses or coordinates. NCES publishes geocoded locations for every US public school. This project uses the state list to decide *which* schools to show, and NCES to decide *where* to put them.

Both are the most recent official releases. No 2026–27 roster with locations has been published yet.

## Method

[`scripts/build_data.py`](scripts/build_data.py) rebuilds everything in `data/` from the two files in `data/raw/`:

1. **Roster:** keep the 299 NYSED schools in the New York City region.
2. **Locations:** keep NCES schools in the five NYC counties that belong to a charter school. In NCES, each NY charter school is its own small education agency, while DOE schools sit inside the large community school districts. That separates the two cleanly.
3. **Match:** the sources share no common ID, so schools are matched on normalized names within the same borough:
   - 272 matched exactly after normalization (case, punctuation, "The", "Charter School", common abbreviations)
   - 1 matched by fuzzy name similarity (≥ 0.85). Fuzzy matches must also have the same trailing number, so "South Bronx Classical V" can never match "South Bronx Classical IV".
   - 8 matched by hand, where NCES truncates or abbreviates the name (for example "COLLEGIATE ACADEMY-MATH-PERSONAL AWA"). These are listed in the script.
   - The script stops with an error if two roster schools land on the same location.

```bash
pip install pandas openpyxl
python scripts/build_data.py
```

## Limitations

- **18 newer schools aren't on the map.** They opened in fall 2025 or 2026, after the NCES 2024–25 location data. They're listed with borough and district in [`data/unmapped_schools.csv`](data/unmapped_schools.csv), and rerunning the build with the 2025–26 NCES file (once published) will place them.
- **One point per school, not per campus.** Some charter schools operate several buildings. The state roster lists 299 NYC schools, while the [NYC Charter Center](https://findnyccharterschools.org/) counts roughly 430 campuses. Each school is mapped at the main address it reports to the federal government.
- **Addresses are as reported for 2024–25.** A school that moved since then will show its previous location.

## Running locally

The page loads its data with `fetch`, so open it through a local web server rather than double-clicking the file:

```bash
python -m http.server 8000
# then open http://localhost:8000
```

## Project structure

```
index.html                 the map (Leaflet, no build step)
data/charter_schools.geojson   mapped schools, loaded by the page
data/charter_schools.csv       same data as a table
data/unmapped_schools.csv      roster schools with no location yet
data/raw/                  original source files
scripts/build_data.py      rebuilds data/ from data/raw/
```

Built with [Leaflet](https://leafletjs.com/). Basemap © [OpenStreetMap](https://www.openstreetmap.org/copyright) contributors, © [CARTO](https://carto.com/attributions).
