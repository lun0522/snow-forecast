export type BandKey = "base" | "mid" | "summit";
export type WindowKey = "24h" | "48h" | "72h" | "120h" | "168h";
export type ConfidenceLevel = "high" | "medium" | "low";
export type RainSnowRisk = "snow" | "mixed" | "rain";

export interface ForecastRunMeta {
  id: number;
  fetched_at_utc: string;
  created_at_utc: string;
  status: string;
  models_requested: string[];
  notes: string | null;
}

export interface WindowSummary {
  snow_min_in: number;
  snow_median_in: number;
  snow_max_in: number;
  native_snow_median_in: number;
  precip_median_in: number;
  avg_slr: number;
  snow_fraction: number;
  rain_snow_risk: RainSnowRisk;
  temp_min_f: number | null;
  temp_max_f: number | null;
  max_wind_mph: number | null;
  max_gust_mph: number | null;
  snow_level_min_ft: number | null;
  snow_level_max_ft: number | null;
  model_count: number;
  models_used: string[];
  confidence: ConfidenceLevel;
  confidence_score: number;
}

export interface DailyBucket {
  date: string;
  day_name: string;
  hours_in_bucket: number;
  is_partial: boolean;
  snow_min_in: number;
  snow_median_in: number;
  snow_max_in: number;
  native_snow_median_in: number;
  precip_median_in: number;
  avg_slr: number;
  snow_fraction: number;
  rain_snow_risk: RainSnowRisk;
  temp_min_f: number | null;
  temp_max_f: number | null;
  max_wind_mph: number | null;
  max_gust_mph: number | null;
  snow_level_min_ft: number | null;
  snow_level_max_ft: number | null;
  model_count: number;
  models_used: string[];
  confidence: ConfidenceLevel;
  confidence_score: number;
}

export interface HourlyConsensusPoint {
  time_utc: string;
  time_local: string;
  local_date: string;
  snow_min_in: number;
  snow_median_in: number;
  snow_max_in: number;
  settled_snow_in: number;
  precip_median_in: number;
  temp_median_f: number | null;
  temp_min_f: number | null;
  temp_max_f: number | null;
  wind_median_mph: number | null;
  wind_gust_max_mph: number | null;
  snow_level_median_ft: number | null;
  slr_median: number | null;
  snow_fraction_median: number | null;
  model_count: number;
}

export interface ModelWindowSummary {
  covered_hours: number;
  physics_snow_in: number;
  native_snow_in: number;
  precip_in: number;
  settled_peak_in: number;
  avg_slr: number;
  snow_fraction: number;
  rain_snow_risk: RainSnowRisk;
  temp_min_f: number | null;
  temp_max_f: number | null;
  max_wind_mph: number | null;
  max_gust_mph: number | null;
  snow_level_min_ft: number | null;
  snow_level_max_ft: number | null;
}

export interface ModelDetail {
  id: string;
  display_name: string;
  coverage_hours: number;
  windows: Record<WindowKey, ModelWindowSummary>;
  hourly: Array<{
    time_utc: string;
    covered: boolean;
    physics_snow_in: number | null;
    native_snow_in: number | null;
    settled_snow_in: number | null;
    temp_f: number | null;
    slr: number | null;
    wind_mph: number | null;
    snow_level_ft: number | null;
  }>;
}

export interface BandSummary {
  label: string;
  elevation_ft: number;
  windows: Record<WindowKey, WindowSummary>;
}

export interface BandDetail extends BandSummary {
  elevation_m: number | null;
  daily: DailyBucket[];
  hourly: HourlyConsensusPoint[];
  models: Record<string, ModelDetail>;
}

export interface ResortSummary {
  id: string;
  name: string;
  region: string;
  state: string;
  timezone: string;
  fetched_at_utc: string;
  run_id?: number;
  bands: Record<BandKey, BandSummary>;
  run_delta: {
    previous_run_at_utc: string;
    summit_72h_in: number | null;
    summit_168h_in: number | null;
  } | null;
}

export interface ResortDetail {
  id: string;
  name: string;
  region: string;
  state: string;
  timezone: string;
  fetched_at_utc: string;
  anchor_utc: string;
  run_id?: number;
  bands: Record<BandKey, BandDetail>;
}

export interface ResortsOverviewResponse {
  run: ForecastRunMeta | null;
  resorts: ResortSummary[];
}

export interface RefreshResponse {
  status: string;
  run_id: number;
  fetched_at_utc: string;
  resorts_count: number;
  resorts: ResortSummary[];
}
