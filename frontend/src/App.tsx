import { useCallback, useEffect, useState } from "react";
import { AlertCircle, ArrowDownRight, ArrowUpRight, CloudSnow, Layers, RefreshCw } from "lucide-react";
import { fetchResortDetail, fetchResorts, refreshForecasts } from "./api";
import { DailyConsensusChart } from "./components/DailyConsensusChart";
import { HourlyMeteogram } from "./components/HourlyMeteogram";
import { ModelComparisonTable } from "./components/ModelComparisonTable";
import type { BandKey, ForecastRunMeta, ResortDetail, ResortSummary } from "./types";
import {
  formatDeltaSnowCm,
  formatElevM,
  formatSnowCm,
  formatUtcTimestamp,
} from "./utils/format";

export function App() {
  const [runMeta, setRunMeta] = useState<ForecastRunMeta | null>(null);
  const [summaries, setSummaries] = useState<ResortSummary[]>([]);
  const [selectedResortId, setSelectedResortId] = useState<string>("kirkwood");
  const [selectedBand, setSelectedBand] = useState<BandKey>("summit");

  const [detail, setDetail] = useState<ResortDetail | null>(null);

  const [loadingOverview, setLoadingOverview] = useState<boolean>(true);
  const [loadingDetail, setLoadingDetail] = useState<boolean>(false);
  const [refreshing, setRefreshing] = useState<boolean>(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const loadOverview = useCallback(async () => {
    setLoadingOverview(true);
    setErrorMsg(null);
    try {
      const data = await fetchResorts();
      setRunMeta(data.run);
      setSummaries(data.resorts);
      setSelectedResortId((curr) =>
        data.resorts.length > 0 && !data.resorts.some((r) => r.id === curr) ? data.resorts[0].id : curr,
      );
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : "Failed to load resort forecasts");
    } finally {
      setLoadingOverview(false);
    }
  }, []);

  useEffect(() => {
    void loadOverview();
  }, [loadOverview]);

  // Fetch detailed resort forecast whenever selection or latest run changes
  useEffect(() => {
    if (!selectedResortId || summaries.length === 0) return;
    let cancelled = false;
    setLoadingDetail(true);

    fetchResortDetail(selectedResortId)
      .then((res) => {
        if (!cancelled) {
          setDetail(res);
        }
      })
      .catch((err) => {
        if (!cancelled) {
          setErrorMsg(err instanceof Error ? err.message : "Failed to load resort details");
        }
      })
      .finally(() => {
        if (!cancelled) setLoadingDetail(false);
      });

    return () => {
      cancelled = true;
    };
  }, [selectedResortId, runMeta?.id, summaries.length]);

  const handleRefresh = async () => {
    setRefreshing(true);
    setErrorMsg(null);
    try {
      await refreshForecasts();
      const data = await fetchResorts();
      setRunMeta(data.run);
      setSummaries(data.resorts);
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : "Forecast refresh failed");
    } finally {
      setRefreshing(false);
    }
  };

  const activeSummary = summaries.find((s) => s.id === selectedResortId) ?? null;
  const activeBand = detail?.bands[selectedBand] ?? null;
  const runDelta72 = activeSummary?.run_delta?.summit_72h_in;

  return (
    <div className="min-h-screen text-slate-100">
      {/* Top Command Header */}
      <header className="sticky top-0 z-30 border-b border-slate-800/80 bg-[#090F18]/90 backdrop-blur-md">
        <div className="mx-auto flex max-w-[1440px] flex-wrap items-center justify-between gap-3 px-4 py-3 md:px-6">
          <div className="flex flex-wrap items-center gap-3.5">
            <div className="flex items-center gap-3">
              <div className="flex h-9 w-9 items-center justify-center rounded-lg border border-sky-400/30 bg-sky-500/15 text-sky-300">
                <CloudSnow className="h-5 w-5" />
              </div>
              <div>
                <h1 className="text-base font-bold tracking-tight text-white">
                  PowderConsensus
                </h1>
                <p className="text-[11px] text-slate-400">
                  {runMeta
                    ? `Updated ${formatUtcTimestamp(runMeta.fetched_at_utc, detail?.timezone ?? "America/Los_Angeles")}`
                    : "Public multi-model snow forecast workstation"}
                </p>
              </div>
            </div>

            {summaries.length > 0 && (
              <select
                aria-label="Select ski resort"
                value={selectedResortId}
                onChange={(e) => setSelectedResortId(e.target.value)}
                className="cursor-pointer rounded-lg border border-sky-400/40 bg-slate-950/90 px-3 py-1.5 text-sm font-semibold text-white shadow-sm transition hover:border-sky-400/70 focus:border-sky-400 focus:outline-none focus:ring-1 focus:ring-sky-400/40"
              >
                {summaries.map((resort) => (
                  <option key={resort.id} value={resort.id} className="bg-slate-950 text-slate-100">
                    {resort.name} ({resort.region}, {resort.state})
                  </option>
                ))}
              </select>
            )}
          </div>

          <div className="flex flex-wrap items-center gap-2.5">
            {/* Live Refresh Action */}
            <button
              type="button"
              disabled={refreshing}
              onClick={handleRefresh}
              className="inline-flex items-center gap-1.5 rounded-lg border border-sky-400/40 bg-sky-500/15 px-3 py-1.5 text-xs font-semibold text-sky-200 transition hover:bg-sky-500/25 disabled:cursor-not-allowed disabled:opacity-50"
            >
              <RefreshCw className={`h-3.5 w-3.5 ${refreshing ? "animate-spin" : ""}`} />
              {refreshing ? "Refreshing Live Models..." : "Refresh Live Data"}
            </button>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-[1440px] space-y-6 px-4 py-6 md:px-6">
        {errorMsg && (
          <div className="flex items-center gap-2.5 rounded-xl border border-rose-500/40 bg-rose-500/10 px-4 py-3 text-xs text-rose-200">
            <AlertCircle className="h-4 w-4 shrink-0 text-rose-400" />
            <span>{errorMsg}</span>
          </div>
        )}

        {loadingOverview ? (
          <div className="rounded-xl border border-slate-800 bg-slate-900/50 p-10 text-center text-sm text-slate-400">
            Loading forecast data from SQLite...
          </div>
        ) : summaries.length === 0 ? (
          <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-10 text-center space-y-3">
            <h2 className="text-base font-semibold text-white">No Forecast Runs Stored Yet</h2>
            <p className="text-xs text-slate-400">
              Click <strong>Refresh Live Data</strong> above or run{" "}
              <code className="rounded bg-slate-950 px-1.5 py-0.5 text-sky-300">
                python -m app.scripts.update
              </code>{" "}
              to ingest live weather models and populate the dashboard.
            </p>
          </div>
        ) : (
          <>
            {/* Selected Resort Deep-Dive Workstation */}
            {detail && activeBand && (
              <section className="space-y-5">
                {/* Resort Deep-Dive Header + Band Picker */}
                <div className="rounded-xl border border-slate-800/90 bg-slate-900/75 p-4 md:p-5">
                  <div className="flex flex-wrap items-center justify-between gap-3">
                    <div>
                      <div className="flex flex-wrap items-center gap-2.5">
                        <h2 className="text-xl font-bold text-white">{detail.name}</h2>
                        <span className="rounded-md border border-slate-700 bg-slate-950 px-2 py-0.5 text-xs text-slate-300">
                          {detail.region}, {detail.state} · {detail.timezone}
                        </span>
                        {runDelta72 != null && (
                          <span
                            className={`inline-flex items-center gap-0.5 rounded-md border px-2 py-0.5 text-xs font-medium tabular-nums ${
                              runDelta72 > 0.2
                                ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-300"
                                : runDelta72 < -0.2
                                  ? "border-rose-500/30 bg-rose-500/10 text-rose-300"
                                  : "border-slate-700 bg-slate-950 text-slate-400"
                            }`}
                          >
                            {runDelta72 >= 0 ? (
                              <ArrowUpRight className="h-3.5 w-3.5" />
                            ) : (
                              <ArrowDownRight className="h-3.5 w-3.5" />
                            )}
                            {formatDeltaSnowCm(runDelta72)} 72h vs prev run
                          </span>
                        )}
                        {loadingDetail && (
                          <span className="text-xs text-sky-300">Syncing band details...</span>
                        )}
                      </div>
                      <p className="mt-1 text-xs text-slate-400">
                        Viewing <strong className="text-slate-200">{activeBand.label}</strong> band at{" "}
                        <strong className="tabular-nums text-slate-200">
                          {formatElevM(activeBand.elevation_ft, activeBand.elevation_m)}
                        </strong>
                      </p>
                    </div>

                    {/* Elevation Band Selector Tabs */}
                    <div className="flex flex-wrap items-center gap-2">
                      <Layers className="h-4 w-4 text-slate-400" />
                      {(["base", "mid", "summit"] as BandKey[]).map((bk) => {
                        const band = detail.bands[bk];
                        if (!band) return null;
                        const active = bk === selectedBand;
                        return (
                          <button
                            key={bk}
                            type="button"
                            onClick={() => setSelectedBand(bk)}
                            className={`rounded-lg border px-3 py-1.5 text-left transition ${
                              active
                                ? "border-sky-400/70 bg-sky-500/15 text-white"
                                : "border-slate-800 bg-slate-950/60 text-slate-400 hover:border-slate-700 hover:text-slate-200"
                            }`}
                          >
                            <div className="text-[11px] font-semibold uppercase tracking-wider">
                              {bk}
                            </div>
                            <div className="tabular-nums text-xs text-slate-300">
                              {formatElevM(band.elevation_ft, band.elevation_m)} · 72h{" "}
                              <span className="text-sky-300 font-semibold">
                                {formatSnowCm(band.windows["72h"]?.snow_median_in)}
                              </span>
                            </div>
                          </button>
                        );
                      })}
                    </div>
                  </div>
                </div>

                {/* Daily 7-Day Consensus Bar + Spread Chart & Local Day Table */}
                <DailyConsensusChart
                  daily={activeBand.daily}
                  elevationFt={activeBand.elevation_ft}
                  elevationM={activeBand.elevation_m}
                  bandLabel={activeBand.label}
                />

                {/* Interactive Hourly Meteogram + Snow Level vs Bands */}
                <HourlyMeteogram
                  hourly={activeBand.hourly}
                  timezone={detail.timezone}
                  bandLabel={activeBand.label}
                  baseElevFt={detail.bands.base?.elevation_ft ?? activeBand.elevation_ft}
                  midElevFt={detail.bands.mid?.elevation_ft ?? activeBand.elevation_ft}
                  summitElevFt={detail.bands.summit?.elevation_ft ?? activeBand.elevation_ft}
                />

                {/* 8-Source Multi-Model Matrix */}
                <ModelComparisonTable band={activeBand} />
              </section>
            )}
          </>
        )}
      </main>
    </div>
  );
}

export default App;
