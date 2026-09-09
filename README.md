# 🥇 XAUUSD Quant Lab

> XAUUSD (Gold) CFD quantitative research — 3 years of 5-minute OHLC data (211k bars) from Gate.io TradFi API, with volatility / risk / seasonality analysis and a ready-to-use **64-indicator dataset** for intraday strategy development.

[中文说明](#中文说明) | [English](#english)

---

<a id="english"></a>

## English

### Dataset

| | |
|---|---|
| Symbol | XAUUSD (Gold vs USD, CFD) |
| Timeframe | **5m** |
| Bars | **211,242** |
| Range | 2023-09-13 → 2026-09-09 (UTC) |
| Columns | `timestamp, datetime_utc, open, high, low, close` |
| Source | Gate.io TradFi public API (`GET /api/v4/tradfi/symbols/XAUUSD/klines`) |
| File | [`data/xauusd_5m.csv`](data/xauusd_5m.csv) (~13 MB) |

### Technical Indicators (64 columns, 5m)

| | |
|---|---|
| File | [`data/xauusd_5m_indicators.csv.gz`](data/xauusd_5m_indicators.csv.gz) (~49 MB, 211,242 rows × 70 cols) |
| Groups | Trend/MA (11) · MACD (3) · Momentum (14) · Volatility/Bands (16) · Trend strength (6) · Statistical (14) |
| Library | [`analysis/indicators_library.py`](analysis/indicators_library.py) — pure pandas/numpy, **no TA-Lib needed** |
| Causality | **No lookahead** — verified: values on truncated history are bit-identical to full-history values |
| Warm-up | First ~200 bars are partially NaN (rolling windows); RSI/StochRSI warm-up starts at bar 13/30 |
| Note | 22 dead-flat holiday candles (o=h=l=c) yield NaN candle-anatomy values (0/0, expected) |

**Indicator list** — Trend: `sma_10/20/50/200`, `ema_9/12/21/26/50/200`, `wma_20` · MACD: `macd_dif/dea/hist` · Momentum: `rsi_6/14/24`, `stoch_k_14`, `stoch_d_14`, `stochrsi_k/d`, `kdj_k/d/j`, `cci_14`, `williams_r_14`, `momentum_10`, `roc_12` · Volatility: `tr`, `atr_7/14/28`, `natr_14`, `bb_up/mid/low/width/pct_b`, `kc_mid/up/low`, `donchian_up/low/mid_20` · Strength: `adx_14`, `plus_di_14`, `minus_di_14`, `aroon_up/down_25`, `psar` · Statistical: `zscore_20`, `linreg_slope_20`, `hv_20`, `hv_96`, `hv_ratio`, `choppiness_14`, `candle_body_pct`, `upper/lower_shadow_pct`, `hl_range_pct`, `gap_pct`, `clv`, `close_vs_ema200_pct`, `close_vs_sma20_pct`.

### Quick Start

```bash
pip install pandas numpy scipy plotly requests

# (optional) refresh / extend the dataset yourself — no API key needed
python scripts/sync_klines.py --symbol XAUUSD --timeframe 5m

# (re)build the 64-indicator dataset from data/xauusd_5m.csv
python analysis/build_indicators.py

# regenerate the interactive HTML report from data/*.csv
python analysis/quant_analysis.py
```

### Key Findings (daily-resolution study, 2020–2026, full report in [`report/`](report/quant_analysis_report.html))

| Metric | Value |
|---|---|
| Annualized return | **+16.05%** |
| Annualized volatility | 17.45% |
| Sharpe / Sortino | 0.92 / 1.17 |
| Max drawdown | **−26.60%** |
| VaR / CVaR (99%, daily) | −3.26% / −4.27% |
| Skew / Excess kurtosis | −0.54 / 5.53 (fat tails) |
| Hurst exponent | 0.481 (≈ random walk) |
| Normality (Jarque-Bera) | rejected (p ≈ 0) |

- **Strong secular uptrend** — gold ~$1,520 (2020) → ~$4,400 (2026).
- **Fat tails** — kurtosis 5.5, left-skewed; normal-based risk models understate tail risk.
- **Volatility clustering** — |returns| autocorrelation significantly positive → GARCH-family / ATR-based position sizing appropriate.
- **Intraday seasonality** — hourly volatility has a stable U-shaped pattern (UTC); exploitable for session-based strategies.

### Repository Layout

```
├── data/xauusd_5m.csv            # 5m OHLC dataset (211k bars)
├── data/xauusd_5m_indicators.csv.gz  # 5m OHLC + 64 indicators (211k bars, gz)
├── scripts/sync_klines.py        # data downloader (public API, no key)
├── analysis/indicators_library.py    # 64-indicator library (pure pandas/numpy)
├── analysis/build_indicators.py  # builds & validates the indicator dataset
├── analysis/quant_analysis.py    # stats + interactive HTML report generator
└── report/quant_analysis_report.html
```

### Data Availability by Timeframe (Gate.io TradFi, probed 2026-09-09)

| TF | Earliest | Bars | Span |
|---|---|---|---|
| 1d | 2020-01-01 | 1,827 | 6.7 y |
| 1h / 4h | 2023-03-20 | 20,569 / 5,481 | 3.5 y |
| **5m** | **2023-09-13** | **211,242** | **3 y** |
| 30m | 2023-09-13 | 35,333 | 3 y |
| 15m | 2026-06-17 | 5,490 | 84 d |
| 1m | 2026-09-03 | 5,496 | 6 d |

`8h / 12h / 3d / 1w / 1M` are **not** supported by the endpoint. 15m history is abnormally short — resample from 5m instead.

### Disclaimer

Market data provided **as is**, for research and education only. Not investment advice.

---

<a id="中文说明"></a>

## 中文说明

### 数据集

- **品种**: XAUUSD 黄金/美元 CFD
- **周期**: 5分钟 · **211,242 根K线** · 覆盖 **2023-09-13 ~ 2026-09-09**(3年,UTC)
- **字段**: `timestamp, datetime_utc, open, high, low, close`
- **来源**: Gate.io TradFi 公开API,无需认证
- **文件**: [`data/xauusd_5m.csv`](data/xauusd_5m.csv)(约13 MB)

### 技术指标数据集(64列,5分钟)

| | |
|---|---|
| 文件 | [`data/xauusd_5m_indicators.csv.gz`](data/xauusd_5m_indicators.csv.gz)(约49 MB,211,242行 × 70列) |
| 分组 | 趋势/均线 (11) · MACD (3) · 动量 (14) · 波动/通道 (16) · 趋势强度 (6) · 统计/微观 (14) |
| 指标库 | [`analysis/indicators_library.py`](analysis/indicators_library.py) — 纯 pandas/numpy 实现,**无需 TA-Lib** |
| 因果性 | **无前视偏差** — 已验证:截断历史计算的值与全量历史计算完全一致 |
| 暖机期 | 前~200根部分为NaN(滚动窗口未满);RSI/StochRSI 分别从第13/30根起有效 |
| 说明 | 22根假日死盘K线(o=h=l=c)的K线形态值为NaN(0/0未定义,属预期) |

**指标清单** — 趋势: `sma_10/20/50/200`、`ema_9/12/21/26/50/200`、`wma_20` · MACD: `macd_dif/dea/hist` · 动量: `rsi_6/14/24`、`stoch_k_14`、`stoch_d_14`、`stochrsi_k/d`、`kdj_k/d/j`、`cci_14`、`williams_r_14`、`momentum_10`、`roc_12` · 波动: `tr`、`atr_7/14/28`、`natr_14`、`bb_up/mid/low/width/pct_b`、`kc_mid/up/low`、`donchian_up/low/mid_20` · 强度: `adx_14`、`plus_di_14`、`minus_di_14`、`aroon_up/down_25`、`psar` · 统计: `zscore_20`、`linreg_slope_20`、`hv_20`、`hv_96`、`hv_ratio`、`choppiness_14`、`candle_body_pct`、`upper/lower_shadow_pct`、`hl_range_pct`、`gap_pct`、`clv`、`close_vs_ema200_pct`、`close_vs_sma20_pct`。

### 快速开始

```bash
pip install pandas numpy scipy plotly requests

# 可选:自行刷新/延长数据(无需API Key)
python scripts/sync_klines.py --symbol XAUUSD --timeframe 5m

# 从 data/xauusd_5m.csv 构建64个指标的数据集(含验证)
python analysis/build_indicators.py

# 从 data/*.csv 重新生成交互式HTML分析报告
python analysis/quant_analysis.py
```

### 核心结论(日线级别 2020–2026,完整报告见 [`report/`](report/quant_analysis_report.html))

| 指标 | 数值 |
|---|---|
| 年化收益率 | **+16.05%** |
| 年化波动率 | 17.45% |
| Sharpe / Sortino | 0.92 / 1.17 |
| 最大回撤 | **−26.60%** |
| VaR / CVaR (99%, 日) | −3.26% / −4.27% |
| 偏度 / 超额峰度 | −0.54 / 5.53(肥尾) |
| Hurst 指数 | 0.481(≈随机游走) |
| 正态性检验 (JB) | 拒绝正态(p ≈ 0) |

- **长期趋势强劲**:金价从2020年约$1,520涨至2026年约$4,400
- **肥尾显著**:峰度5.5、左偏,正态假设会低估尾部风险
- **波动率聚集**:|收益率|自相关显著为正 → 适合GARCH / ATR仓位管理
- **日内季节性**:小时波动率呈稳定U型(UTC),可做时段策略

### 目录结构

```
├── data/xauusd_5m.csv            # 5分钟OHLC数据集(21万根)
├── data/xauusd_5m_indicators.csv.gz  # 5分钟OHLC + 64个指标(压缩)
├── scripts/sync_klines.py        # 数据下载脚本(公开API,无需Key)
├── analysis/indicators_library.py    # 64指标库(纯pandas/numpy)
├── analysis/build_indicators.py  # 指标数据集构建与验证脚本
├── analysis/quant_analysis.py    # 统计分析 + HTML报告生成
└── report/quant_analysis_report.html
```

### 免责声明

数据按"原样"提供,仅供研究与学习使用,不构成投资建议。

---

## License

[MIT](LICENSE)
