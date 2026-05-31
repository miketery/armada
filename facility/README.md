# FFL License Mapper

Local FastAPI and Leaflet app for exploring `0426-ffl-list.csv`.

## Data model

- FFL rows are loaded into SQLite at `data/ffl.sqlite`.
- Map coordinates use the U.S. Census 2025 ZCTA gazetteer file:
  `https://www2.census.gov/geo/docs/maps-data/data/gazetteer/2025_Gazetteer/2025_Gaz_zcta_national.zip`
- Coordinates are ZIP tabulation area estimates, not street-level geocodes. Guam, Northern Mariana Islands, and U.S. Virgin Islands rows fall back to territory centroids when no Census ZCTA centroid is available.
- Leaflet is vendored under `static/vendor/`. Map tiles are requested from OpenStreetMap at runtime.

## Commands

From this directory:

```bash
../.venv/bin/python -m app.import_data
../.venv/bin/uvicorn app.main:app --reload --port 8008
```

Then open:

```text
http://127.0.0.1:8008
```

## API

- `GET /api/stats`
- `GET /api/filters`
- `GET /api/markers?north=...&south=...&east=...&west=...&zoom=...`
- `GET /api/licenses`
- `GET /api/licenses/{id}`

