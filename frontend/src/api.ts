import type {
  ForecastRunMeta,
  ResortDetail,
  ResortsOverviewResponse,
} from "./types";

const USE_STATIC =
  import.meta.env.VITE_DATA_MODE === "static" ||
  (!import.meta.env.DEV && !import.meta.env.VITE_API_BASE && import.meta.env.VITE_DATA_MODE !== "api");

const API_BASE = (import.meta.env.VITE_API_BASE as string | undefined) ?? "";
const STATIC_BASE = `${import.meta.env.BASE_URL}data`;

async function requestJson<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, init);
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
  return requestJson(`${API_BASE}/api/health`);
}

export function fetchResorts(): Promise<ResortsOverviewResponse> {
  if (USE_STATIC) {
    return requestJson(`${STATIC_BASE}/resorts.json`, { cache: "no-cache" });
  }
  return requestJson(`${API_BASE}/api/resorts`);
}

export function fetchResortDetail(resortId: string): Promise<ResortDetail> {
  const encodedId = encodeURIComponent(resortId);
  if (USE_STATIC) {
    return requestJson(`${STATIC_BASE}/resorts/${encodedId}.json`, { cache: "no-cache" });
  }
  return requestJson(`${API_BASE}/api/resorts/${encodedId}`);
}
