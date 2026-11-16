import { useState } from "react";
import { COPY, type Lang } from "../i18n";
import type { BandDetail, BandKey, DailyBucket } from "../types";
import { TermTooltip } from "./TermTooltip";
import {
  formatSnowCm,
  formatTempC,
  getResortDailyWindRisk,
  getSlrQuality,
  inToCm,
  mphToKmh,
  resortWindRiskTitle,
  riskBadgeClass,
  riskLabel,
  slrBadgeClass,
  slrTitle,
  windRiskBadgeClass,
} from "../utils/format";

const BADGE_PILL_BASE = "inline-block whitespace-nowrap rounded border px-2 py-0.5 font-medium";
const AMBER_SWATCH = "bg-amber-500 dark:bg-amber-400/80";
const SKY_SWATCH = "bg-sky-500 dark:bg-sky-400/80";
const ROSE_SWATCH = "bg-rose-500 dark:bg-rose-400/80";

function TooltipColorLegend({
  heading,
  items,
}: {
  heading?: string;
  items: Array<{ swatchClass: string; text: string }>;
}) {
  return (
    <div className="space-y-1.5">
      {heading && <p className="font-medium text-slate-800 dark:text-slate-100">{heading}</p>}
      <div className="space-y-1">
        {items.map((item) => (
          <div key={item.text} className="flex items-center gap-1.5">
            <span className={`inline-block h-2 w-2 shrink-0 rounded-xs ${item.swatchClass}`} />
            <span>{item.text}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

interface DailyConsensusChartProps {
  daily: DailyBucket[];
  bands?: Partial<Record<BandKey, BandDetail>>;
  selectedBand?: BandKey;
  isDark?: boolean;
  lang?: Lang;
}

export function DailyConsensusChart({
  daily,
  bands,
  selectedBand,
  isDark = false,
  lang = "zh",
}: DailyConsensusChartProps) {
  const [hoveredIdx, setHoveredIdx] = useState<number | null>(null);
  const t = COPY[lang].daily;

  const svgColors = isDark
    ? {
        gridStroke: "rgba(148, 163, 184, 0.14)",
        hoverBg: "rgba(56, 189, 248, 0.08)",
        rangeBar: "rgba(56, 189, 248, 0.18)",
        rangeBarHover: "rgba(56, 189, 248, 0.28)",
        rangeBarStroke: "rgba(56, 189, 248, 0.36)",
        snowBar: "#38bdf8",
        snowBarHover: "#7dd3fc",
        mixedBar: "#f59e0b",
        rainBar: "#f43f5e",
      }
    : {
        gridStroke: "rgba(100, 116, 139, 0.18)",
        hoverBg: "rgba(2, 132, 199, 0.08)",
        rangeBar: "rgba(14, 165, 233, 0.20)",
        rangeBarHover: "rgba(14, 165, 233, 0.30)",
        rangeBarStroke: "rgba(2, 132, 199, 0.34)",
        snowBar: "#0284c7",
        snowBarHover: "#0369a1",
        mixedBar: "#d97706",
        rainBar: "#e11d48",
      };

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
  const barW = Math.min(48, colW * 0.56);
  const medW = Math.min(26, barW * 0.56);

  const yForSnowCm = (cm: number) => padT + plotH - (cm / maxSnowCm) * plotH;

  const yTicks = [0, 0.25, 0.5, 0.75, 1.0].map((frac) => ({
    val: Math.round(maxSnowCm * frac),
    y: padT + plotH * (1 - frac),
  }));

  return (
    <div className="rounded-xl border border-slate-200/90 bg-white/90 p-4 shadow-xs md:p-5 dark:border-slate-800/90 dark:bg-slate-900/65 dark:shadow-none">
      <div className="flex flex-wrap items-end justify-between gap-3 border-b border-slate-200/80 pb-3 dark:border-slate-800/70">
        <div>
          <h3 className="text-sm font-semibold text-slate-900 dark:text-white">
            {t.titlePrefix}
          </h3>
          <p className="text-xs text-slate-500 dark:text-slate-400">
            {t.subtitle}
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-4 text-[11px] text-slate-500 dark:text-slate-400">
          <span className="inline-flex items-center gap-1.5">
            <span className="inline-block h-2 w-2 rounded-xs bg-sky-600 dark:bg-sky-400" /> {t.legendMedian}
          </span>
          <span className="inline-flex items-center gap-1.5">
            <span className="inline-block h-2 w-2 rounded-xs border border-sky-600/35 bg-sky-500/20 dark:border-sky-400/35 dark:bg-sky-400/20" />{" "}
            {t.legendRange}
          </span>
        </div>
      </div>

      {/* SVG Range-Bar + Median Bullet Chart */}
      <div className="mt-3 overflow-x-auto">
        <svg viewBox={`0 0 ${svgW} ${svgH}`} className="w-full min-w-[540px] select-none">
          {yTicks.map((tick) => (
            <g key={tick.val}>
              <line
                x1={padL}
                x2={svgW - padR}
                y1={tick.y}
                y2={tick.y}
                stroke={svgColors.gridStroke}
                strokeDasharray="3 3"
              />
              <text
                x={padL - 6}
                y={tick.y + 3}
                textAnchor="end"
                className="fill-slate-500 text-[10px] tabular-nums dark:fill-slate-400"
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
                ? svgColors.rainBar
                : day.rain_snow_risk === "mixed"
                  ? svgColors.mixedBar
                  : isHovered
                    ? svgColors.snowBarHover
                    : svgColors.snowBar;

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
                  fill={isHovered ? svgColors.hoverBg : "transparent"}
                />

                {maxCm > 0.1 && (
                  <rect
                    x={cx - barW / 2}
                    y={yMax}
                    width={barW}
                    height={Math.max(2, yMin - yMax)}
                    rx={4}
                    fill={isHovered ? svgColors.rangeBarHover : svgColors.rangeBar}
                    stroke={svgColors.rangeBarStroke}
                    strokeWidth={1}
                  />
                )}

                {medCm > 0.05 && (
                  <rect
                    x={cx - medW / 2}
                    y={yMed}
                    width={medW}
                    height={Math.max(2, yZero - yMed)}
                    rx={3}
                    fill={fillColor}
                    fillOpacity={0.9}
                  />
                )}

                <text
                  x={cx}
                  y={Math.max(11, Math.min(yMed, yMax) - 5)}
                  textAnchor="middle"
                  className="fill-slate-800 text-[10px] font-semibold tabular-nums dark:fill-slate-100"
                >
                  {medCm >= 0.1 ? `${medCm.toFixed(1)} cm` : "0 cm"}
                </text>

                <text
                  x={cx}
                  y={svgH - 12}
                  textAnchor="middle"
                  className="fill-slate-600 text-[10px] font-medium dark:fill-slate-300"
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
        <table className="w-full min-w-[560px] text-left text-xs">
          <thead>
            <tr
              className={`border-b border-slate-200 text-[11px] text-slate-500 dark:border-slate-800 dark:text-slate-400 ${
                lang === "en" ? "uppercase tracking-wider" : ""
              }`}
            >
              <th className="py-2 pr-3 font-medium">{t.colDay}</th>
              <th className="py-2 px-3 font-medium">{t.colSnowMedian}</th>
              <th className="py-2 px-3 font-medium">
                <TermTooltip
                  label={t.colSlr}
                  tooltip={
                    <div className="space-y-2">
                      <p>{t.slrTooltip}</p>
                      <div className="border-t border-slate-200/80 pt-1.5 dark:border-slate-700/80">
                        <TooltipColorLegend
                          items={[
                            { swatchClass: AMBER_SWATCH, text: t.wetSnow },
                            { swatchClass: SKY_SWATCH, text: t.powderSnow },
                          ]}
                        />
                      </div>
                    </div>
                  }
                />
              </th>
              <th className="py-2 px-3 font-medium">
                <TermTooltip
                  label={t.colTemp}
                  tooltip={
                    <TooltipColorLegend
                      heading={t.tempLegendHeading}
                      items={[
                        { swatchClass: AMBER_SWATCH, text: t.mixed },
                        { swatchClass: ROSE_SWATCH, text: t.rain },
                      ]}
                    />
                  }
                />
              </th>
              <th className="py-2 pl-3 font-medium">
                <TermTooltip
                  label={t.colWind}
                  tooltip={
                    <TooltipColorLegend
                      heading={t.windRiskLabel}
                      items={[
                        { swatchClass: AMBER_SWATCH, text: t.windHold },
                        { swatchClass: ROSE_SWATCH, text: t.windClosed },
                      ]}
                    />
                  }
                />
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-200/80 tabular-nums dark:divide-slate-800/60">
            {daily.map((day, idx) => {
              const slrQuality = getSlrQuality(day.avg_slr);
              const slrBadge = slrBadgeClass(slrQuality);
              const tempBadge = riskBadgeClass(day.rain_snow_risk);
              const windRisk = getResortDailyWindRisk(day, bands, selectedBand);
              const windBadge = windRiskBadgeClass(windRisk.level);
              return (
                <tr
                  key={day.date}
                  onMouseEnter={() => setHoveredIdx(idx)}
                  onMouseLeave={() => setHoveredIdx(null)}
                  className={`transition ${
                    hoveredIdx === idx ? "bg-sky-50/90 dark:bg-sky-500/10" : "hover:bg-slate-50 dark:hover:bg-slate-800/35"
                  }`}
                >
                  <td className="py-2 pr-3 font-medium text-slate-900 dark:text-slate-100">
                    {day.day_name}
                    {day.is_partial && (
                      <span className="ml-1.5 text-[10px] text-slate-500">({day.hours_in_bucket}h)</span>
                    )}
                  </td>
                  <td className="py-2 px-3">
                    <span className="font-semibold text-sky-700 dark:text-sky-300">
                      {formatSnowCm(day.snow_median_in)}
                    </span>
                    <span className="ml-1.5 text-slate-500 dark:text-slate-400">
                      ({inToCm(day.snow_min_in).toFixed(1)}–{inToCm(day.snow_max_in).toFixed(1)} cm)
                    </span>
                  </td>
                  <td className="py-2 px-3 text-slate-700 dark:text-slate-300">
                    <span
                      title={slrTitle(slrQuality, lang)}
                      className={slrBadge ? `${BADGE_PILL_BASE} ${slrBadge}` : "whitespace-nowrap"}
                    >
                      {day.avg_slr.toFixed(1)}:1
                    </span>
                  </td>
                  <td className="py-2 px-3 text-slate-700 dark:text-slate-300">
                    <span
                      title={`${t.phasePrefix} ${riskLabel(day.rain_snow_risk, lang)}`}
                      className={tempBadge ? `${BADGE_PILL_BASE} ${tempBadge}` : "whitespace-nowrap"}
                    >
                      {formatTempC(day.temp_min_f)} / {formatTempC(day.temp_max_f)}
                    </span>
                  </td>
                  <td className="py-2 pl-3 text-slate-700 dark:text-slate-300">
                    <span
                      title={resortWindRiskTitle(windRisk, selectedBand, lang)}
                      className={windBadge ? `${BADGE_PILL_BASE} ${windBadge}` : "whitespace-nowrap"}
                    >
                      {day.max_wind_mph !== null ? `${Math.round(mphToKmh(day.max_wind_mph))} km/h` : "—"}
                      {day.max_gust_mph !== null ? ` (${Math.round(mphToKmh(day.max_gust_mph))}g)` : ""}
                    </span>
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
