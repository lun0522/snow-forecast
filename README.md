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
- **Step 3:** Custom snow physics (dynamic Kuchera/DGZ SLR, snow level warnings, compaction) & consensus blending
- **Step 4:** SQLite historical store + FastAPI REST API
- **Step 5:** React + Tailwind dashboard UI

## Running Step 1 & Step 2

From `backend/`:

```bash
# Run offline unit tests
python3 -m unittest discover -s tests -v

# Step 1: Discover DEM elevations, NWS gridpoints, and nearest SNOTEL stations -> app/resorts.json
python3 -m app.scripts.discover_stations

# Step 2: Fetch live forecasts & telemetry, print comparison table, save data/latest_snapshot.json
python3 -m app.scripts.fetch_snapshot
```
