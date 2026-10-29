# NYC Charter Schools Map

An interactive map of New York City's charter schools for the 2025–26 school year.

**Live map:** `https://<your-username>.github.io/nyc-charter-schools-map/`

- **293 of the 299 schools** on the state roster mapped across all five boroughs
- Search by name or address, and filter by borough or authorizer
- Click any school for its address, community school district, year opened and authorizer
- Download the cleaned data as [CSV](data/charter_schools.csv) or [GeoJSON](data/charter_schools.geojson)

## Data sources

| What | Source | As of |
|---|---|---|
| Which schools exist | [NYSED Charter School Directory](https://www.nysed.gov/charter-schools/charter-schools-directory) (Excel) | Sep 2, 2025 (2025–26 roster) |
| Where they are | [NCES EDGE Public School Locations 2024–25](https://data-nces.opendata.arcgis.com/datasets/nces::public-school-locations-2024-25) | 2024–25 school year |
| Where the newest schools are | [SUNY Charter Schools Institute](https://www.newyorkcharters.org/charter-schools/?region=nyc) school pages, [InsideSchools](https://insideschools.org/), GreatSchools, state BEDS record | Checked Oct 2026 |

The state directory is the official list of charter schools, but it has no addresses or coordinates. NCES publishes geocoded locations for every US public school. This project uses the state list to decide *which* schools to show, and NCES to decide *where* to put them.

These are the most recent official releases. No 2026–27 roster with locations has been published yet.

## Method

[`scripts/build_data.py`](scripts/build_data.py) rebuilds everything in `data/` from the two files in `data/raw/`:

1. **Roster:** keep the 299 NYSED schools in the New York City region.
2. **Locations:** keep NCES schools in the five NYC counties that belong to a charter school. In NCES, each NY charter school is its own small education agency, while DOE schools sit inside the large community school districts. That separates the two cleanly.
3. **Match:** the sources share no common ID, so schools are matched on normalized names within the same borough:
   - 272 matched exactly after normalization (case, punctuation, "The", "Charter School", common abbreviations)
   - 1 matched by fuzzy name similarity (≥ 0.85). Fuzzy matches must also have the same trailing number, so "South Bronx Classical V" can never match "South Bronx Classical IV".
   - 8 matched by hand, where NCES truncates or abbreviates the name (for example "COLLEGIATE ACADEMY-MATH-PERSONAL AWA"). These are listed in the script.
   - The script stops with an error if two roster schools land on the same location.
4. **Newest schools:** schools that opened in fall 2025 or later aren't in the NCES 2024–25 file. For 12 of them, addresses come from authorizer records and school directories, listed with source links in [`data/new_school_addresses.csv`](data/new_school_addresses.csv). Their coordinates were estimated by hand from the address and nearby schools with known coordinates, so each is marked as accurate to a block or a neighborhood. They show on the map as dashed pins.

```bash
pip install pandas openpyxl
python scripts/build_data.py
```

## Limitations

- **6 schools aren't on the map.** They opened in fall 2025 or 2026, and neither the federal data nor their authorizer has published a street address yet. Several likely operate inside an existing network school's building. They're listed with borough and district in [`data/unmapped_schools.csv`](data/unmapped_schools.csv).
- **12 pins are approximate.** The dashed pins for the newest schools are placed by hand. Once NCES publishes 2025–26 locations, rerunning the build with that file will give exact positions. Explore Enrich is mapped at its state-registered address, a suite in the building that also houses the Explore network office.
- **Borough follows the address.** Two schools have a federally reported address in a different borough than the state roster: Achievement First Legacy (roster: Brooklyn, address: St. Albans, Queens) and Atmosphere Academy (roster: Bronx, address: Marble Hill, legally Manhattan). The map uses the address.
- **Updated locations.** Success Academy NYC 17 is listed in the Bronx on the September 2025 state roster, but its authorizer now places it in Ridgewood, Queens. The map uses the authorizer's address. The roster's "Zeta Charter School - Queens 2" appears to be the campus SUNY calls Zeta Queens Flushing.
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
data/new_school_addresses.csv  addresses and estimated coordinates for schools opened 2025+
data/unmapped_schools.csv      roster schools with no address yet
data/raw/                  original source files
scripts/build_data.py      rebuilds data/ from data/raw/
```

Built with [Leaflet](https://leafletjs.com/). Basemap © [OpenStreetMap](https://www.openstreetmap.org/copyright) contributors, © [CARTO](https://carto.com/attributions).
