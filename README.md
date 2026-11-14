# Snow Forecast Dashboard

Personal ski resort snow forecast engine and dashboard using public meteorological models and ground-truth snowpack telemetry.

## Target Resorts (Initial Scope)
- **Northstar California** (North Tahoe, CA)
- **Heavenly Mountain** (South Tahoe, CA/NV)
- **Kirkwood Mountain** (Sierra Crest, CA)
- **Park City Mountain** (Wasatch Back, UT)
- **Keystone Resort** (Summit County, CO)

## Public Data Sources
- **Open-Meteo** (`/v1/forecast` & `/v1/elevation`): Multi-model forecasts (`ecmwf_ifs025`, `gfs_global`, `gfs_hrrr`, `ncep_nbm_conus`, `gem_global`, `icon_global`) with Copernicus 90m DEM and elevation lapse-rate downscaling for Base, Mid, and Summit bands (gracefully skipped if unreachable).
- **MET Norway Locationforecast 2.0** (`api.met.no`): Global ECMWF-backed hourly/6h forecast adjusted for exact Base/Mid/Summit `altitude`.
- **US National Weather Service** (`api.weather.gov`): 2.5 km NDFD/NBM gridpoints (`quantitativePrecipitation`, `snowfallAmount`, `snowLevel`, temperature, wind).
- **USDA NRCS SNOTEL** (`wcc.sc.egov.usda.gov/awdbRestApi`): Automated SWE (`WTEQ`), snow depth (`SNWD`), precipitation (`PREC`), and temperature (`TOBS`).
- **California DWR CDEC** (`cdec.water.ca.gov/dynamicapp/wsSensorData`): Sierra Nevada snow pillows & depth sensors.

## Roadmap
- **Step 1 (Done):** Resort registry (`backend/app/resorts.json`) + station & NWS grid discovery (`discover_stations.py`)
- **Step 2 (Done):** Multi-model, NWS, SNOTEL, and CDEC ingestion (`fetch_snapshot.py`)
- **Step 3 (Done):** Custom snow physics (wet-bulb partitioning, dynamic SLR + wind compaction, storm settling) & consensus blending (`app/engine/`)
- **Step 4 (Done):** SQLite historical store (`data/snow.db`) + FastAPI REST API (`app/main.py`) + refresh pipeline (`app/scripts/update.py`)
- **Step 5:** React + Tailwind dashboard UI

## Running the Backend (Steps 1–4)

From `backend/` (using the virtual environment):

```bash
# Install dependencies
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt

# Run unit & API tests
.venv/bin/pytest tests -v

# Step 1: Discover DEM elevations, NWS gridpoints, and nearest SNOTEL stations -> app/resorts.json
.venv/bin/python -m app.scripts.discover_stations

# Step 2: Fetch raw forecasts & telemetry -> data/latest_snapshot.json
.venv/bin/python -m app.scripts.fetch_snapshot

# Steps 3 & 4: Fetch live data, run snow physics + consensus engine, and store in SQLite (data/snow.db)
.venv/bin/python -m app.scripts.update
# Or reprocess the latest saved snapshot offline:
.venv/bin/python -m app.scripts.update --from-snapshot

# Start the FastAPI server (port 8000)
.venv/bin/uvicorn app.main:app --reload --port 8000
```

### API Endpoints
- `GET /api/health` — API & latest SQLite forecast run status
- `GET /api/runs` — Recent forecast runs stored in SQLite
- `GET /api/resorts` — Overview cards for all 5 resorts (24h/48h/72h/5d/7d Base/Mid/Summit consensus, snow level, confidence, primary SNOTEL/CDEC, run-to-run deltas)
- `GET /api/resorts/{resort_id}` — Detailed 168h consensus timeline, individual model breakdowns, local-timezone daily rollups, and station telemetry
- `GET /api/resorts/{resort_id}/history` — Historical SNOTEL/CDEC time series and run-to-run forecast trends
- `POST /api/refresh` — Trigger a live multi-source fetch, physics/consensus run, and SQLite save
