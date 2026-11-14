import type { BandKey } from "./types";

export type Lang = "en" | "zh";

export const LANG_STORAGE_KEY = "powderconsensus-lang";

export interface UiCopy {
  header: {
    selectResort: string;
    bands: Record<BandKey, string>;
    syncing: string;
    lastUpdated: string;
    switchToLight: string;
    switchToDark: string;
    switchLanguage: string;
    loadingData: string;
    emptyTitle: string;
    emptyDescPrefix: string;
    emptyDescMid: string;
    emptyDescSuffix: string;
  };
  snowpack: {
    title: string;
    subtitle: string;
    sweUnit: string;
    unavailable: string;
  };
  daily: {
    titlePrefix: string;
    subtitle: string;
    colDay: string;
    colSnowMedian: string;
    colQpf: string;
    colSlr: string;
    colTemp: string;
    colWind: string;
    colSnowLevel: string;
    phasePrefix: string;
    slrLabel: string;
    wetSnow: string;
    powderSnow: string;
    tempLabel: string;
    mixed: string;
    rain: string;
    windRiskLabel: string;
    windHold: string;
    windClosed: string;
  };
  hourly: {
    titlePrefix: string;
    subtitle: string;
    rateLabel: string;
    cumLabel: string;
    settledLabel: string;
    tempLabel: string;
    snowLvlLabel: string;
    windLabel: string;
    slrLabel: string;
    panelATitle: string;
    hourlyMedian: string;
    hourlyMax: string;
    cumulativeSnow: string;
    settledDepth: string;
    panelBTitle: string;
    snowLevelLegend: string;
    airTempLegend: string;
    dashedLinesLegend: string;
  };
  models: {
    titlePrefix: string;
    subtitle: string;
    colModel: string;
    colHorizon: string;
    col24h: string;
    col48h: string;
    col72h: string;
    col5d: string;
    col7d: string;
    col72hSlr: string;
    col72hTempWind: string;
    consensusMedian: string;
    minMaxSpread: string;
    rawNativePrefix: string;
    stopsAtTitle: (hours: number) => string;
  };
}

export const COPY: Record<Lang, UiCopy> = {
  en: {
    header: {
      selectResort: "Select ski resort",
      bands: {
        base: "base",
        mid: "mid",
        summit: "summit",
      },
      syncing: "Syncing band details...",
      lastUpdated: "Last updated:",
      switchToLight: "Switch to light mode",
      switchToDark: "Switch to dark mode",
      switchLanguage: "Switch language between Chinese and English",
      loadingData: "Loading forecast data...",
      emptyTitle: "No Forecast Runs Available Yet",
      emptyDescPrefix: "Run ",
      emptyDescMid: " (or trigger the GitHub Actions Pages workflow) to ingest live weather models and populate the dashboard.",
      emptyDescSuffix: "",
    },
    snowpack: {
      title: "Current Base Depth (Natural Snow)",
      subtitle: "Excludes snowmaking & groomed trails",
      sweUnit: "SWE",
      unavailable: "Nearby automated snow telemetry is currently unavailable.",
    },
    daily: {
      titlePrefix: "7-Day Snow Forecast",
      subtitle:
        "Bars show median snowfall (cm) across models; vertical lines show the min–max model range per day",
      colDay: "Local Day",
      colSnowMedian: "Snow Median (Range)",
      colQpf: "QPF",
      colSlr: "SLR",
      colTemp: "Temp Lo / Hi",
      colWind: "Max Wind / Gust",
      colSnowLevel: "Snow Level",
      phasePrefix: "Phase:",
      slrLabel: "SLR:",
      wetSnow: "Wet (<10:1)",
      powderSnow: "Powder (≥15:1)",
      tempLabel: "Temp:",
      mixed: "Mixed",
      rain: "Rain",
      windRiskLabel: "Wind lift risk:",
      windHold: "High lifts may close (≥55 km/h gust)",
      windClosed: "Lifts likely closed (≥72 km/h gust)",
    },
    hourly: {
      titlePrefix: "Hourly Snowfall & Snow Level Forecast",
      subtitle:
        "Hover over the charts for hour-by-hour snowfall rate, storm total, snow level vs. resort elevations, and temperature",
      rateLabel: "Rate:",
      cumLabel: "Cum:",
      settledLabel: "Settled:",
      tempLabel: "Temp:",
      snowLvlLabel: "Snow Lvl:",
      windLabel: "Wind:",
      slrLabel: "SLR",
      panelATitle: "Snowfall Rate (cm/h) & Storm Total",
      hourlyMedian: "Hourly median",
      hourlyMax: "Hourly max",
      cumulativeSnow: "Cumulative snow",
      settledDepth: "Settled depth",
      panelBTitle: "Snow Level (m) vs Resort Elevations & Temp (°C)",
      snowLevelLegend: "Snow level (m)",
      airTempLegend: "Air temp (°C)",
      dashedLinesLegend: "Dashed lines: Base / Mid / Summit (m)",
    },
    models: {
      titlePrefix: "Forecast by Weather Model",
      subtitle:
        "Side-by-side totals using unified snow-density physics (short-range models like HRRR only cover earlier windows)",
      colModel: "Weather Model",
      colHorizon: "Horizon",
      col24h: "24h",
      col48h: "48h",
      col72h: "72h",
      col5d: "5d",
      col7d: "7d",
      col72hSlr: "72h SLR",
      col72hTempWind: "72h Temp · Wind",
      consensusMedian: "Consensus Median",
      minMaxSpread: "min–max spread",
      rawNativePrefix: "raw native",
      stopsAtTitle: (hours) => `Model stops at ${hours}h`,
    },
  },
  zh: {
    header: {
      selectResort: "选择滑雪场",
      bands: {
        base: "山脚",
        mid: "半山",
        summit: "山顶",
      },
      syncing: "正在同步海拔数据...",
      lastUpdated: "更新时间:",
      switchToLight: "切换为浅色模式",
      switchToDark: "切换为深色模式",
      switchLanguage: "切换中英文界面",
      loadingData: "正在加载预报数据...",
      emptyTitle: "暂无可用预报数据",
      emptyDescPrefix: "请运行 ",
      emptyDescMid: "（或触发 GitHub Actions Pages 工作流）以拉取最新气象模型并生成看板数据。",
      emptyDescSuffix: "",
    },
    snowpack: {
      title: "当前自然雪深",
      subtitle: "不含人工造雪与压雪雪道",
      sweUnit: "SWE",
      unavailable: "附近自动雪深监测站数据暂不可用。",
    },
    daily: {
      titlePrefix: "7天降雪预报",
      subtitle: "柱状图为各模型降雪量中位数 (cm)；竖线表示每日各模型的最小–最大范围",
      colDay: "日期",
      colSnowMedian: "降雪中位数 (范围)",
      colQpf: "降水量 QPF",
      colSlr: "雪水比 SLR",
      colTemp: "最低 / 最高温",
      colWind: "最大风速 / 阵风",
      colSnowLevel: "雪线海拔",
      phasePrefix: "降水相态:",
      slrLabel: "SLR:",
      wetSnow: "湿雪 (<10:1)",
      powderSnow: "粉雪 (≥15:1)",
      tempLabel: "相态:",
      mixed: "雨夹雪",
      rain: "降雨",
      windRiskLabel: "大风缆车风险:",
      windHold: "高海拔缆车可能停运 (阵风 ≥55 km/h)",
      windClosed: "缆车极可能停运 (阵风 ≥72 km/h)",
    },
    hourly: {
      titlePrefix: "逐小时降雪与雪线预报",
      subtitle: "悬停图表可查看逐小时降雪率、过程累计降雪、雪线对比雪场海拔及气温变化",
      rateLabel: "降雪率:",
      cumLabel: "累计:",
      settledLabel: "沉降雪深:",
      tempLabel: "气温:",
      snowLvlLabel: "雪线:",
      windLabel: "风速:",
      slrLabel: "SLR",
      panelATitle: "逐小时降雪率 (cm/h) 与过程累计降雪",
      hourlyMedian: "逐小时中位数",
      hourlyMax: "逐小时最大值",
      cumulativeSnow: "累计降雪量",
      settledDepth: "沉降雪深",
      panelBTitle: "雪线高度 (m) 对比雪场海拔与气温 (°C)",
      snowLevelLegend: "雪线高度 (m)",
      airTempLegend: "气温 (°C)",
      dashedLinesLegend: "虚线：山脚 / 半山 / 山顶 (m)",
    },
    models: {
      titlePrefix: "各气象模型降雪预报",
      subtitle: "采用统一雪密度物理模型计算的对比总量（HRRR 等短临模型仅覆盖较早时段）",
      colModel: "气象模型",
      colHorizon: "预报时长",
      col24h: "24h",
      col48h: "48h",
      col72h: "72h",
      col5d: "5天",
      col7d: "7天",
      col72hSlr: "72h 雪水比",
      col72hTempWind: "72h 气温 · 风速",
      consensusMedian: "多模型共识中位数",
      minMaxSpread: "最小–最大范围",
      rawNativePrefix: "原生模型输出",
      stopsAtTitle: (hours) => `该模型最长覆盖至 ${hours}h`,
    },
  },
};
