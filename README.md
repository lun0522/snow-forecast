# Snow Forecast Dashboard

Personal ski resort snow forecast engine and dashboard using public meteorological models.

## Target Resorts
- **Northstar California** (North Tahoe, CA)
- **Heavenly Mountain** (South Tahoe, CA/NV)
- **Kirkwood Mountain** (Sierra Crest, CA)
- **Park City Mountain** (Wasatch Back, UT)
- **Keystone Resort** (Summit County, CO)
- **Whistler Blackcomb** (Coast Mountains, BC)

## Public Data Sources
- **Open-Meteo** (`/v1/forecast` & `/v1/elevation`): Multi-model forecasts (`ecmwf_ifs025`, `gfs_global`, `gfs_hrrr`, `ncep_nbm_conus`, `gem_global`, `icon_global`) with Copernicus 90m DEM and elevation lapse-rate downscaling for Base, Mid, and Summit bands (gracefully skipped if unreachable).
- **MET Norway Locationforecast 2.0** (`api.met.no`): Global ECMWF-backed hourly/6h forecast adjusted for exact Base/Mid/Summit `altitude`.
- **US National Weather Service** (`api.weather.gov`): 2.5 km NDFD/NBM gridpoints (`quantitativePrecipitation`, `snowfallAmount`, `snowLevel`, temperature, wind).

## Roadmap
- **Step 1 (Done):** Resort registry (`backend/app/resorts.json`) + DEM & NWS grid discovery (`discover_stations.py`)
- **Step 2 (Done):** Multi-model, MET Norway, and NWS ingestion (`fetch_snapshot.py`)
- **Step 3 (Done):** Custom snow physics (wet-bulb partitioning, dynamic SLR + wind compaction, storm settling) & consensus blending (`app/engine/`)
- **Step 4 (Done):** SQLite store (`data/snow.db`) + FastAPI REST API (`app/main.py`) + refresh pipeline (`app/scripts/update.py`)
- **Step 5 (Done):** React + TypeScript + Tailwind dashboard UI (`frontend/`)

## Running the Backend (Steps 1–4)

From `backend/` (using the virtual environment):

```bash
# Install dependencies
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt

# Run unit & API tests
.venv/bin/pytest tests -v

# Step 1: Discover DEM elevations & NWS gridpoints -> app/resorts.json
.venv/bin/python -m app.scripts.discover_stations

# Step 2: Fetch raw forecasts -> data/latest_snapshot.json
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
- `GET /api/resorts` — Overview summaries for all configured resorts (24h/48h/72h/5d/7d Base/Mid/Summit consensus, snow level, confidence, run-to-run deltas)
- `GET /api/resorts/{resort_id}` — Detailed 168h consensus timeline, individual model breakdowns, and local-timezone daily rollups
- `POST /api/refresh` — Trigger a live multi-source fetch, physics/consensus run, and SQLite save


## Running the Web UI (Step 5)

With the FastAPI server running on port `8000`, launch the Vite + React dashboard from `frontend/`:

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173` in your browser (`/api/*` requests proxy automatically to `http://127.0.0.1:8000`).
