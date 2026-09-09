# 🥇 XAUUSD Quant Lab

> XAUUSD (Gold) CFD quantitative research — 3 years of 5-minute OHLC data (211k bars) from Gate.io TradFi API, volatility / risk / seasonality analysis, a **64-indicator dataset** (no-lookahead verified), and a **cost-aware event-driven backtest framework** for intraday strategy development.

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

### Backtest Framework (event-driven, cost-aware)

| | |
|---|---|
| Engine | [`backtest/engine.py`](backtest/engine.py) — signal at bar close → fill at **next bar open**; SL/TP checked intrabar (stop-first on ties); daily flat 20:55 UTC (Fri 20:45) |
| Costs | **$0.16 /oz round-trip all-in** (spread + slippage + commission, Gate.io actual) → $0.08 per side |
| Validation | synthetic PnL hand-checks + no-lookahead **prefix-consistency check** (truncated-history replay must be bit-identical) |
| Runner | [`scripts/run_backtest.py`](scripts/run_backtest.py) |

```bash
python scripts/run_backtest.py --strategy ema_cross_9_21 --save
python scripts/run_backtest.py --strategy donchian_breakout_20 --sl 5.0 --tp 8.0
```

**Baseline results (2023-09 → 2026-09, fixed 100 oz, $100k start):**

| strategy | return | Sharpe | PF | win rate | trades | friction paid |
|---|---:|---:|---:|---:|---:|---:|
| EMA cross 9/21 | **+51.6%** | 0.50 | 1.02 | 29.1% | 9,323 | $149k |
| Donchian breakout 20 | −44.5% | −0.52 | 0.98 | 35.0% | 5,221 | $84k |

> Key lesson: at 100 oz each round trip costs **$16** → 10 trades/day ≈ $160/day
> ≈ $58k/year of friction on $100k capital. Any intraday edge must clear this
> bar first — which is exactly what the feature-screening step measures.

### Factor Screening & Walk-Forward Research

| | |
|---|---|
| Stage 1 — IC + grid | [`scripts/run_screening.py`](scripts/run_screening.py) · [`analysis/factor_screening.py`](analysis/factor_screening.py) — Spearman IC with monthly Newey-West t-stats over all 64 indicators, then a per-factor z-score grid (window W × threshold T × hold H) with IS/OOS 70/30 split and the $16/trade cost gate |
| Stage 2 — combos + WF | [`scripts/run_combo_matrix.py`](scripts/run_combo_matrix.py) · [`analysis/combo_screening.py`](analysis/combo_screening.py) — **one-sided** re-test + pairwise AND combos, ranked by 4-fold walk-forward (expanding train, 6-month test windows); the final 6 months (2026-03-10 → 2026-09-09) are **sealed as an untouchable holdout** |
| Reports | [`report/factor_screening.md`](report/factor_screening.md) · [`report/combo_matrix.md`](report/combo_matrix.md) · `factor_ic_results.csv` · `factor_grid_results.csv` · `combo_wf_results.csv` |

**Locked candidate (engine-verified, replay delta $0.00)** — research slice 2023-09 → 2026-03:

| spec | side | res Sharpe | avg $/trade | trades | res maxDD |
|---|---|---:|---:|---:|---:|
| `plus_di_14` · W6048 · z>+1.5 · hold 120 bars (10h) | long | **2.51** | +$293 | 906 | −$27.9k |

All 4 walk-forward folds positive (test PnL +$2.5k / +$39k / +$75k / +$139k, Sharpe 0.18 → 3.69).
Full-pool WF simulation (540 configs, re-picked each fold by train Sharpe): Sharpe 0.69, avg +$271/trade.

**Findings / honest lessons:**

- The Stage-1 grid ran **two-sided** configs (long at z>+T *and* short at z<−T). Stage-2's
  one-sided decomposition corrects the attribution: `plus_di`'s long leg (+$160k research)
  was masked by its losing short leg in the both-side config; `aroon`'s Stage-1 profit came
  mostly from its **short** leg; `gap_pct`'s profit is all in its long leg.
- Pairwise combos are **redundant**: `aroon ∧ plus_di` at T=1.25 keeps 89–96% of the
  plus_di-only trades at slightly lower Sharpe; at T=1.5 the overlap collapses to <6%.
- Exploratory (not locked): `aroon_up_25` short (z<−1.5, W6048) — res Sharpe 1.42,
  +$724/trade, 170 trades, positive in all 4 folds.

Judgement day — run the locked spec against the sealed holdout **once**, after research is frozen:

```bash
python scripts/run_combo_matrix.py --final
```

### Quick Start

```bash
pip install pandas numpy scipy plotly requests

# (optional) refresh / extend the dataset yourself — no API key needed
python scripts/sync_klines.py --symbol XAUUSD --timeframe 5m

# (re)build the 64-indicator dataset from data/xauusd_5m.csv
python analysis/build_indicators.py

# regenerate the interactive HTML report from data/*.csv
python analysis/quant_analysis.py

# run a validated baseline backtest (cost-aware)
python scripts/run_backtest.py --strategy ema_cross_9_21 --save

# stage 1: IC screen + per-factor grid (IS/OOS 70/30)
python scripts/run_screening.py

# stage 2: one-sided combos + 4-fold walk-forward (seals the last 6 months)
python scripts/run_combo_matrix.py
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
├── analysis/data_quality.py      # holiday / dead-bar QC (report/data_quality_5m.md)
├── analysis/factor_screening.py  # IC + grid machinery (fast engine-calibrated accounting)
├── analysis/combo_screening.py   # one-sided combos + walk-forward engine
├── backtest/                     # event-driven backtest engine
│   ├── engine.py · config.py · metrics.py · validate.py
├── strategies/baseline.py        # ema_cross_9_21, donchian_breakout_20
├── scripts/run_backtest.py       # backtest runner (validated)
├── scripts/run_screening.py      # stage-1 runner (IC + grid)
├── scripts/run_combo_matrix.py   # stage-2 runner (walk-forward + sealed holdout)
└── report/quant_analysis_report.html + backtest_*.md + factor_screening.md + combo_matrix.md
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

### 回测框架(事件驱动、计入真实成本)

| | |
|---|---|
| 引擎 | [`backtest/engine.py`](backtest/engine.py) — 信号在bar收盘产生 → **下一根bar开盘价成交**;SL/TP盘中按高低点触发(双触发时止损优先);每日20:55 UTC强平(周五20:45) |
| 成本 | **$0.16/oz 全包往返**(点差+滑点+佣金,Gate.io实际) → 每边$0.08 |
| 验证 | 合成盈亏手工对账 + **无前视一致性检查**(截断历史重放,权益路径逐位一致) |
| 运行 | [`scripts/run_backtest.py`](scripts/run_backtest.py) |

```bash
python scripts/run_backtest.py --strategy ema_cross_9_21 --save
python scripts/run_backtest.py --strategy donchian_breakout_20 --sl 5.0 --tp 8.0
```

**基线结果(2023-09 → 2026-09,固定100盎司,初始$100k):**

| 策略 | 收益 | Sharpe | PF | 胜率 | 笔数 | 摩擦成本 |
|---|---:|---:|---:|---:|---:|---:|
| EMA 9/21 交叉 | **+51.6%** | 0.50 | 1.02 | 29.1% | 9,323 | $149k |
| 唐奇安20突破 | −44.5% | −0.52 | 0.98 | 35.0% | 5,221 | $84k |

> 关键教训:100盎司下每笔往返成本**$16** → 每天10笔 ≈ $160/天 ≈ 每年$58k(本金$100k)。日内策略的边际收益必须先跨过这道门槛——这正是下一步特征筛选要量化的东西。

### 因子筛选与 Walk-Forward 研究

| | |
|---|---|
| 第一阶段 — IC + 网格 | [`scripts/run_screening.py`](scripts/run_screening.py) · [`analysis/factor_screening.py`](analysis/factor_screening.py) — 64个指标的 Spearman IC(月度 Newey-West t 检验)+ 单因子 z 分数网格(窗口 W × 阈值 T × 持仓 H),IS/OOS 七三分割,$16/笔成本门槛 |
| 第二阶段 — 组合 + WF | [`scripts/run_combo_matrix.py`](scripts/run_combo_matrix.py) · [`analysis/combo_screening.py`](analysis/combo_screening.py) — **单边**复测 + 两两 AND 组合,按 4 折 walk-forward(扩张训练窗、6个月测试窗)排序;最后6个月(2026-03-10 → 2026-09-09)**封存为终审数据,研究期间禁止触碰** |
| 报告 | [`report/factor_screening.md`](report/factor_screening.md) · [`report/combo_matrix.md`](report/combo_matrix.md) · `factor_ic_results.csv` · `factor_grid_results.csv` · `combo_wf_results.csv` |

**锁定候选(引擎逐笔复核,重放误差 $0.00)** — 研究切片 2023-09 → 2026-03:

| 规格 | 方向 | 研究Sharpe | 均$/笔 | 笔数 | 研究最大回撤 |
|---|---|---:|---:|---:|---:|
| `plus_di_14` · W6048 · z>+1.5 · 持仓120根(10小时) | 做多 | **2.51** | +$293 | 906 | −$27.9k |

4 折 walk-forward 全部为正(测试PnL +$2.5k / +$39k / +$75k / +$139k,Sharpe 0.18 → 3.69)。
全池 WF 模拟(540个配置,每折按训练Sharpe重选):Sharpe 0.69,均 +$271/笔。

**结论与教训:**

- 第一阶段网格是**双向**配置(z>+T 做多同时 z<−T 做空)。第二阶段的单边分解修正了归因:`plus_di` 的多头腿(研究期 +$160k)在双向配置里被亏损的空头腿掩盖;`aroon` 第一阶段的利润主要来自**空头腿**;`gap_pct` 的利润全部在多头腿。
- 两两组合**冗余**:`aroon ∧ plus_di` 在 T=1.25 时保留 plus_di 单独交易的 89–96%,Sharpe 还略低;T=1.5 时重叠骤降到 <6%(笔数太少)。
- 探索性(未锁定):`aroon_up_25` 做空(z<−1.5, W6048)— 研究Sharpe 1.42,+$724/笔,170笔,4折全正。

审判日 — 研究冻结后,对封存数据运行锁定规格**一次**:

```bash
python scripts/run_combo_matrix.py --final
```

### 快速开始

```bash
pip install pandas numpy scipy plotly requests

# 可选:自行刷新/延长数据(无需API Key)
python scripts/sync_klines.py --symbol XAUUSD --timeframe 5m

# 从 data/xauusd_5m.csv 构建64个指标的数据集(含验证)
python analysis/build_indicators.py

# 从 data/*.csv 重新生成交互式HTML分析报告
python analysis/quant_analysis.py

# 运行基线回测(含无前视验证)
python scripts/run_backtest.py --strategy ema_cross_9_21 --save

# 第一阶段:IC筛选 + 单因子网格(IS/OOS 七三分割)
python scripts/run_screening.py

# 第二阶段:单边组合矩阵 + 4折walk-forward(封存最后6个月)
python scripts/run_combo_matrix.py
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
├── analysis/data_quality.py      # 假日死盘QC(report/data_quality_5m.md)
├── analysis/factor_screening.py  # IC + 网格机制(快速记账,与引擎校准到$0.00)
├── analysis/combo_screening.py   # 单边组合 + walk-forward引擎
├── backtest/                     # 事件驱动回测引擎
│   ├── engine.py · config.py · metrics.py · validate.py
├── strategies/baseline.py        # 基线策略:ema_cross_9_21 / donchian_breakout_20
├── scripts/run_backtest.py       # 回测运行器(含验证)
├── scripts/run_screening.py      # 第一阶段运行器(IC + 网格)
├── scripts/run_combo_matrix.py   # 第二阶段运行器(walk-forward + 封存终审)
└── report/quant_analysis_report.html + backtest_*.md + factor_screening.md + combo_matrix.md
```

### 免责声明

数据按"原样"提供,仅供研究与学习使用,不构成投资建议。

---

## License

[MIT](LICENSE)
