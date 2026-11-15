import { useState } from "react";
import { ChevronDown } from "lucide-react";
import { COPY, type Lang } from "../i18n";
import type { BandDetail, WindowKey } from "../types";
import {
  formatElevM,
  formatSnowCm,
  formatSnowCmRange,
  formatTempC,
  formatWindKmh,
} from "../utils/format";

interface ModelComparisonTableProps {
  band: BandDetail;
  lang?: Lang;
}

const MODEL_ORDER = [
  "ecmwf_ifs025",
  "ncep_nbm_conus",
  "gfs_global",
  "gem_global",
  "icon_global",
  "met_no",
  "nws_gridpoints",
  "gfs_hrrr",
];

const WINDOWS: WindowKey[] = ["24h", "48h", "72h", "120h", "168h"];

export function ModelComparisonTable({ band, lang = "zh" }: ModelComparisonTableProps) {
  const [isOpen, setIsOpen] = useState(false);
  const t = COPY[lang].models;
  const models = Object.values(band.models).sort((a, b) => {
    const ia = MODEL_ORDER.indexOf(a.id);
    const ib = MODEL_ORDER.indexOf(b.id);
    return (ia === -1 ? 99 : ia) - (ib === -1 ? 99 : ib);
  });

  const consensus72 = band.windows["72h"];

  return (
    <div
      className={`rounded-xl border bg-white/90 p-4 shadow-xs transition-colors md:p-5 dark:bg-slate-900/65 dark:shadow-none ${
        isOpen
          ? "border-slate-200/90 dark:border-slate-800/90"
          : "border-slate-200/90 hover:border-sky-300 dark:border-slate-800/90 dark:hover:border-sky-500/40"
      }`}
    >
      <button
        type="button"
        aria-expanded={isOpen}
        onClick={() => setIsOpen((prev) => !prev)}
        className={`group flex w-full cursor-pointer items-center justify-between gap-3 text-left transition ${
          isOpen ? "pb-3 border-b border-slate-200/80 dark:border-slate-800/70" : ""
        }`}
      >
        <div>
          <h3 className="text-sm font-semibold text-slate-900 dark:text-white">
            {t.titlePrefix} · {band.label} ({formatElevM(band.elevation_ft, band.elevation_m)})
          </h3>
          <p className="text-xs text-slate-500 dark:text-slate-400">
            {t.subtitle}
          </p>
        </div>
        <span
          className={`inline-flex shrink-0 items-center gap-1.5 rounded-lg border px-3 py-1.5 text-xs font-medium shadow-xs transition ${
            isOpen
              ? "border-slate-300/90 bg-slate-50 text-slate-700 group-hover:bg-slate-100 group-hover:text-slate-900 dark:border-slate-700 dark:bg-slate-800/80 dark:text-slate-200 dark:group-hover:bg-slate-800"
              : "border-sky-300 bg-sky-50 text-sky-700 group-hover:border-sky-400 group-hover:bg-sky-100 group-hover:text-sky-800 dark:border-sky-500/40 dark:bg-sky-500/15 dark:text-sky-200 dark:group-hover:border-sky-400/60 dark:group-hover:bg-sky-500/25"
          }`}
        >
          <span>{isOpen ? t.collapseModels : t.expandModels(models.length)}</span>
          <ChevronDown
            className={`h-4 w-4 transition-transform duration-150 ${isOpen ? "rotate-180" : ""}`}
          />
        </span>
      </button>

      {isOpen && (
        <>
          <div className="mt-3 overflow-x-auto">
        <table className="w-full min-w-[680px] text-left text-xs">
          <thead>
            <tr
              className={`border-b border-slate-200 text-[11px] text-slate-500 dark:border-slate-800 dark:text-slate-400 ${
                lang === "en" ? "uppercase tracking-wider" : ""
              }`}
            >
              <th className="py-2 pr-3 font-medium">{t.colModel}</th>
              <th className="py-2 px-2 font-medium">{t.colHorizon}</th>
              <th className="py-2 px-2 font-medium">{t.col24h}</th>
              <th className="py-2 px-2 font-medium">{t.col48h}</th>
              <th className="py-2 px-2 font-medium">{t.col72h}</th>
              <th className="py-2 px-2 font-medium">{t.col5d}</th>
              <th className="py-2 px-2 font-medium">{t.col7d}</th>
              <th className="py-2 px-2 font-medium">{t.col72hSlr}</th>
              <th className="py-2 pl-2 font-medium text-right">{t.col72hTempWind}</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-200/80 tabular-nums dark:divide-slate-800/60">
            {/* Consensus Pin Row */}
            <tr className="bg-sky-50/90 font-medium text-sky-950 dark:bg-sky-500/8 dark:text-sky-100">
              <td className="py-2.5 pr-3">
                <div className="flex items-center gap-2">
                  <span className="h-2 w-2 rounded-full bg-sky-500 dark:bg-sky-400" />
                  <span>{t.consensusMedian}</span>
                </div>
                <div className="pl-4 text-[10px] font-normal text-slate-500 dark:text-slate-400">
                  {t.minMaxSpread}
                </div>
              </td>
              <td className="py-2.5 px-2 text-slate-500 dark:text-slate-400">168h</td>
              {WINDOWS.map((wk) => {
                const w = band.windows[wk];
                return (
                  <td key={wk} className="py-2.5 px-2">
                    <div className="font-semibold text-sky-700 dark:text-sky-300">
                      {formatSnowCm(w?.snow_median_in)}
                    </div>
                    {w && (
                      <div className="whitespace-nowrap text-[10px] font-normal text-slate-500 dark:text-slate-400">
                        {formatSnowCmRange(w.snow_min_in, w.snow_max_in)}
                      </div>
                    )}
                  </td>
                );
              })}
              <td className="py-2.5 px-2 text-slate-700 dark:text-slate-300">
                {consensus72 ? `${consensus72.avg_slr.toFixed(1)}:1` : "—"}
              </td>
              <td className="py-2.5 pl-2 text-right text-slate-700 dark:text-slate-300">
                {formatTempC(consensus72?.temp_min_f)}/
                {formatTempC(consensus72?.temp_max_f)} ·{" "}
                {formatWindKmh(consensus72?.max_wind_mph)}
              </td>
            </tr>

            {models.map((m) => {
              const rawKey: WindowKey = m.coverage_hours >= 148 ? "168h" : m.coverage_hours >= 64 ? "72h" : "24h";
              const rawLabel = rawKey === "168h" ? "7d" : rawKey;
              const rawVal = m.windows[rawKey]?.native_snow_in ?? 0;
              const slrRef = m.coverage_hours >= 64 ? m.windows["72h"] : m.windows["24h"];

              return (
                <tr key={m.id} className="hover:bg-slate-50 dark:hover:bg-slate-800/35">
                  <td className="py-2 pr-3">
                    <div className="font-medium text-slate-900 dark:text-slate-200">{m.display_name}</div>
                    <div className="text-[10px] text-slate-500">
                      {t.rawNativePrefix} ({rawLabel}): {formatSnowCm(rawVal)}
                    </div>
                  </td>
                  <td className="py-2 px-2">
                    <span
                      className={`rounded border px-1.5 py-0.5 text-[10px] ${
                        m.coverage_hours < 72
                          ? "border-amber-300 bg-amber-100/80 text-amber-800 dark:border-amber-500/30 dark:bg-amber-500/10 dark:text-amber-300"
                          : "border-slate-300 bg-slate-100 text-slate-700 dark:border-slate-700 dark:bg-slate-950/60 dark:text-slate-300"
                      }`}
                    >
                      {m.coverage_hours}h
                    </span>
                  </td>
                  {WINDOWS.map((wk) => {
                    const winSnow = m.windows[wk]?.physics_snow_in;
                    const beyondHorizon =
                      (wk === "48h" && m.coverage_hours < 40) ||
                      (wk === "72h" && m.coverage_hours < 64) ||
                      (wk === "120h" && m.coverage_hours < 105) ||
                      (wk === "168h" && m.coverage_hours < 148);
                    return (
                      <td
                        key={wk}
                        className={`py-2 px-2 ${beyondHorizon ? "text-slate-400 dark:text-slate-600" : "text-slate-800 dark:text-slate-200"}`}
                        title={beyondHorizon ? t.stopsAtTitle(m.coverage_hours) : undefined}
                      >
                        {beyondHorizon ? "—" : formatSnowCm(winSnow)}
                      </td>
                    );
                  })}
                  <td className="py-2 px-2 text-slate-700 dark:text-slate-300">
                    {slrRef ? `${slrRef.avg_slr.toFixed(1)}:1` : "—"}
                  </td>
                  <td className="py-2 pl-2 text-right text-slate-500 dark:text-slate-400">
                    {formatTempC(slrRef?.temp_min_f)}/
                    {formatTempC(slrRef?.temp_max_f)} ·{" "}
                    {formatWindKmh(slrRef?.max_wind_mph)}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      <div className="mt-4 border-t border-slate-200/80 pt-3 dark:border-slate-800/70">
        <div className="text-[11px] font-semibold text-slate-600 dark:text-slate-300">
          {t.modelGuideTitle}
        </div>
        <dl className="mt-2 space-y-1.5 text-[11px] leading-relaxed text-slate-600 dark:text-slate-400">
          {models.map((m) => {
            const desc = t.modelDescriptions[m.id];
            if (!desc) return null;
            return (
              <div key={m.id}>
                <dt className="inline font-medium text-slate-800 dark:text-slate-200">
                  {m.display_name}:{" "}
                </dt>
                <dd className="inline">{desc}</dd>
              </div>
            );
          })}
        </dl>
      </div>
        </>
      )}
    </div>
  );
}
