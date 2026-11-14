import type { ConfidenceLevel, RainSnowRisk } from "../types";

export function inToCm(inches: number): number {
  return inches * 2.54;
}

export function inToMm(inches: number): number {
  return inches * 25.4;
}

export function ftToMeters(feet: number): number {
  return feet * 0.3048;
}

export function fToCelsius(fahrenheit: number): number {
  return (fahrenheit - 32) * (5 / 9);
}

export function mphToKmh(mph: number): number {
  return mph * 1.60934;
}

export function formatSnowCm(inches: number | null | undefined, digits = 1): string {
  if (inches === null || inches === undefined || Number.isNaN(inches)) {
    return "—";
  }
  return `${inToCm(inches).toFixed(digits)} cm`;
}

export function formatSnowCmRange(minIn: number, maxIn: number, digits = 1): string {
  return `(${inToCm(minIn).toFixed(digits)}–${inToCm(maxIn).toFixed(digits)} cm)`;
}

export function formatPrecipMm(inches: number | null | undefined, digits = 1): string {
  if (inches === null || inches === undefined || Number.isNaN(inches)) {
    return "—";
  }
  return `${inToMm(inches).toFixed(digits)} mm`;
}

export function formatElevM(
  feet: number | null | undefined,
  explicitMeters?: number | null,
): string {
  if (explicitMeters !== null && explicitMeters !== undefined && !Number.isNaN(explicitMeters)) {
    return `${Math.round(explicitMeters).toLocaleString()} m`;
  }
  if (feet === null || feet === undefined || Number.isNaN(feet)) {
    return "—";
  }
  return `${Math.round(ftToMeters(feet)).toLocaleString()} m`;
}

export function formatElevRangeM(
  minFt: number | null | undefined,
  maxFt: number | null | undefined,
): string {
  if (
    minFt === null ||
    minFt === undefined ||
    maxFt === null ||
    maxFt === undefined ||
    Number.isNaN(minFt) ||
    Number.isNaN(maxFt)
  ) {
    return "—";
  }
  return `${Math.round(ftToMeters(minFt)).toLocaleString()}–${Math.round(ftToMeters(maxFt)).toLocaleString()} m`;
}

export function formatTempC(fahrenheit: number | null | undefined, digits = 0): string {
  if (fahrenheit === null || fahrenheit === undefined || Number.isNaN(fahrenheit)) {
    return "—";
  }
  const c = fToCelsius(fahrenheit);
  const rounded = Number(c.toFixed(digits));
  const clean = Object.is(rounded, -0) ? 0 : rounded;
  return `${clean.toFixed(digits)}°C`;
}

export function formatWindKmh(mph: number | null | undefined): string {
  if (mph === null || mph === undefined || Number.isNaN(mph)) {
    return "—";
  }
  return `${Math.round(mphToKmh(mph))} km/h`;
}

export function formatDeltaSnowCm(deltaIn: number | null | undefined): string {
  if (deltaIn === null || deltaIn === undefined || Number.isNaN(deltaIn)) {
    return "0.0 cm";
  }
  const cm = inToCm(deltaIn);
  const sign = cm > 0 ? "+" : "";
  return `${sign}${cm.toFixed(1)} cm`;
}

export function formatUtcTimestamp(iso: string | null | undefined, tz = "America/Los_Angeles"): string {
  if (!iso) return "Unknown";
  const dt = new Date(iso);
  if (Number.isNaN(dt.getTime())) return iso;
  return new Intl.DateTimeFormat("en-US", {
    timeZone: tz,
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
    timeZoneName: "short",
  }).format(dt);
}

export function formatLocalHourTick(timeUtcIso: string, tz: string, includeDate = false): string {
  const dt = new Date(timeUtcIso);
  if (Number.isNaN(dt.getTime())) return timeUtcIso;
  if (includeDate) {
    return new Intl.DateTimeFormat("en-US", {
      timeZone: tz,
      weekday: "short",
      hour: "numeric",
    }).format(dt);
  }
  return new Intl.DateTimeFormat("en-US", {
    timeZone: tz,
    hour: "numeric",
  }).format(dt);
}

export function riskBadgeClass(risk: RainSnowRisk): string {
  switch (risk) {
    case "snow":
      return "bg-sky-500/15 text-sky-300 border-sky-500/30";
    case "mixed":
      return "bg-amber-500/15 text-amber-300 border-amber-500/30";
    case "rain":
      return "bg-rose-500/15 text-rose-300 border-rose-500/30";
  }
}

export function confidenceBadgeClass(confidence: ConfidenceLevel): string {
  switch (confidence) {
    case "high":
      return "bg-emerald-500/15 text-emerald-300 border-emerald-500/30";
    case "medium":
      return "bg-amber-500/15 text-amber-300 border-amber-500/30";
    case "low":
      return "bg-rose-500/15 text-rose-300 border-rose-500/30";
  }
}
