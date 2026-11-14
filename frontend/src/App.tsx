import { useCallback, useEffect, useState } from "react";
import { AlertCircle, Clock, Moon, Sun } from "lucide-react";
import { fetchResortDetail, fetchResorts } from "./api";
import { DailyConsensusChart } from "./components/DailyConsensusChart";
import { HourlyMeteogram } from "./components/HourlyMeteogram";
import { ModelComparisonTable } from "./components/ModelComparisonTable";
import { SnowpackPanel } from "./components/SnowpackPanel";
import { COPY, LANG_STORAGE_KEY, type Lang } from "./i18n";
import type { BandKey, ForecastRunMeta, ResortDetail, ResortSummary } from "./types";
import { formatElevM, formatLastUpdated } from "./utils/format";

type Theme = "light" | "dark";
const THEME_STORAGE_KEY = "powderconsensus-theme";

function readInitialTheme(): Theme {
  try {
    const saved = window.localStorage.getItem(THEME_STORAGE_KEY);
    if (saved === "dark" || saved === "light") {
      return saved;
    }
  } catch {
    // Ignore storage access errors in sandboxed contexts.
  }
  return "light";
}

function readInitialLang(): Lang {
  try {
    const saved = window.localStorage.getItem(LANG_STORAGE_KEY);
    if (saved === "en" || saved === "zh") {
      return saved;
    }
  } catch {
    // Ignore storage access errors in sandboxed contexts.
  }
  return "zh";
}

export function App() {
  const [theme, setTheme] = useState<Theme>(readInitialTheme);
  const isDark = theme === "dark";
  const [lang, setLang] = useState<Lang>(readInitialLang);
  const t = COPY[lang];

  const [runMeta, setRunMeta] = useState<ForecastRunMeta | null>(null);
  const [summaries, setSummaries] = useState<ResortSummary[]>([]);
  const [selectedResortId, setSelectedResortId] = useState<string>("kirkwood");
  const [selectedBand, setSelectedBand] = useState<BandKey>("summit");

  const [detail, setDetail] = useState<ResortDetail | null>(null);

  const [loadingOverview, setLoadingOverview] = useState<boolean>(true);
  const [loadingDetail, setLoadingDetail] = useState<boolean>(false);
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
    document.documentElement.classList.toggle("dark", isDark);
    try {
      window.localStorage.setItem(THEME_STORAGE_KEY, theme);
    } catch {
      // Ignore storage access errors in sandboxed contexts.
    }
  }, [isDark, theme]);

  useEffect(() => {
    document.documentElement.lang = lang === "zh" ? "zh-CN" : "en";
    try {
      window.localStorage.setItem(LANG_STORAGE_KEY, lang);
    } catch {
      // Ignore storage access errors in sandboxed contexts.
    }
  }, [lang]);

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

  const activeSummary = summaries.find((s) => s.id === selectedResortId) ?? null;
  const activeBand = detail?.bands[selectedBand] ?? null;
  const bandOptionsSource = detail?.bands ?? activeSummary?.bands;

  return (
    <div className="min-h-screen text-slate-900 dark:text-slate-100">
      {/* Top Control Header */}
      <header className="sticky top-0 z-30 border-b border-slate-200/90 bg-white/85 backdrop-blur-md dark:border-slate-800/80 dark:bg-[#090F18]/90">
        <div className="mx-auto flex max-w-[1440px] flex-wrap items-center justify-between gap-3 px-4 py-2.5 md:px-6">
          <div className="flex flex-wrap items-center gap-3">
            {summaries.length > 0 && (
              <select
                aria-label={t.header.selectResort}
                value={selectedResortId}
                onChange={(e) => setSelectedResortId(e.target.value)}
                className="cursor-pointer rounded-lg border border-sky-500/40 bg-white px-3 py-1.5 text-sm font-semibold text-slate-900 shadow-xs transition hover:border-sky-600/60 focus:border-sky-500 focus:outline-none focus:ring-1 focus:ring-sky-500/35 dark:border-sky-400/40 dark:bg-slate-950/90 dark:text-white dark:shadow-sm dark:hover:border-sky-400/70 dark:focus:border-sky-400 dark:focus:ring-sky-400/40"
              >
                {summaries.map((resort) => (
                  <option
                    key={resort.id}
                    value={resort.id}
                    className="bg-white text-slate-900 dark:bg-slate-950 dark:text-slate-100"
                  >
                    {resort.name} ({resort.region}, {resort.state})
                  </option>
                ))}
              </select>
            )}

            {/* Elevation Band Selector */}
            {bandOptionsSource && (
              <div className="inline-flex items-center rounded-lg border border-slate-200 bg-slate-100/90 p-0.5 dark:border-slate-800 dark:bg-slate-950/80">
                {(["base", "mid", "summit"] as BandKey[]).map((bk) => {
                  const band = bandOptionsSource[bk];
                  if (!band) return null;
                  const active = bk === selectedBand;
                  const explicitM = detail?.bands[bk]?.elevation_m ?? null;
                  return (
                    <button
                      key={bk}
                      type="button"
                      onClick={() => setSelectedBand(bk)}
                      className={`inline-flex items-center gap-1.5 rounded-md px-2.5 py-1 text-xs transition ${
                        active
                          ? "bg-white text-slate-900 font-semibold shadow-xs ring-1 ring-slate-200/80 dark:bg-sky-500/20 dark:text-white dark:ring-0"
                          : "text-slate-600 hover:text-slate-900 dark:text-slate-400 dark:hover:text-slate-200"
                      }`}
                    >
                      <span className={lang === "en" ? "uppercase tracking-wider" : ""}>
                        {t.header.bands[bk]}
                      </span>
                      <span
                        className={`tabular-nums text-[11px] ${
                          active ? "text-sky-700 dark:text-slate-300/90" : "text-slate-500 dark:text-slate-400"
                        }`}
                      >
                        {formatElevM(band.elevation_ft, explicitM)}
                      </span>
                    </button>
                  );
                })}
              </div>
            )}
          </div>

          <div className="flex flex-wrap items-center gap-2.5">
            {loadingDetail && (
              <span className="text-xs text-sky-700 dark:text-sky-300">{t.header.syncing}</span>
            )}
            <div
              title={runMeta?.fetched_at_utc ? `Fetched UTC: ${runMeta.fetched_at_utc}` : undefined}
              className="inline-flex items-center gap-1.5 rounded-lg border border-slate-200/90 bg-slate-50 px-2.5 py-1.5 text-xs text-slate-600 dark:border-slate-800 dark:bg-slate-900/70 dark:text-slate-300"
            >
              <Clock className="h-3.5 w-3.5 shrink-0 text-slate-500 dark:text-slate-400" />
              <span className="text-slate-500 dark:text-slate-400">{t.header.lastUpdated}</span>
              <span className="font-medium tabular-nums text-slate-800 dark:text-slate-100">
                {formatLastUpdated(runMeta?.fetched_at_utc)}
              </span>
            </div>
            <div
              role="group"
              aria-label={t.header.switchLanguage}
              title={t.header.switchLanguage}
              className="inline-flex items-center rounded-lg border border-slate-300/90 bg-slate-100/90 p-0.5 text-xs shadow-xs dark:border-slate-700/80 dark:bg-slate-950/80"
            >
              {(
                [
                  { code: "zh" as const, label: "中" },
                  { code: "en" as const, label: "EN" },
                ] as const
              ).map(({ code, label }) => {
                const active = lang === code;
                return (
                  <button
                    key={code}
                    type="button"
                    aria-pressed={active}
                    onClick={() => setLang(code)}
                    className={`rounded-md px-2 py-1 transition ${
                      active
                        ? "bg-white font-semibold text-sky-700 shadow-xs ring-1 ring-slate-200/80 dark:bg-sky-500/20 dark:text-sky-200 dark:ring-0"
                        : "text-slate-600 hover:text-slate-900 dark:text-slate-400 dark:hover:text-slate-200"
                    }`}
                  >
                    {label}
                  </button>
                );
              })}
            </div>
            <button
              type="button"
              onClick={() => setTheme((prev) => (prev === "dark" ? "light" : "dark"))}
              aria-label={isDark ? t.header.switchToLight : t.header.switchToDark}
              title={isDark ? t.header.switchToLight : t.header.switchToDark}
              className="inline-flex items-center justify-center rounded-lg border border-slate-300/90 bg-white p-1.5 text-slate-700 shadow-xs transition hover:border-slate-400 hover:bg-slate-100 hover:text-slate-900 dark:border-slate-700/80 dark:bg-slate-900/80 dark:text-slate-300 dark:hover:border-slate-600 dark:hover:bg-slate-800 dark:hover:text-white"
            >
              {isDark ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
            </button>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-[1440px] space-y-6 px-4 py-6 md:px-6">
        {errorMsg && (
          <div className="flex items-center gap-2.5 rounded-xl border border-rose-300 bg-rose-50 px-4 py-3 text-xs text-rose-800 dark:border-rose-500/40 dark:bg-rose-500/10 dark:text-rose-200">
            <AlertCircle className="h-4 w-4 shrink-0 text-rose-600 dark:text-rose-400" />
            <span>{errorMsg}</span>
          </div>
        )}

        {loadingOverview ? (
          <div className="rounded-xl border border-slate-200 bg-white/80 p-10 text-center text-sm text-slate-600 shadow-xs dark:border-slate-800 dark:bg-slate-900/50 dark:text-slate-400 dark:shadow-none">
            {t.header.loadingData}
          </div>
        ) : summaries.length === 0 ? (
          <div className="rounded-xl border border-slate-200 bg-white/90 p-10 text-center space-y-3 shadow-xs dark:border-slate-800 dark:bg-slate-900/60 dark:shadow-none">
            <h2 className="text-base font-semibold text-slate-900 dark:text-white">
              {t.header.emptyTitle}
            </h2>
            <p className="text-xs text-slate-600 dark:text-slate-400">
              {t.header.emptyDescPrefix}
              <code className="rounded bg-slate-100 px-1.5 py-0.5 text-sky-700 dark:bg-slate-950 dark:text-sky-300">
                python -m app.scripts.update
              </code>
              {t.header.emptyDescMid}
            </p>
          </div>
        ) : (
          <>
            {/* Selected Resort Deep-Dive Workstation */}
            {detail && activeBand && (
              <section className="space-y-5">
                <SnowpackPanel
                  snowpack={detail.current_snowpack}
                  timezone={detail.timezone}
                  lang={lang}
                />

                {/* Daily 7-Day Consensus Bar + Spread Chart & Local Day Table */}
                <DailyConsensusChart
                  daily={activeBand.daily}
                  elevationFt={activeBand.elevation_ft}
                  elevationM={activeBand.elevation_m}
                  bandLabel={activeBand.label}
                  isDark={isDark}
                  lang={lang}
                />

                {/* Interactive Hourly Meteogram + Snow Level vs Bands */}
                <HourlyMeteogram
                  hourly={activeBand.hourly}
                  timezone={detail.timezone}
                  bandLabel={activeBand.label}
                  baseElevFt={detail.bands.base?.elevation_ft ?? activeBand.elevation_ft}
                  midElevFt={detail.bands.mid?.elevation_ft ?? activeBand.elevation_ft}
                  summitElevFt={detail.bands.summit?.elevation_ft ?? activeBand.elevation_ft}
                  isDark={isDark}
                  lang={lang}
                />

                {/* 8-Source Multi-Model Matrix */}
                <ModelComparisonTable band={activeBand} lang={lang} />
              </section>
            )}
          </>
        )}
      </main>
    </div>
  );
}

export default App;
