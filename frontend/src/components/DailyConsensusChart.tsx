import { useState } from "react";
import type { DailyBucket } from "../types";
import {
  formatElevM,
  formatElevRangeM,
  formatPrecipMm,
  formatSnowCm,
  formatTempC,
  getSlrQuality,
  getWindRiskLevel,
  inToCm,
  mphToKmh,
  riskBadgeClass,
  riskLabel,
  slrBadgeClass,
  slrTitle,
  windRiskBadgeClass,
  windRiskTitle,
} from "../utils/format";

const BADGE_PILL_BASE = "inline-block whitespace-nowrap rounded border px-2 py-0.5 font-medium";

interface DailyConsensusChartProps {
  daily: DailyBucket[];
  elevationFt: number;
  elevationM?: number | null;
  bandLabel: string;
}

export function DailyConsensusChart({
  daily,
  elevationFt,
  elevationM,
  bandLabel,
}: DailyConsensusChartProps) {
  const [hoveredIdx, setHoveredIdx] = useState<number | null>(null);

  if (!daily.length) {
    return null;
  }

  const maxSnowCm = Math.max(
    10,
    ...daily.map((d) => inToCm(Math.max(d.snow_max_in, d.snow_median_in))),
  );

  const svgW = 760;
  const svgH = 210;
  const padL = 44;
  const padR = 14;
  const padT = 18;
  const padB = 34;
  const plotW = svgW - padL - padR;
  const plotH = svgH - padT - padB;
  const colW = plotW / daily.length;
  const barW = Math.min(44, colW * 0.5);

  const yForSnowCm = (cm: number) => padT + plotH - (cm / maxSnowCm) * plotH;

  const yTicks = [0, 0.25, 0.5, 0.75, 1.0].map((frac) => ({
    val: Math.round(maxSnowCm * frac),
    y: padT + plotH * (1 - frac),
  }));

  return (
    <div className="rounded-xl border border-slate-800/90 bg-slate-900/65 p-4 md:p-5">
      <div className="pb-3 border-b border-slate-800/70">
        <h3 className="text-sm font-semibold text-white">
          7-Day Local Forecast Consensus · {bandLabel} ({formatElevM(elevationFt, elevationM)})
        </h3>
        <p className="text-xs text-slate-400">
          Bars = multi-model median snowfall (cm); whiskers = min–max model range per local calendar day
        </p>
      </div>

      {/* SVG Column + Whisker Chart */}
      <div className="mt-3 overflow-x-auto">
        <svg viewBox={`0 0 ${svgW} ${svgH}`} className="w-full min-w-[540px] select-none">
          {yTicks.map((tick) => (
            <g key={tick.val}>
              <line
                x1={padL}
                x2={svgW - padR}
                y1={tick.y}
                y2={tick.y}
                stroke="rgba(148, 163, 184, 0.14)"
                strokeDasharray="3 3"
              />
              <text
                x={padL - 6}
                y={tick.y + 3}
                textAnchor="end"
                className="fill-slate-500 text-[10px] tabular-nums"
              >
                {tick.val} cm
              </text>
            </g>
          ))}

          {daily.map((day, idx) => {
            const medCm = inToCm(day.snow_median_in);
            const minCm = inToCm(day.snow_min_in);
            const maxCm = inToCm(day.snow_max_in);

            const cx = padL + colW * idx + colW / 2;
            const yMed = yForSnowCm(medCm);
            const yMin = yForSnowCm(minCm);
            const yMax = yForSnowCm(maxCm);
            const yZero = padT + plotH;
            const isHovered = hoveredIdx === idx;

            const fillColor =
              day.rain_snow_risk === "rain"
                ? "#f43f5e"
                : day.rain_snow_risk === "mixed"
                  ? "#f59e0b"
                  : isHovered
                    ? "#7dd3fc"
                    : "#38bdf8";

            return (
              <g
                key={day.date}
                className="cursor-pointer"
                onMouseEnter={() => setHoveredIdx(idx)}
                onMouseLeave={() => setHoveredIdx(null)}
              >
                <rect
                  x={padL + colW * idx + 2}
                  y={padT}
                  width={Math.max(10, colW - 4)}
                  height={plotH}
                  rx={6}
                  fill={isHovered ? "rgba(56, 189, 248, 0.08)" : "transparent"}
                />

                {medCm > 0.05 && (
                  <rect
                    x={cx - barW / 2}
                    y={yMed}
                    width={barW}
                    height={Math.max(2, yZero - yMed)}
                    rx={4}
                    fill={fillColor}
                    fillOpacity={0.85}
                  />
                )}

                {maxCm > 0.1 && (
                  <g>
                    <line
                      x1={cx}
                      x2={cx}
                      y1={yMax}
                      y2={yMin}
                      stroke="rgba(226, 232, 240, 0.65)"
                      strokeWidth={1.5}
                    />
                    <line
                      x1={cx - 5}
                      x2={cx + 5}
                      y1={yMax}
                      y2={yMax}
                      stroke="rgba(226, 232, 240, 0.85)"
                      strokeWidth={1.5}
                    />
                    <line
                      x1={cx - 5}
                      x2={cx + 5}
                      y1={yMin}
                      y2={yMin}
                      stroke="rgba(226, 232, 240, 0.65)"
                      strokeWidth={1.5}
                    />
                  </g>
                )}

                <text
                  x={cx}
                  y={Math.max(11, Math.min(yMed, yMax) - 5)}
                  textAnchor="middle"
                  className="fill-slate-100 text-[10px] font-semibold tabular-nums"
                >
                  {medCm >= 0.1 ? `${medCm.toFixed(1)} cm` : "0 cm"}
                </text>

                <text
                  x={cx}
                  y={svgH - 12}
                  textAnchor="middle"
                  className="fill-slate-300 text-[10px] font-medium"
                >
                  {day.day_name}
                  {day.is_partial ? "*" : ""}
                </text>
              </g>
            );
          })}
        </svg>
      </div>

      {/* High-Density Daily Table */}
      <div className="mt-4 overflow-x-auto">
        <table className="w-full min-w-[660px] text-left text-xs">
          <thead>
            <tr className="border-b border-slate-800 text-[11px] uppercase tracking-wider text-slate-400">
              <th className="py-2 pr-3 font-medium">Local Day</th>
              <th className="py-2 px-3 font-medium">Snow Median (Range)</th>
              <th className="py-2 px-3 font-medium">QPF</th>
              <th className="py-2 px-3 font-medium">SLR</th>
              <th className="py-2 px-3 font-medium">Temp Lo / Hi</th>
              <th className="py-2 px-3 font-medium">Max Wind / Gust</th>
              <th className="py-2 pl-3 font-medium">Snow Level</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800/60 tabular-nums">
            {daily.map((day, idx) => {
              const slrQuality = getSlrQuality(day.avg_slr);
              const slrBadge = slrBadgeClass(slrQuality);
              const tempBadge = riskBadgeClass(day.rain_snow_risk);
              const windRisk = getWindRiskLevel(day.max_wind_mph, day.max_gust_mph);
              const windBadge = windRiskBadgeClass(windRisk);
              return (
                <tr
                  key={day.date}
                  onMouseEnter={() => setHoveredIdx(idx)}
                  onMouseLeave={() => setHoveredIdx(null)}
                  className={`transition ${
                    hoveredIdx === idx ? "bg-sky-500/10" : "hover:bg-slate-800/35"
                  }`}
                >
                  <td className="py-2 pr-3 font-medium text-slate-100">
                    {day.day_name}
                    {day.is_partial && (
                      <span className="ml-1.5 text-[10px] text-slate-500">({day.hours_in_bucket}h)</span>
                    )}
                  </td>
                  <td className="py-2 px-3">
                    <span className="font-semibold text-sky-300">
                      {formatSnowCm(day.snow_median_in)}
                    </span>
                    <span className="ml-1.5 text-slate-400">
                      ({inToCm(day.snow_min_in).toFixed(1)}–{inToCm(day.snow_max_in).toFixed(1)} cm)
                    </span>
                  </td>
                  <td className="py-2 px-3 text-slate-300">{formatPrecipMm(day.precip_median_in, 1)}</td>
                  <td className="py-2 px-3">
                    <span
                      title={slrTitle(slrQuality)}
                      className={slrBadge ? `${BADGE_PILL_BASE} ${slrBadge}` : "whitespace-nowrap"}
                    >
                      {day.avg_slr.toFixed(1)}:1
                    </span>
                  </td>
                  <td className="py-2 px-3 text-slate-300">
                    <span
                      title={`Phase: ${riskLabel(day.rain_snow_risk)}`}
                      className={tempBadge ? `${BADGE_PILL_BASE} ${tempBadge}` : "whitespace-nowrap"}
                    >
                      {formatTempC(day.temp_min_f)} / {formatTempC(day.temp_max_f)}
                    </span>
                  </td>
                  <td className="py-2 px-3 text-slate-300">
                    <span
                      title={windRiskTitle(windRisk)}
                      className={windBadge ? `${BADGE_PILL_BASE} ${windBadge}` : "whitespace-nowrap"}
                    >
                      {day.max_wind_mph !== null ? `${Math.round(mphToKmh(day.max_wind_mph))} km/h` : "—"}
                      {day.max_gust_mph !== null ? ` (${Math.round(mphToKmh(day.max_gust_mph))}g)` : ""}
                    </span>
                  </td>
                  <td className="py-2 pl-3 text-slate-300">
                    {formatElevRangeM(day.snow_level_min_ft, day.snow_level_max_ft)}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {/* Compact Color Key for SLR, Temp Phase & Wind Lift Risk */}
      <div className="mt-2.5 flex flex-wrap items-center justify-between gap-x-5 gap-y-1.5 text-[11px] text-slate-400">
        <div className="flex flex-wrap items-center gap-3">
          <span>SLR:</span>
          <span className="inline-flex items-center gap-1">
            <span className="inline-block h-2 w-2 rounded-xs bg-amber-400/80" /> Wet (&lt;10:1)
          </span>
          <span className="inline-flex items-center gap-1">
            <span className="inline-block h-2 w-2 rounded-xs bg-sky-400/80" /> Powder (≥15:1)
          </span>
        </div>
        <div className="flex flex-wrap items-center gap-3">
          <span>Temp:</span>
          <span className="inline-flex items-center gap-1">
            <span className="inline-block h-2 w-2 rounded-xs bg-amber-400/80" /> Mixed
          </span>
          <span className="inline-flex items-center gap-1">
            <span className="inline-block h-2 w-2 rounded-xs bg-rose-400/80" /> Rain
          </span>
        </div>
        <div className="flex flex-wrap items-center gap-3">
          <span>Wind lift risk:</span>
          <span className="inline-flex items-center gap-1">
            <span className="inline-block h-2 w-2 rounded-xs bg-amber-400/80" /> High lifts may close (≥55 km/h gust)
          </span>
          <span className="inline-flex items-center gap-1">
            <span className="inline-block h-2 w-2 rounded-xs bg-rose-400/80" /> Lifts likely closed (≥72 km/h gust)
          </span>
        </div>
      </div>
    </div>
  );
}
