import type { Lang } from "../i18n";
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

export function formatLastUpdated(timeUtcIso: string | null | undefined): string {
  if (!timeUtcIso) return "—";
  const dt = new Date(timeUtcIso);
  if (Number.isNaN(dt.getTime())) return timeUtcIso;
  return new Intl.DateTimeFormat("en-US", {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
    timeZoneName: "short",
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

const AMBER_BADGE =
  "bg-amber-100/80 text-amber-800 border-amber-300 dark:bg-amber-500/15 dark:text-amber-300 dark:border-amber-500/30";
const SKY_BADGE =
  "bg-sky-100/80 text-sky-800 border-sky-300 dark:bg-sky-500/15 dark:text-sky-300 dark:border-sky-500/30";
const ROSE_BADGE =
  "bg-rose-100/80 text-rose-800 border-rose-300 dark:bg-rose-500/15 dark:text-rose-300 dark:border-rose-500/30";

export function slrBadgeClass(quality: SlrQuality): string {
  switch (quality) {
    case "wet":
      return AMBER_BADGE;
    case "normal":
      return "";
    case "powder":
      return SKY_BADGE;
  }
}

export function slrTitle(quality: SlrQuality, lang: Lang = "en"): string {
  switch (quality) {
    case "wet":
      return lang === "zh" ? "湿重雪 (<10:1)" : "Wet / dense snow (<10:1)";
    case "normal":
      return lang === "zh" ? "常规雪密度 (10–14.9:1)" : "Normal snow density (10–14.9:1)";
    case "powder":
      return lang === "zh" ? "蓬松粉雪 (≥15:1)" : "Light powder (≥15:1)";
  }
}

export function riskBadgeClass(risk: RainSnowRisk): string {
  switch (risk) {
    case "snow":
      return "";
    case "mixed":
      return AMBER_BADGE;
    case "rain":
      return ROSE_BADGE;
  }
}

export function riskLabel(risk: RainSnowRisk, lang: Lang = "en"): string {
  switch (risk) {
    case "snow":
      return lang === "zh" ? "纯雪" : "Snow";
    case "mixed":
      return lang === "zh" ? "雨夹雪" : "Mixed rain/snow";
    case "rain":
      return lang === "zh" ? "降雨" : "Rain";
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
      return ROSE_BADGE;
    case "caution":
      return AMBER_BADGE;
    case "none":
      return "";
  }
}

export function windRiskTitle(level: WindRiskLevel, lang: Lang = "en"): string | undefined {
  switch (level) {
    case "high":
      return lang === "zh"
        ? "缆车极可能停运 (阵风 ≥72 km/h 或风速 ≥55 km/h)"
        : "Very likely lifts will close (gusts ≥72 km/h or wind ≥55 km/h)";
    case "caution":
      return lang === "zh"
        ? "高海拔缆车可能停运 (阵风 ≥55 km/h 或风速 ≥40 km/h)"
        : "Lifts may close, especially high-elevation ones (gusts ≥55 km/h or wind ≥40 km/h)";
    case "none":
      return undefined;
  }
}
