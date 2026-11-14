import type { RainSnowRisk } from "../types";

export type SlrQuality = "wet" | "normal" | "powder";
export type WindRiskLevel = "none" | "caution" | "high";

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

export function getSlrQuality(avgSlr: number): SlrQuality {
  const rounded = Number(avgSlr.toFixed(1));
  if (rounded < 10.0) {
    return "wet";
  }
  if (rounded >= 15.0) {
    return "powder";
  }
  return "normal";
}

export function slrBadgeClass(quality: SlrQuality): string {
  switch (quality) {
    case "wet":
      return "bg-amber-500/15 text-amber-300 border-amber-500/30";
    case "normal":
      return "";
    case "powder":
      return "bg-sky-500/15 text-sky-300 border-sky-500/30";
  }
}

export function slrTitle(quality: SlrQuality): string {
  switch (quality) {
    case "wet":
      return "Wet / dense snow (<10:1)";
    case "normal":
      return "Normal snow density (10–14.9:1)";
    case "powder":
      return "Light powder (≥15:1)";
  }
}

export function riskBadgeClass(risk: RainSnowRisk): string {
  switch (risk) {
    case "snow":
      return "";
    case "mixed":
      return "bg-amber-500/15 text-amber-300 border-amber-500/30";
    case "rain":
      return "bg-rose-500/15 text-rose-300 border-rose-500/30";
  }
}

export function riskLabel(risk: RainSnowRisk): string {
  switch (risk) {
    case "snow":
      return "Snow";
    case "mixed":
      return "Mixed rain/snow";
    case "rain":
      return "Rain";
  }
}

export function getWindRiskLevel(
  maxWindMph: number | null | undefined,
  maxGustMph: number | null | undefined,
): WindRiskLevel {
  const windKmh = maxWindMph != null ? mphToKmh(maxWindMph) : 0;
  const gustKmh = maxGustMph != null ? mphToKmh(maxGustMph) : 0;
  if (gustKmh >= 72 || windKmh >= 55) {
    return "high";
  }
  if (gustKmh >= 55 || windKmh >= 40) {
    return "caution";
  }
  return "none";
}

export function windRiskBadgeClass(level: WindRiskLevel): string {
  switch (level) {
    case "high":
      return "bg-rose-500/15 text-rose-300 border-rose-500/30";
    case "caution":
      return "bg-amber-500/15 text-amber-300 border-amber-500/30";
    case "none":
      return "";
  }
}

export function windRiskTitle(level: WindRiskLevel): string | undefined {
  switch (level) {
    case "high":
      return "Very likely lifts will close (gusts ≥72 km/h or wind ≥55 km/h)";
    case "caution":
      return "Lifts may close, especially high-elevation ones (gusts ≥55 km/h or wind ≥40 km/h)";
    case "none":
      return undefined;
  }
}
