import type {
  ForecastRunMeta,
  RefreshResponse,
  ResortDetail,
  ResortsOverviewResponse,
} from "./types";

const API_BASE = (import.meta.env.VITE_API_BASE as string | undefined) ?? "";

async function requestJson<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, init);
  if (!response.ok) {
    let message = `Request failed (${response.status})`;
    try {
      const payload = (await response.json()) as { detail?: string };
      if (payload?.detail) {
        message = payload.detail;
      }
    } catch {
      // Ignore non-JSON error body
    }
    throw new Error(message);
  }
  return (await response.json()) as T;
}

export function fetchHealth(): Promise<{
  status: string;
  latest_run: ForecastRunMeta | null;
  resorts_count: number;
}> {
  return requestJson("/api/health");
}

export function fetchResorts(): Promise<ResortsOverviewResponse> {
  return requestJson("/api/resorts");
}

export function fetchResortDetail(resortId: string): Promise<ResortDetail> {
  return requestJson(`/api/resorts/${encodeURIComponent(resortId)}`);
}

export function refreshForecasts(): Promise<RefreshResponse> {
  return requestJson("/api/refresh", { method: "POST" });
}
