import { COPY, type Lang } from "../i18n";
import type { CurrentSnowpack } from "../types";
import { formatLocalHourTick } from "../utils/format";
import { TermTooltip } from "./TermTooltip";

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
    <div className="rounded-xl border border-slate-200/90 bg-white/90 p-4 shadow-xs md:p-5 dark:border-slate-800/90 dark:bg-slate-900/65 dark:shadow-none">
      <div className="flex flex-wrap items-baseline gap-2 border-b border-slate-200/80 pb-3 dark:border-slate-800/70">
        <h3 className="text-sm font-semibold text-slate-900 dark:text-white">
          {t.title}
        </h3>
        <span className="text-xs text-slate-500 dark:text-slate-400">
          · {t.subtitle}
        </span>
      </div>

      {snowpack.status === "ok" && snowpack.stations.length > 0 ? (
        <div className="mt-3 overflow-x-auto">
          <table className="w-full min-w-[600px] text-left text-xs">
            <thead>
              <tr
                className={`border-b border-slate-200 text-[11px] text-slate-500 dark:border-slate-800 dark:text-slate-400 ${
                  lang === "en" ? "uppercase tracking-wider" : ""
                }`}
              >
                <th className="py-2 pr-3 font-medium">{t.colStation}</th>
                <th className="py-2 px-3 font-medium">{t.colElevation}</th>
                <th className="py-2 px-3 font-medium">{t.colDistance}</th>
                <th className="py-2 px-3 font-medium">{t.colBaseDepth}</th>
                <th className="py-2 px-3 font-medium">{t.colChange24h}</th>
                <th className="py-2 px-3 font-medium">
                  <TermTooltip label={t.colSwe} tooltip={t.sweTooltip} />
                </th>
                <th className="py-2 pl-3 font-medium">{t.colObserved}</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200/80 tabular-nums dark:divide-slate-800/60">
              {snowpack.stations.map((st) => {
                const delta = st.delta_24h_cm;
                const hasSignificantDelta = delta !== null && Math.abs(delta) >= 0.5;
                return (
                  <tr
                    key={st.id}
                    className="transition hover:bg-slate-50 dark:hover:bg-slate-800/35"
                  >
                    <td
                      title={st.id}
                      className="py-2 pr-3 font-medium text-slate-900 dark:text-slate-100"
                    >
                      {st.name}
                    </td>
                    <td className="py-2 px-3 text-slate-700 dark:text-slate-300">
                      {Math.round(st.elevation_m).toLocaleString()} m
                    </td>
                    <td className="py-2 px-3 text-slate-600 dark:text-slate-400">
                      {st.distance_km.toFixed(1)} km
                    </td>
                    <td className="py-2 px-3 font-semibold text-sky-700 dark:text-sky-300">
                      {st.snow_depth_cm.toFixed(1)} cm
                    </td>
                    <td className="py-2 px-3">
                      {hasSignificantDelta ? (
                        <span
                          className={`inline-block whitespace-nowrap rounded px-1.5 py-0.5 text-[11px] font-medium ${
                            delta > 0
                              ? "bg-sky-100 text-sky-800 dark:bg-sky-500/15 dark:text-sky-300"
                              : "bg-amber-100 text-amber-800 dark:bg-amber-500/15 dark:text-amber-300"
                          }`}
                        >
                          {delta > 0 ? `+${delta.toFixed(1)}` : delta.toFixed(1)} cm
                        </span>
                      ) : delta !== null ? (
                        <span className="text-slate-500 dark:text-slate-400">0.0 cm</span>
                      ) : (
                        <span className="text-slate-400 dark:text-slate-500">—</span>
                      )}
                    </td>
                    <td className="py-2 px-3 text-slate-700 dark:text-slate-300">
                      {st.swe_mm !== null ? `${st.swe_mm.toFixed(0)} mm` : "—"}
                    </td>
                    <td className="py-2 pl-3 text-slate-600 dark:text-slate-400">
                      {formatLocalHourTick(st.observed_at_utc, timezone, true)}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      ) : (
        <p
          title={snowpack.error || undefined}
          className="mt-2.5 text-xs text-slate-500 dark:text-slate-400"
        >
          {t.unavailable}
        </p>
      )}
    </div>
  );
}
