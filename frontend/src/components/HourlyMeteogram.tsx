import { useMemo, useState } from "react";
import type { HourlyConsensusPoint } from "../types";
import {
  fToCelsius,
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
  bandLabel: string;
  baseElevFt: number;
  midElevFt: number;
  summitElevFt: number;
}

type HorizonOption = 48 | 72 | 168;

export function HourlyMeteogram({
  hourly,
  timezone,
  bandLabel,
  baseElevFt,
  midElevFt,
  summitElevFt,
}: HourlyMeteogramProps) {
  const [horizon, setHorizon] = useState<HorizonOption>(168);
  const [hoverIdx, setHoverIdx] = useState<number | null>(null);

  const visible = useMemo(() => hourly.slice(0, horizon), [hourly, horizon]);

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

  const tempsC = visible
    .map((p) => (p.temp_median_f !== null ? fToCelsius(p.temp_median_f) : null))
    .filter((v): v is number => v !== null);
  const minTempC = Math.min(-12, ...(tempsC.length ? tempsC : [-8]));
  const maxTempC = Math.max(6, ...(tempsC.length ? tempsC : [4]));
  const tempSpanC = Math.max(6, maxTempC - minTempC);

  const xFor = (i: number) => padL + (visible.length > 1 ? (i / (visible.length - 1)) * plotW : 0);
  const barStep = plotW / Math.max(1, visible.length);
  const yForRateCm = (cm: number) => sPadT + sPlotH - (cm / maxRateCm) * sPlotH;
  const yForCumCm = (cm: number) => sPadT + sPlotH - (cm / maxCumCm) * sPlotH;
  const yForElevM = (m: number) => lPadT + lPlotH - ((m - minElevM) / elevSpanM) * lPlotH;
  const yForTempC = (c: number) => lPadT + lPlotH - ((c - minTempC) / tempSpanC) * lPlotH;

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
  const tempPath = buildPath(
    visible
      .map((p, i) =>
        p.temp_median_f !== null ? { x: xFor(i), y: yForTempC(fToCelsius(p.temp_median_f)) } : null,
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
    <div className="rounded-xl border border-slate-800/90 bg-slate-900/65 p-4 md:p-5 space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-800/70 pb-3">
        <div>
          <h3 className="text-sm font-semibold text-white">
            Hourly Storm Meteogram &amp; Snow Level · {bandLabel}
          </h3>
          <p className="text-xs text-slate-400">
            Scrub across hours to inspect snowfall intensity (cm/h), cumulative vs settled depth (cm), snow level (m) vs bands, and temp (°C)
          </p>
        </div>
        <div className="inline-flex rounded-lg border border-slate-700/80 bg-slate-950/75 p-0.5 text-xs">
          {([48, 72, 168] as HorizonOption[]).map((h) => (
            <button
              key={h}
              type="button"
              onClick={() => {
                setHorizon(h);
                setHoverIdx(null);
              }}
              className={`rounded-md px-2.5 py-1 font-medium transition ${
                horizon === h ? "bg-sky-500/20 text-sky-200" : "text-slate-400 hover:text-slate-200"
              }`}
            >
              {h === 168 ? "7d (168h)" : `${h}h`}
            </button>
          ))}
        </div>
      </div>

      {/* Live Scrub Readout Strip */}
      <div className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-slate-800 bg-slate-950/80 px-3.5 py-2 text-xs">
        <div className="flex flex-wrap items-center gap-x-4 gap-y-1">
          <span className="font-semibold text-sky-200">
            {formatLocalHourTick(activePt.time_utc, timezone, true)}
          </span>
          <span className="tabular-nums text-slate-300">
            Rate:{" "}
            <strong className="text-sky-300">{inToCm(activePt.snow_median_in).toFixed(1)} cm/h</strong>{" "}
            <span className="text-slate-500">
              ({inToCm(activePt.snow_min_in).toFixed(1)}–{inToCm(activePt.snow_max_in).toFixed(1)})
            </span>
          </span>
          <span className="tabular-nums text-slate-300">
            Cum: <strong className="text-cyan-200">{formatSnowCm(activeCumIn)}</strong>
          </span>
          <span className="tabular-nums text-slate-300">
            Settled: <strong className="text-emerald-300">{formatSnowCm(activePt.settled_snow_in)}</strong>
          </span>
        </div>
        <div className="flex flex-wrap items-center gap-x-4 gap-y-1 tabular-nums text-slate-300">
          <span>
            Temp: <strong className="text-violet-300">{formatTempC(activePt.temp_median_f)}</strong>
          </span>
          <span>
            Snow Lvl: <strong className="text-amber-300">{formatElevM(activePt.snow_level_median_ft)}</strong>
          </span>
          <span>
            Wind: <strong>{formatWindKmh(activePt.wind_median_mph)}</strong>
          </span>
          <span className="text-slate-400">
            SLR {activePt.slr_median !== null ? `${activePt.slr_median.toFixed(1)}:1` : "—"} ·{" "}
            {activePt.model_count}m
          </span>
        </div>
      </div>

      {/* Panel A: Snowfall Rate + Cumulative vs Settled */}
      <div className="space-y-1">
        <div className="flex flex-wrap items-center justify-between text-[11px] text-slate-400">
          <span className="font-medium text-slate-300">Snowfall Rate (cm/h) &amp; Storm Total</span>
          <div className="flex items-center gap-4">
            <span className="inline-flex items-center gap-1.5">
              <span className="inline-block h-2 w-2 rounded-xs bg-sky-400" /> Hourly median
            </span>
            <span className="inline-flex items-center gap-1.5">
              <span className="inline-block h-0.5 w-4 bg-cyan-300" /> Cumulative snow
            </span>
            <span className="inline-flex items-center gap-1.5">
              <span className="inline-block h-0.5 w-4 border-t-2 border-dashed border-emerald-400" />{" "}
              Settled depth
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
                    stroke="rgba(148, 163, 184, 0.12)"
                    strokeDasharray="3 3"
                  />
                  <text x={padL - 6} y={y + 3} textAnchor="end" className="fill-sky-400/80 text-[10px] tabular-nums">
                    {(maxRateCm * frac).toFixed(1)}cm/h
                  </text>
                  <text
                    x={svgW - padR + 6}
                    y={y + 3}
                    textAnchor="start"
                    className="fill-cyan-300/80 text-[10px] tabular-nums"
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
                stroke="rgba(148, 163, 184, 0.14)"
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
                      fill="rgba(56, 189, 248, 0.16)"
                    />
                  )}
                  {pt.snow_median_in > 0.01 && (
                    <rect
                      x={cx - bw / 2}
                      y={yMed}
                      width={bw}
                      height={Math.max(1, yZero - yMed)}
                      fill="#38bdf8"
                      fillOpacity={0.85}
                    />
                  )}
                </g>
              );
            })}

            <path d={cumPath} fill="none" stroke="#67e8f9" strokeWidth={2} />
            <path d={settledPath} fill="none" stroke="#34d399" strokeWidth={1.75} strokeDasharray="5 3" />

            {hoverIdx !== null && (
              <line
                x1={xFor(activeIdx)}
                x2={xFor(activeIdx)}
                y1={sPadT}
                y2={sPadT + sPlotH}
                stroke="rgba(226, 232, 240, 0.7)"
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
        <div className="flex flex-wrap items-center justify-between text-[11px] text-slate-400">
          <span className="font-medium text-slate-300">Snow Level (m) vs Resort Elevations &amp; Temp (°C)</span>
          <div className="flex items-center gap-4">
            <span className="inline-flex items-center gap-1.5">
              <span className="inline-block h-0.5 w-4 bg-amber-400" /> Snow level (m)
            </span>
            <span className="inline-flex items-center gap-1.5">
              <span className="inline-block h-0.5 w-4 bg-violet-400" /> Air temp (°C)
            </span>
            <span className="text-slate-500">Dashed lines: Base / Mid / Summit (m)</span>
          </div>
        </div>

        <div className="overflow-x-auto">
          <svg viewBox={`0 0 ${svgW} ${lvlH}`} className="w-full min-w-[600px] select-none">
            {[
              { label: "Summit", elevM: summitElevM, color: "rgba(56, 189, 248, 0.45)" },
              { label: "Mid", elevM: midElevM, color: "rgba(148, 163, 184, 0.35)" },
              { label: "Base", elevM: baseElevM, color: "rgba(251, 146, 60, 0.45)" },
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
                  <text x={padL - 5} y={y + 3} textAnchor="end" className="fill-slate-400 text-[9.5px] tabular-nums">
                    {Math.round(band.elevM)}m
                  </text>
                </g>
              );
            })}

            {[minTempC, (minTempC + maxTempC) / 2, maxTempC].map((tVal) => (
              <text
                key={tVal}
                x={svgW - padR + 6}
                y={yForTempC(tVal) + 3}
                textAnchor="start"
                className="fill-violet-300/80 text-[10px] tabular-nums"
              >
                {Math.round(tVal)}°C
              </text>
            ))}

            {/* 0°C Freezing Line */}
            {0 >= minTempC && 0 <= maxTempC && (
              <line
                x1={padL}
                x2={svgW - padR}
                y1={yForTempC(0)}
                y2={yForTempC(0)}
                stroke="rgba(167, 139, 250, 0.28)"
                strokeDasharray="2 4"
              />
            )}

            {dayTickIndices.map(({ pt, i }) => {
              const x = xFor(i);
              return (
                <g key={`ldiv-${i}`}>
                  <line
                    x1={x}
                    x2={x}
                    y1={lPadT}
                    y2={lPadT + lPlotH}
                    stroke="rgba(148, 163, 184, 0.14)"
                  />
                  <text x={x + 3} y={lvlH - 8} className="fill-slate-400 text-[10px]">
                    {pt.local_date.slice(5)}
                  </text>
                </g>
              );
            })}

            {snowLvlPath && <path d={snowLvlPath} fill="none" stroke="#fbbf24" strokeWidth={2} />}
            {tempPath && <path d={tempPath} fill="none" stroke="#c084fc" strokeWidth={1.6} opacity={0.85} />}

            {hoverIdx !== null && (
              <line
                x1={xFor(activeIdx)}
                x2={xFor(activeIdx)}
                y1={lPadT}
                y2={lPadT + lPlotH}
                stroke="rgba(226, 232, 240, 0.7)"
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
