import type { BandKey } from "./types";

export type Lang = "en" | "zh";

export const LANG_STORAGE_KEY = "powderconsensus-lang";

export interface UiCopy {
  header: {
    selectResort: string;
    elevationAria: string;
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
    colStation: string;
    colElevation: string;
    colDistance: string;
    colBaseDepth: string;
    colChange24h: string;
    colSwe: string;
    colObserved: string;
    sweTooltip: string;
    unavailable: string;
  };
  daily: {
    titlePrefix: string;
    subtitle: string;
    legendMedian: string;
    legendRange: string;
    colDay: string;
    colSnowMedian: string;
    colSlr: string;
    slrTooltip: string;
    colTemp: string;
    colWind: string;
    phasePrefix: string;
    wetSnow: string;
    powderSnow: string;
    tempLegendHeading: string;
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
    dashedLinesLegend: string;
    bandSummit: string;
    bandMid: string;
    bandBase: string;
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
    modelGuideTitle: string;
    modelDescriptions: Record<string, string>;
    expandModels: (count: number) => string;
    collapseModels: string;
  };
}

export const COPY: Record<Lang, UiCopy> = {
  en: {
    header: {
      selectResort: "Select ski resort",
      elevationAria: "Select elevation band",
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
      colStation: "Station",
      colElevation: "Elevation",
      colDistance: "Distance",
      colBaseDepth: "Base Depth",
      colChange24h: "24h Change",
      colSwe: "SWE",
      colObserved: "Observed",
      sweTooltip:
        "Snow Water Equivalent — the depth of liquid water contained in the natural snowpack if melted. Higher SWE for a given depth indicates a denser, more durable base.",
      unavailable: "Nearby automated snow telemetry is currently unavailable.",
    },
    daily: {
      titlePrefix: "7-Day Snow Forecast",
      subtitle:
        "Bars show daily median snowfall (cm); shaded bands show the min–max model prediction range",
      legendMedian: "Daily median",
      legendRange: "Model prediction range (min–max)",
      colDay: "Local Day",
      colSnowMedian: "Snow Median (Range)",
      colSlr: "SLR",
      slrTooltip:
        "Snow-to-Liquid Ratio — units of snow depth per 1 unit of liquid water (e.g., 15:1 = 15 cm snow per 10 mm water).",
      colTemp: "Temp Lo / Hi",
      colWind: "Max Wind / Gust",
      phasePrefix: "Phase:",
      wetSnow: "Wet (<10:1)",
      powderSnow: "Powder (≥15:1)",
      tempLegendHeading: "Precipitation phase:",
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
      cumulativeSnow: "Cumulative snow median",
      settledDepth: "Settled depth median",
      panelBTitle: "Snow Level (m) vs Resort Elevations",
      snowLevelLegend: "Snow level (m)",
      dashedLinesLegend: "Dashed lines: Base / Mid / Summit (m)",
      bandSummit: "Summit",
      bandMid: "Mid",
      bandBase: "Base",
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
      modelGuideTitle: "Model Notes",
      modelDescriptions: {
        ecmwf_ifs025:
          "European Centre (ECMWF) global medium-range model; widely regarded as a benchmark for multi-day storm tracks.",
        ncep_nbm_conus:
          "NOAA National Blend of Models (2.5 km CONUS), statistically calibrated for mountain terrain precipitation and temperatures.",
        gfs_global:
          "US NOAA Global Forecast System updated four times daily; tracks broad Pacific moisture plumes over 7+ days.",
        gem_global:
          "Environment Canada global model (GDPS), often strong at timing cold fronts across North America.",
        icon_global:
          "German Weather Service (DWD) global icosahedral-grid model providing an independent European physics perspective.",
        met_no:
          "Norwegian Meteorological Institute Locationforecast combining high-res ECMWF output (~9 km) with altitude lapse-rate adjustments.",
        nws_gridpoints:
          "Official US National Weather Service forecaster-edited 2.5 km digital grid (NDFD/NBM) incorporating local mountain office expertise.",
        gfs_hrrr:
          "High-Resolution Rapid Refresh (3 km) updated hourly; excels at short-range orographic lift and banded snow rates (~48h max).",
      },
      expandModels: (count) => `Expand (${count} models)`,
      collapseModels: "Collapse",
    },
  },
  zh: {
    header: {
      selectResort: "选择滑雪场",
      elevationAria: "选择海拔区域",
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
      colStation: "监测站",
      colElevation: "海拔",
      colDistance: "距离",
      colBaseDepth: "自然雪深",
      colChange24h: "24h 变化",
      colSwe: "雪水当量 SWE",
      colObserved: "实测时间",
      sweTooltip:
        "雪水当量 (Snow Water Equivalent)：将自然积雪全部融化后折合的液态水深度。同雪深下 SWE 越高，说明雪层越紧实耐久。",
      unavailable: "附近自动雪深监测站数据暂不可用。",
    },
    daily: {
      titlePrefix: "7天降雪预报",
      subtitle: "实心柱状为各模型每日降雪中位数 (cm)；浅色背景带表示模型最小–最大预测范围",
      legendMedian: "每日中位数",
      legendRange: "模型预测范围 (最小–最大)",
      colDay: "日期",
      colSnowMedian: "降雪中位数 (范围)",
      colSlr: "雪水比 SLR",
      slrTooltip:
        "雪水比 (Snow-to-Liquid Ratio)：每 1 份液态水可形成的降雪厚度（如 15:1 表示 10 mm 水对应 15 cm 雪）。",
      colTemp: "最低 / 最高温",
      colWind: "最大风速 / 阵风",
      phasePrefix: "降水相态:",
      wetSnow: "湿雪 (<10:1)",
      powderSnow: "粉雪 (≥15:1)",
      tempLegendHeading: "降水相态:",
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
      cumulativeSnow: "累计降雪中位数",
      settledDepth: "沉降雪深中位数",
      panelBTitle: "雪线高度 (m) 对比雪场海拔",
      snowLevelLegend: "雪线高度 (m)",
      dashedLinesLegend: "虚线：山脚 / 半山 / 山顶 (m)",
      bandSummit: "山顶",
      bandMid: "半山",
      bandBase: "山脚",
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
      modelGuideTitle: "模型说明",
      modelDescriptions: {
        ecmwf_ifs025:
          "欧洲中期天气预报中心 (ECMWF) 全球模式，被公认为多日大尺度风暴路径预报的行业基准。",
        ncep_nbm_conus:
          "美国 NOAA 多模型融合预报 (NBM, 2.5 km)，针对美国本土山地地形的降水与气温进行了统计校准。",
        gfs_global:
          "美国 NOAA 主力全球预报系统 (GFS)，每日更新四次，擅长捕捉未来 7 天以上的大范围太平洋水汽输送。",
        gem_global:
          "加拿大气象局 (CMC) 全球模式 (GEM)，对北美冷锋推进节奏和冷空气过程把握较好。",
        icon_global:
          "德国气象局 (DWD) 约 11 km 全球模式 (ICON)，提供独立于 ECMWF 与 NOAA 的欧系物理参考。",
        met_no:
          "挪威气象研究所 Locationforecast，结合约 9 km 高分辨率 ECMWF 数据与目标海拔直减率进行气温/降雪订正。",
        nws_gridpoints:
          "美国国家气象局 (NWS) 官方 2.5 km 精细格点预报 (NDFD)，融入当地气象台站预报员对高山地形的订正判断。",
        gfs_hrrr:
          "美国高分辨率快速更新短临模式 (HRRR, 3 km)，逐小时更新，擅长捕捉短期地形抬升与局地强降雪带（最长约 48h）。",
      },
      expandModels: (count) => `展开 (${count} 个模型)`,
      collapseModels: "收起",
    },
  },
};
