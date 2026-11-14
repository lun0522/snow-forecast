import { COPY, type Lang } from "../i18n";
import type { CurrentSnowpack } from "../types";
import { formatLocalHourTick } from "../utils/format";

interface SnowpackPanelProps {
  snowpack: CurrentSnowpack | null | undefined;
  timezone: string;
  lang?: Lang;
}

export function SnowpackPanel({ snowpack, timezone, lang = "zh" }: SnowpackPanelProps) {
  if (!snowpack) {
    return null;
  }
  const t = COPY[lang].snowpack;

  return (
    <div className="rounded-xl border border-slate-200/90 bg-white/90 px-4 py-3.5 shadow-xs md:px-5 dark:border-slate-800/90 dark:bg-slate-900/65 dark:shadow-none">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <div className="flex flex-wrap items-baseline gap-2">
          <h3 className="text-sm font-semibold text-slate-900 dark:text-white">
            {t.title}
          </h3>
          <span className="text-xs text-slate-500 dark:text-slate-400">
            · {t.subtitle}
          </span>
        </div>
      </div>

      {snowpack.status === "ok" && snowpack.stations.length > 0 ? (
        <div className="mt-2.5 grid grid-cols-1 gap-2.5 sm:grid-cols-2 lg:grid-cols-3">
          {snowpack.stations.map((st) => {
            const delta = st.delta_24h_cm;
            const hasDelta = delta !== null && Math.abs(delta) >= 0.5;
            return (
              <div
                key={st.id}
                className="flex items-center justify-between gap-3 rounded-lg border border-slate-200/90 bg-slate-50/90 px-3 py-2 dark:border-slate-800/80 dark:bg-slate-950/60"
              >
                <div className="min-w-0">
                  <div className="truncate text-xs font-medium text-slate-900 dark:text-slate-100">
                    {st.name}
                  </div>
                  <div className="mt-0.5 text-[11px] text-slate-500 tabular-nums dark:text-slate-400">
                    {Math.round(st.elevation_m).toLocaleString()} m · {st.distance_km.toFixed(1)} km ·{" "}
                    {formatLocalHourTick(st.observed_at_utc, timezone, true)}
                  </div>
                </div>

                <div className="shrink-0 text-right tabular-nums">
                  <div className="flex items-baseline justify-end gap-1.5">
                    <span className="text-sm font-semibold text-sky-700 dark:text-sky-300">
                      {st.snow_depth_cm.toFixed(1)} cm
                    </span>
                    {hasDelta && (
                      <span
                        className={`rounded px-1 py-0.5 text-[10px] font-medium ${
                          delta > 0
                            ? "bg-sky-100 text-sky-800 dark:bg-sky-500/15 dark:text-sky-300"
                            : "bg-amber-100 text-amber-800 dark:bg-amber-500/15 dark:text-amber-300"
                        }`}
                      >
                        {delta > 0 ? `+${delta.toFixed(1)}` : delta.toFixed(1)} 24h
                      </span>
                    )}
                  </div>
                  <div className="mt-0.5 text-[11px] text-slate-500 dark:text-slate-400">
                    {st.swe_mm !== null ? `${st.swe_mm.toFixed(0)} mm ${t.sweUnit}` : st.id}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      ) : (
        <p className="mt-2 text-xs text-slate-500">
          {snowpack.error || t.unavailable}
        </p>
      )}
    </div>
  );
}
