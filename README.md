# Snow Forecast Dashboard

Multi-model ski resort snow forecast engine and dashboard built with public meteorological models, unified snow-density physics, and nearby natural snowpack telemetry.

**Live Site:** https://lun0522.github.io/snow-forecast/

## Target Resorts
- **Northstar California** (North Lake Tahoe, CA)
- **Heavenly Mountain** (South Lake Tahoe, CA)
- **Kirkwood Mountain** (Sierra Crest, CA)
- **Park City Mountain** (Wasatch Back, UT)
- **Keystone Resort** (Summit County, CO)
- **Whistler Blackcomb** (Coast Mountains, BC)

## Public Data Sources
- **Open-Meteo** (`/v1/forecast` & `/v1/elevation`): Multi-model forecasts (`ecmwf_ifs025`, `gfs_global`, `gfs_hrrr`, `ncep_nbm_conus`, `gem_global`, `icon_global`) with Copernicus 90m DEM and elevation downscaling for Base, Mid, and Summit bands.
- **MET Norway Locationforecast 2.0** (`api.met.no`): ECMWF-backed hourly/6h forecast adjusted for exact Base/Mid/Summit altitude.
- **US National Weather Service** (`api.weather.gov`): 2.5 km NDFD/NBM gridpoints (`quantitativePrecipitation`, `snowfallAmount`, `snowLevel`, temperature, wind).
- **USDA NRCS SNOTEL & BC River Forecast Centre ASWS**: Current natural snow base depth, 24h change, and snow water equivalent (SWE) from nearby automated mountain stations.

## Running the Backend

From `backend/` (using the virtual environment):

```bash
# Install dependencies
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt

# Run unit & API tests
.venv/bin/pytest tests -v

# Fetch live data, run snow physics + consensus blending, and store in SQLite (data/snow.db)
.venv/bin/python -m app.scripts.update

# Export static JSON payloads (resorts.json + resorts/<id>.json) for GitHub Pages / static hosting
.venv/bin/python -m app.scripts.update --export-dir ../frontend/public/data

# Reprocess the latest saved snapshot offline (data/latest_snapshot.json)
.venv/bin/python -m app.scripts.update --from-snapshot

# Optional: refresh DEM elevations & NWS gridpoints -> app/resorts.json
.venv/bin/python -m app.scripts.discover_stations

# Optional: fetch raw forecasts -> data/latest_snapshot.json without writing SQLite
.venv/bin/python -m app.scripts.fetch_snapshot

# Start the FastAPI server (port 8000)
.venv/bin/uvicorn app.main:app --reload --port 8000
```

### API Endpoints
- `GET /api/health` — API & latest SQLite forecast run status
- `GET /api/runs` — Recent forecast runs stored in SQLite
- `GET /api/resorts` — Overview summaries for all configured resorts (24h/48h/72h/5d/7d Base/Mid/Summit consensus, snow level, confidence, nearby snowpack depth)
- `GET /api/resorts/{resort_id}` — Detailed 168h consensus timeline, individual model breakdowns, and local-timezone daily rollups
- `POST /api/refresh` — Trigger a live multi-source fetch, physics/consensus run, and SQLite save

## Running the Web UI

With the FastAPI server running on port `8000`, launch the Vite + React dashboard from `frontend/`:

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173` in your browser (`/api/*` requests proxy automatically to `http://127.0.0.1:8000`). Production builds (`npm run build`) automatically read exported static JSON from `data/resorts.json` unless `VITE_DATA_MODE=api` or `VITE_API_BASE` is set.

## Deploying to GitHub Pages (Static + GitHub Actions)

1. Push to `main`.
2. In your GitHub repository: **Settings → Pages → Build and deployment → Source**, choose **GitHub Actions**.
3. Run **Deploy Static Forecast Site to GitHub Pages** (`.github/workflows/deploy.yml`) once from the **Actions** tab, or let it trigger automatically on pushes to `main` and every 4 hours on schedule (`17 */4 * * *` UTC).
4. Each workflow run tests the backend, runs `python -m app.scripts.update --export-dir ../frontend/public/data`, builds Vite in static mode (`VITE_DATA_MODE=static`), and deploys `frontend/dist` to https://lun0522.github.io/snow-forecast/.
