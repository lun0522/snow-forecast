import { useMemo, useState } from "react";
import { COPY, type Lang } from "../i18n";
import type { HourlyConsensusPoint } from "../types";
import {
  formatElevM,
  formatLocalHourTick,
  formatSnowCm,
  formatTempC,
  formatWindKmh,
  ftToMeters,
  inToCm,
} from "../utils/format";

interface HourlyMeteogramProps {
  hourly: HourlyConsensusPoint[];
  timezone: string;
  baseElevFt: number;
  midElevFt: number;
  summitElevFt: number;
  isDark?: boolean;
  lang?: Lang;
}

const MAX_HORIZON_HOURS = 168;

export function HourlyMeteogram({
  hourly,
  timezone,
  baseElevFt,
  midElevFt,
  summitElevFt,
  isDark = false,
  lang = "zh",
}: HourlyMeteogramProps) {
  const [hoverIdx, setHoverIdx] = useState<number | null>(null);
  const t = COPY[lang].hourly;

  const svgColors = isDark
    ? {
        gridStroke: "rgba(148, 163, 184, 0.12)",
        dayDivider: "rgba(148, 163, 184, 0.14)",
        maxRateShade: "rgba(56, 189, 248, 0.16)",
        medRateBar: "#38bdf8",
        cumLine: "#67e8f9",
        settledLine: "#34d399",
        snowLvlLine: "#fbbf24",
        summitBand: "rgba(56, 189, 248, 0.45)",
        midBand: "rgba(148, 163, 184, 0.35)",
        baseBand: "rgba(251, 146, 60, 0.45)",
        crosshair: "rgba(226, 232, 240, 0.7)",
      }
    : {
        gridStroke: "rgba(100, 116, 139, 0.18)",
        dayDivider: "rgba(100, 116, 139, 0.2)",
        maxRateShade: "rgba(14, 165, 233, 0.18)",
        medRateBar: "#0284c7",
        cumLine: "#0891b2",
        settledLine: "#059669",
        snowLvlLine: "#d97706",
        summitBand: "rgba(2, 132, 199, 0.48)",
        midBand: "rgba(100, 116, 139, 0.42)",
        baseBand: "rgba(234, 88, 12, 0.48)",
        crosshair: "rgba(15, 23, 42, 0.55)",
      };

  const visible = useMemo(() => hourly.slice(0, MAX_HORIZON_HOURS), [hourly]);

  const cumulativeSnowIn = useMemo(() => {
    const out: number[] = [];
    let running = 0;
    for (const pt of visible) {
      running += pt.snow_median_in;
      out.push(Math.round(running * 100) / 100);
    }
    return out;
  }, [visible]);

  if (!visible.length) {
    return null;
  }

  const activeIdx = hoverIdx !== null && hoverIdx < visible.length ? hoverIdx : visible.length - 1;
  const activePt = visible[activeIdx];
  const activeCumIn = cumulativeSnowIn[activeIdx] ?? 0;

  const svgW = 860;
  const padL = 52;
  const padR = 54;
  const plotW = svgW - padL - padR;

  // Panel A (Snow rate cm/h + cumulative/settled cm)
  const snowH = 190;
  const sPadT = 16;
  const sPadB = 22;
  const sPlotH = snowH - sPadT - sPadB;
  const maxRateCm = Math.max(1.2, ...visible.map((p) => inToCm(p.snow_max_in)));
  const maxCumCm = Math.max(
    5,
    ...cumulativeSnowIn.map(inToCm),
    ...visible.map((p) => inToCm(p.settled_snow_in)),
  );

  // Panel B (Snow level in meters vs Base/Mid/Summit + Air Temp C)
  const lvlH = 175;
  const lPadT = 16;
  const lPadB = 28;
  const lPlotH = lvlH - lPadT - lPadB;

  const baseElevM = ftToMeters(baseElevFt);
  const midElevM = ftToMeters(midElevFt);
  const summitElevM = ftToMeters(summitElevFt);

  const snowLvlsM = visible
    .map((p) => (p.snow_level_median_ft !== null ? ftToMeters(p.snow_level_median_ft) : null))
    .filter((v): v is number => v !== null);
  const minElevM = Math.min(baseElevM - 450, ...(snowLvlsM.length ? snowLvlsM : [baseElevM]));
  const maxElevM = Math.max(summitElevM + 450, ...(snowLvlsM.length ? snowLvlsM : [summitElevM]));
  const elevSpanM = Math.max(400, maxElevM - minElevM);

  const xFor = (i: number) => padL + (visible.length > 1 ? (i / (visible.length - 1)) * plotW : 0);
  const barStep = plotW / Math.max(1, visible.length);
  const yForRateCm = (cm: number) => sPadT + sPlotH - (cm / maxRateCm) * sPlotH;
  const yForCumCm = (cm: number) => sPadT + sPlotH - (cm / maxCumCm) * sPlotH;
  const yForElevM = (m: number) => lPadT + lPlotH - ((m - minElevM) / elevSpanM) * lPlotH;

  const buildPath = (pts: Array<{ x: number; y: number }>) => {
    if (!pts.length) return "";
    return pts.map((p, idx) => `${idx === 0 ? "M" : "L"}${p.x.toFixed(1)},${p.y.toFixed(1)}`).join(" ");
  };

  const cumPath = buildPath(
    cumulativeSnowIn.map((valIn, i) => ({ x: xFor(i), y: yForCumCm(inToCm(valIn)) })),
  );
  const settledPath = buildPath(
    visible.map((p, i) => ({ x: xFor(i), y: yForCumCm(inToCm(p.settled_snow_in)) })),
  );

  const snowLvlPath = buildPath(
    visible
      .map((p, i) =>
        p.snow_level_median_ft !== null
          ? { x: xFor(i), y: yForElevM(ftToMeters(p.snow_level_median_ft)) }
          : null,
      )
      .filter((pt): pt is { x: number; y: number } => pt !== null),
  );

  const dayTickIndices = visible
    .map((pt, i) => ({ pt, i }))
    .filter(({ pt, i }) => i === 0 || pt.local_date !== visible[i - 1]?.local_date);

  const handlePointerMove = (evt: React.MouseEvent<SVGRectElement>) => {
    const rect = evt.currentTarget.getBoundingClientRect();
    if (!rect.width) return;
    const relX = evt.clientX - rect.left;
    const ratio = Math.max(0, Math.min(1, relX / rect.width));
    const idx = Math.round(ratio * (visible.length - 1));
    setHoverIdx(idx);
  };

  return (
    <div className="rounded-xl border border-slate-200/90 bg-white/90 p-4 shadow-xs md:p-5 space-y-4 dark:border-slate-800/90 dark:bg-slate-900/65 dark:shadow-none">
      <div className="border-b border-slate-200/80 pb-3 dark:border-slate-800/70">
        <h3 className="text-sm font-semibold text-slate-900 dark:text-white">
          {t.titlePrefix}
        </h3>
        <p className="text-xs text-slate-500 dark:text-slate-400">
          {t.subtitle}
        </p>
      </div>

      {/* Live Scrub Readout Strip */}
      <div className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-slate-200 bg-slate-50 px-3.5 py-2 text-xs dark:border-slate-800 dark:bg-slate-950/80">
        <div className="flex flex-wrap items-center gap-x-4 gap-y-1">
          <span className="font-semibold text-slate-900 dark:text-sky-200">
            {formatLocalHourTick(activePt.time_utc, timezone, true)}
          </span>
          <span className="tabular-nums text-slate-600 dark:text-slate-300">
            {t.rateLabel}{" "}
            <strong className="text-sky-700 dark:text-sky-300">
              {inToCm(activePt.snow_median_in).toFixed(1)} cm/h
            </strong>{" "}
            <span className="text-slate-500">
              ({inToCm(activePt.snow_min_in).toFixed(1)}–{inToCm(activePt.snow_max_in).toFixed(1)})
            </span>
          </span>
          <span className="tabular-nums text-slate-600 dark:text-slate-300">
            {t.cumLabel} <strong className="text-cyan-700 dark:text-cyan-200">{formatSnowCm(activeCumIn)}</strong>
          </span>
          <span className="tabular-nums text-slate-600 dark:text-slate-300">
            {t.settledLabel}{" "}
            <strong className="text-emerald-700 dark:text-emerald-300">
              {formatSnowCm(activePt.settled_snow_in)}
            </strong>
          </span>
        </div>
        <div className="flex flex-wrap items-center gap-x-4 gap-y-1 tabular-nums text-slate-600 dark:text-slate-300">
          <span>
            {t.tempLabel}{" "}
            <strong className="text-violet-700 dark:text-violet-300">
              {formatTempC(activePt.temp_median_f)}
            </strong>
          </span>
          <span>
            {t.snowLvlLabel}{" "}
            <strong className="text-amber-700 dark:text-amber-300">
              {formatElevM(activePt.snow_level_median_ft)}
            </strong>
          </span>
          <span>
            {t.windLabel} <strong className="text-slate-900 dark:text-slate-100">{formatWindKmh(activePt.wind_median_mph)}</strong>
          </span>
          <span className="text-slate-500 dark:text-slate-400">
            {t.slrLabel} {activePt.slr_median !== null ? `${activePt.slr_median.toFixed(1)}:1` : "—"} ·{" "}
            {activePt.model_count}m
          </span>
        </div>
      </div>

      {/* Panel A: Snowfall Rate + Cumulative vs Settled */}
      <div className="space-y-1">
        <div className="flex flex-wrap items-center justify-between text-[11px] text-slate-500 dark:text-slate-400">
          <span className="font-medium text-slate-700 dark:text-slate-300">
            {t.panelATitle}
          </span>
          <div className="flex flex-wrap items-center gap-4">
            <span className="inline-flex items-center gap-1.5">
              <span className="inline-block h-2 w-2 rounded-xs bg-sky-600 dark:bg-sky-400" /> {t.hourlyMedian}
            </span>
            <span className="inline-flex items-center gap-1.5">
              <span className="inline-block h-2 w-2 rounded-xs bg-sky-500/25 dark:bg-sky-400/25" /> {t.hourlyMax}
            </span>
            <span className="inline-flex items-center gap-1.5">
              <span className="inline-block h-0.5 w-4 bg-cyan-600 dark:bg-cyan-300" /> {t.cumulativeSnow}
            </span>
            <span className="inline-flex items-center gap-1.5">
              <span className="inline-block h-0.5 w-4 border-t-2 border-dashed border-emerald-600 dark:border-emerald-400" />{" "}
              {t.settledDepth}
            </span>
          </div>
        </div>

        <div className="overflow-x-auto">
          <svg viewBox={`0 0 ${svgW} ${snowH}`} className="w-full min-w-[600px] select-none">
            {[0, 0.5, 1].map((frac) => {
              const y = sPadT + sPlotH * (1 - frac);
              return (
                <g key={frac}>
                  <line
                    x1={padL}
                    x2={svgW - padR}
                    y1={y}
                    y2={y}
                    stroke={svgColors.gridStroke}
                    strokeDasharray="3 3"
                  />
                  <text
                    x={padL - 6}
                    y={y + 3}
                    textAnchor="end"
                    className="fill-sky-600 text-[10px] tabular-nums dark:fill-sky-400/80"
                  >
                    {(maxRateCm * frac).toFixed(1)}cm/h
                  </text>
                  <text
                    x={svgW - padR + 6}
                    y={y + 3}
                    textAnchor="start"
                    className="fill-cyan-700 text-[10px] tabular-nums dark:fill-cyan-300/80"
                  >
                    {Math.round(maxCumCm * frac)}cm
                  </text>
                </g>
              );
            })}

            {dayTickIndices.map(({ i }) => (
              <line
                key={`sdiv-${i}`}
                x1={xFor(i)}
                x2={xFor(i)}
                y1={sPadT}
                y2={sPadT + sPlotH}
                stroke={svgColors.dayDivider}
              />
            ))}

            {visible.map((pt, i) => {
              const cx = xFor(i);
              const yZero = sPadT + sPlotH;
              const yMed = yForRateCm(inToCm(pt.snow_median_in));
              const yMax = yForRateCm(inToCm(pt.snow_max_in));
              const bw = Math.max(1.5, barStep * 0.68);
              return (
                <g key={pt.time_utc}>
                  {pt.snow_max_in > 0.01 && (
                    <rect
                      x={cx - bw / 2}
                      y={yMax}
                      width={bw}
                      height={Math.max(1, yZero - yMax)}
                      fill={svgColors.maxRateShade}
                    />
                  )}
                  {pt.snow_median_in > 0.01 && (
                    <rect
                      x={cx - bw / 2}
                      y={yMed}
                      width={bw}
                      height={Math.max(1, yZero - yMed)}
                      fill={svgColors.medRateBar}
                      fillOpacity={0.85}
                    />
                  )}
                </g>
              );
            })}

            <path d={cumPath} fill="none" stroke={svgColors.cumLine} strokeWidth={2} />
            <path d={settledPath} fill="none" stroke={svgColors.settledLine} strokeWidth={1.75} strokeDasharray="5 3" />

            {hoverIdx !== null && (
              <line
                x1={xFor(activeIdx)}
                x2={xFor(activeIdx)}
                y1={sPadT}
                y2={sPadT + sPlotH}
                stroke={svgColors.crosshair}
                strokeWidth={1}
              />
            )}

            <rect
              x={padL}
              y={sPadT}
              width={plotW}
              height={sPlotH}
              fill="transparent"
              className="cursor-crosshair"
              onMouseMove={handlePointerMove}
              onMouseLeave={() => setHoverIdx(null)}
            />
          </svg>
        </div>
      </div>

      {/* Panel B: Snow Level (m) vs Elevation Bands + Air Temp (°C) */}
      <div className="space-y-1">
        <div className="flex flex-wrap items-center justify-between text-[11px] text-slate-500 dark:text-slate-400">
          <span className="font-medium text-slate-700 dark:text-slate-300">
            {t.panelBTitle}
          </span>
          <div className="flex items-center gap-4">
            <span className="inline-flex items-center gap-1.5">
              <span className="inline-block h-0.5 w-4 bg-amber-600 dark:bg-amber-400" /> {t.snowLevelLegend}
            </span>
            <span className="text-slate-500">{t.dashedLinesLegend}</span>
          </div>
        </div>

        <div className="overflow-x-auto">
          <svg viewBox={`0 0 ${svgW} ${lvlH}`} className="w-full min-w-[600px] select-none">
            {[
              { label: t.bandSummit, elevM: summitElevM, color: svgColors.summitBand },
              { label: t.bandMid, elevM: midElevM, color: svgColors.midBand },
              { label: t.bandBase, elevM: baseElevM, color: svgColors.baseBand },
            ].map((band) => {
              const y = yForElevM(band.elevM);
              return (
                <g key={band.label}>
                  <line
                    x1={padL}
                    x2={svgW - padR}
                    y1={y}
                    y2={y}
                    stroke={band.color}
                    strokeDasharray="4 4"
                    strokeWidth={1}
                  />
                  <text
                    x={padL - 5}
                    y={y + 3}
                    textAnchor="end"
                    className="fill-slate-500 text-[9.5px] tabular-nums dark:fill-slate-400"
                  >
                    {Math.round(band.elevM)}m
                  </text>
                  <text
                    x={svgW - padR + 6}
                    y={y + 3}
                    textAnchor="start"
                    className="fill-slate-500 text-[9.5px] dark:fill-slate-400"
                  >
                    {band.label}
                  </text>
                </g>
              );
            })}

            {dayTickIndices.map(({ pt, i }) => {
              const x = xFor(i);
              return (
                <g key={`ldiv-${i}`}>
                  <line
                    x1={x}
                    x2={x}
                    y1={lPadT}
                    y2={lPadT + lPlotH}
                    stroke={svgColors.dayDivider}
                  />
                  <text x={x + 3} y={lvlH - 8} className="fill-slate-500 text-[10px] dark:fill-slate-400">
                    {pt.local_date.slice(5)}
                  </text>
                </g>
              );
            })}

            {snowLvlPath && <path d={snowLvlPath} fill="none" stroke={svgColors.snowLvlLine} strokeWidth={2} />}

            {hoverIdx !== null && (
              <line
                x1={xFor(activeIdx)}
                x2={xFor(activeIdx)}
                y1={lPadT}
                y2={lPadT + lPlotH}
                stroke={svgColors.crosshair}
                strokeWidth={1}
              />
            )}

            <rect
              x={padL}
              y={lPadT}
              width={plotW}
              height={lPlotH}
              fill="transparent"
              className="cursor-crosshair"
              onMouseMove={handlePointerMove}
              onMouseLeave={() => setHoverIdx(null)}
            />
          </svg>
        </div>
      </div>
    </div>
  );
}
