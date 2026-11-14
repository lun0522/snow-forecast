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

export function ModelComparisonTable({ band }: ModelComparisonTableProps) {
  const models = Object.values(band.models).sort((a, b) => {
    const ia = MODEL_ORDER.indexOf(a.id);
    const ib = MODEL_ORDER.indexOf(b.id);
    return (ia === -1 ? 99 : ia) - (ib === -1 ? 99 : ib);
  });

  const consensus72 = band.windows["72h"];

  return (
    <div className="rounded-xl border border-slate-200/90 bg-white/90 p-4 shadow-xs md:p-5 dark:border-slate-800/90 dark:bg-slate-900/65 dark:shadow-none">
      <div className="pb-3 border-b border-slate-200/80 dark:border-slate-800/70">
        <h3 className="text-sm font-semibold text-slate-900 dark:text-white">
          Multi-Model Spread Matrix · {band.label} ({formatElevM(band.elevation_ft, band.elevation_m)})
        </h3>
        <p className="text-xs text-slate-500 dark:text-slate-400">
          All models run through unified wet-bulb SLR + wind compaction physics. Partial-horizon models (like HRRR 44h) only enter shorter consensus windows.
        </p>
      </div>

      <div className="mt-3 overflow-x-auto">
        <table className="w-full min-w-[680px] text-left text-xs">
          <thead>
            <tr className="border-b border-slate-200 text-[11px] uppercase tracking-wider text-slate-500 dark:border-slate-800 dark:text-slate-400">
              <th className="py-2 pr-3 font-medium">Weather Model</th>
              <th className="py-2 px-2 font-medium">Horizon</th>
              <th className="py-2 px-2 font-medium">24h</th>
              <th className="py-2 px-2 font-medium">48h</th>
              <th className="py-2 px-2 font-medium">72h</th>
              <th className="py-2 px-2 font-medium">5d</th>
              <th className="py-2 px-2 font-medium">7d</th>
              <th className="py-2 px-2 font-medium">72h SLR</th>
              <th className="py-2 pl-2 font-medium text-right">72h Temp · Wind</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-200/80 tabular-nums dark:divide-slate-800/60">
            {/* Consensus Pin Row */}
            <tr className="bg-sky-50/90 font-medium text-sky-950 dark:bg-sky-500/8 dark:text-sky-100">
              <td className="py-2.5 pr-3">
                <div className="flex items-center gap-2">
                  <span className="h-2 w-2 rounded-full bg-sky-500 dark:bg-sky-400" />
                  <span>Consensus Median</span>
                </div>
                <div className="pl-4 text-[10px] font-normal text-slate-500 dark:text-slate-400">
                  min–max spread
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
                      raw native ({rawLabel}): {formatSnowCm(rawVal)}
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
                        title={beyondHorizon ? `Model stops at ${m.coverage_hours}h` : undefined}
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
    </div>
  );
}
