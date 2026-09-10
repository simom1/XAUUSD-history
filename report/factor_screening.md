# XAUUSD 5m - Factor Screening Report

> Research-only revision: 2026-03-10 onward is excluded from selection and remains a consumed development set.

- data: `xauusd_5m_indicators.csv.gz` (175,475 bars, 2023-09-13 -> 2026-03-09)
- IS/OOS split: first 70% IS (2023-09-13 -> 2025-06-10), last 30% OOS (2025-06-10 -> 2026-03-09)
- cost model: all-in $0.16/oz round trip ($0.08/side); 1 unit = 100 oz
- data quality: see `report/data_quality_5m.md` (verdict: clean; 22 holiday flat candles -> 88 structural NaN cells in 4 columns)

## Method

1. **Factor universe**: 61 scale-free factors derived from the 64-indicator set (price-level indicators converted to % distance / channel position).
2. **IC study**: monthly Spearman rank IC vs forward returns h in (12, 84, 288) bars (1h / ~7h / ~24h); selection uses IS months only, OOS Spearman reported as stability check.
3. **Grid backtest**: entry when trailing z-score (windows [2016, 6048]) crosses +/-[1.5, 2.5], fixed hold [12, 84] bars, long-when-high (momentum) vs long-when-low (reversal) both evaluated; exact engine accounting (next-open fills, session flat 21:00 UTC / Fri 20:45, entry block 15 min, $0.16 RT cost). Direction & params selected on IS; OOS untouched.

## Fast-model calibration

EMA 9/21 baseline: engine vs vectorized accounting (net $ over full sample): engine $-34,942 vs fast $-34,942 - delta $0.0000 (float noise).

## IC results (h = 84 bars ~ 7h, top 15 by |t|)

| factor | ic_mean | icir | t | pos_pct | is_spr | oos_spr | months |
|---:|---:|---:|---:|---:|---:|---:|---:|
| upper_shadow_pct | +0.0093 | +0.6670 | +3.1300 | +0.7730 | +0.0095 | +0.0029 | 22 |
| clv | -0.0055 | -0.4620 | -2.1700 | +0.3180 | -0.0029 | -0.0069 | 22 |
| tr_pct | -0.0247 | -0.3900 | -1.8300 | +0.3640 | -0.0094 | +0.0278 | 22 |
| hl_range_pct | -0.0246 | -0.3890 | -1.8200 | +0.3640 | -0.0093 | +0.0278 | 22 |
| hv_20 | -0.0310 | -0.3500 | -1.6400 | +0.4550 | -0.0100 | +0.0342 | 22 |
| atr_7_pct | -0.0285 | -0.3320 | -1.5600 | +0.4550 | -0.0081 | +0.0301 | 22 |
| natr_14 | -0.0247 | -0.2740 | -1.2900 | +0.4550 | -0.0046 | +0.0269 | 22 |
| hv_ratio | -0.0200 | -0.2340 | -1.1000 | +0.4550 | -0.0113 | +0.0312 | 22 |
| bb_width | -0.0183 | -0.2220 | -1.0400 | +0.4090 | -0.0015 | +0.0280 | 22 |
| atr_28_pct | -0.0204 | -0.2190 | -1.0300 | +0.4090 | -0.0019 | +0.0241 | 22 |
| vol_percentile | -0.0194 | -0.1870 | -0.8800 | +0.5910 | -0.0123 | +0.0103 | 22 |
| kdj_j | -0.0051 | -0.1720 | -0.8100 | +0.5000 | +0.0019 | -0.0178 | 22 |
| adx_14 | -0.0141 | -0.1680 | -0.7900 | +0.5000 | -0.0065 | -0.0272 | 22 |
| kdj_k | -0.0072 | -0.1600 | -0.7500 | +0.5000 | +0.0027 | -0.0294 | 22 |
| macd_hist_pct | +0.0042 | +0.1570 | +0.7400 | +0.6820 | +0.0051 | -0.0047 | 22 |

(full table: `report/factor_ic_results.csv`, horizons 12/84/288)

## Single-factor grid - top 25 by IS Sharpe (min 150 IS trades)

| rank | factor | win | thr | long_when | hold | is_sharpe | is_pnl | is_trades | is_avg_usd | is_pf | oos_sharpe | oos_pnl | oos_trades | oos_avg_usd | oos_pf |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | aroon_up_25 | 6048 | +1.50 | high | 12 | +2.24 | +31037.00 | 292 | +106.29 | +1.67 | +0.61 | +18514.00 | 202 | +91.65 | +1.12 |
| 2 | atr_28_pct | 2016 | +1.50 | low | 84 | +1.65 | +64012.00 | 393 | +162.88 | +1.35 | +1.25 | +74232.00 | 207 | +358.61 | +1.33 |
| 3 | bb_squeeze | 6048 | +2.50 | high | 84 | +1.55 | +60920.00 | 424 | +143.68 | +1.32 | +0.67 | +31519.00 | 169 | +186.50 | +1.18 |
| 4 | natr_14 | 2016 | +1.50 | low | 84 | +1.37 | +58204.00 | 460 | +126.53 | +1.26 | +0.66 | +39646.00 | 217 | +182.70 | +1.14 |
| 5 | macd_hist_pct | 2016 | +1.50 | low | 84 | +1.37 | +73018.00 | 799 | +90.19 | +1.20 | +0.14 | +9789.00 | 369 | +29.12 | +1.02 |
| 6 | close_vs_ema9 | 2016 | +2.50 | high | 12 | +1.37 | +46292.00 | 1050 | +44.70 | +1.17 | -1.16 | -56771.00 | 433 | -132.60 | +0.84 |
| 7 | bb_squeeze | 2016 | +2.50 | high | 84 | +1.36 | +53593.00 | 435 | +123.20 | +1.28 | +0.67 | +32083.00 | 177 | +181.26 | +1.17 |
| 8 | close_vs_ema12 | 2016 | +2.50 | high | 12 | +1.27 | +41741.00 | 960 | +43.48 | +1.16 | -1.47 | -69678.00 | 401 | -173.76 | +0.80 |
| 9 | di_ratio | 2016 | +1.50 | high | 84 | +1.25 | +53414.00 | 659 | +79.22 | +1.19 | +2.54 | +95977.00 | 249 | +390.30 | +1.58 |
| 10 | close_vs_wma20 | 2016 | +2.50 | low | 84 | +1.24 | +57051.00 | 507 | +112.53 | +1.22 | -0.35 | -21387.00 | 218 | -98.11 | +0.93 |
| 11 | macd_hist_pct | 6048 | +2.50 | low | 84 | +1.23 | +50075.00 | 362 | +138.33 | +1.26 | -0.55 | -32010.00 | 162 | -197.59 | +0.86 |
| 12 | linreg_slope_20 | 2016 | +2.50 | low | 84 | +1.22 | +45220.00 | 316 | +143.10 | +1.30 | -2.18 | -115508.00 | 138 | -837.01 | +0.51 |
| 13 | close_vs_sma10 | 2016 | +2.50 | high | 12 | +1.20 | +39922.00 | 1000 | +40.57 | +1.16 | -1.08 | -51404.00 | 411 | -126.64 | +0.85 |
| 14 | di_ratio | 6048 | +1.50 | high | 84 | +1.18 | +50243.00 | 653 | +76.94 | +1.18 | +2.92 | +109644.00 | 250 | +438.58 | +1.71 |
| 15 | close_vs_sma10 | 2016 | +2.50 | low | 84 | +1.16 | +54764.00 | 549 | +99.59 | +1.20 | -0.81 | -50303.00 | 231 | -217.38 | +0.85 |
| 16 | gap_pct | 6048 | +1.50 | low | 84 | +1.15 | +28986.00 | 203 | +142.79 | +1.35 | +0.67 | +33654.00 | 113 | +297.82 | +1.23 |
| 17 | hv_96 | 6048 | +2.50 | low | 12 | +1.14 | +21193.00 | 293 | +72.33 | +1.27 | +1.24 | +55477.00 | 192 | +288.94 | +1.30 |
| 18 | macd_hist_pct | 2016 | +2.50 | low | 84 | +1.13 | +44874.00 | 362 | +123.96 | +1.25 | +0.16 | +9130.00 | 166 | +55.00 | +1.04 |
| 19 | di_ratio | 6048 | +2.50 | high | 84 | +1.12 | +38502.00 | 401 | +96.01 | +1.23 | +2.15 | +61781.00 | 147 | +420.28 | +1.69 |
| 20 | atr_28_pct | 6048 | +2.50 | low | 12 | +1.12 | +23824.00 | 334 | +71.33 | +1.25 | +1.32 | +61116.00 | 196 | +311.82 | +1.27 |
| 21 | close_vs_wma20 | 6048 | +2.50 | high | 12 | +1.10 | +36236.00 | 890 | +40.71 | +1.15 | -0.96 | -48689.00 | 418 | -116.48 | +0.86 |
| 22 | candle_body_pct | 6048 | +1.50 | high | 84 | +1.10 | +66333.00 | 1314 | +50.54 | +1.12 | -1.82 | -140403.00 | 576 | -243.88 | +0.80 |
| 23 | hv_96 | 2016 | +1.50 | low | 84 | +1.10 | +36794.00 | 289 | +127.31 | +1.28 | +1.02 | +56878.00 | 159 | +357.72 | +1.30 |
| 24 | kc_pos | 6048 | +2.50 | low | 84 | +1.09 | +46323.00 | 508 | +91.19 | +1.20 | -0.43 | -23698.00 | 220 | -107.72 | +0.92 |
| 25 | close_vs_ema12 | 2016 | +2.50 | low | 84 | +1.06 | +49534.00 | 531 | +93.28 | +1.18 | -0.57 | -35445.00 | 229 | -154.78 | +0.89 |

Full grid: `report/factor_grid_results.csv` (864 configs). Columns `is_*`/`oos_*` are in/out-of-sample; `pnl` in USD on 100 oz; `avg_usd` = average NET PnL per trade after the $16 cost hurdle.

## Engine confirmation (top configs, full sample)

| config | engine_pnl | engine_trades | engine_pf | engine_costs | fast_pnl | delta | is_sharpe | oos_sharpe | oos_pnl |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| aroon_up_25 | W6048 T1.5 long@high H12 | +49551.00 | 494 | +1.25 | +7904.00 | +49551.00 | +0.00 | +2.24 | +0.61 | +18514.00 |
| atr_28_pct | W2016 T1.5 long@low H84 | +138244.00 | 600 | +1.34 | +9600.00 | +138244.00 | +0.00 | +1.65 | +1.25 | +74232.00 |
| bb_squeeze | W6048 T2.5 long@high H84 | +92439.00 | 593 | +1.25 | +9488.00 | +92439.00 | +0.00 | +1.55 | +0.67 | +31519.00 |
| natr_14 | W2016 T1.5 long@low H84 | +97850.00 | 677 | +1.20 | +10832.00 | +97850.00 | +0.00 | +1.37 | +0.66 | +39646.00 |
| macd_hist_pct | W2016 T1.5 long@low H84 | +82807.00 | 1168 | +1.10 | +18688.00 | +82807.00 | +0.00 | +1.37 | +0.14 | +9789.00 |
| close_vs_ema9 | W2016 T2.5 long@high H12 | -10479.00 | 1483 | +0.98 | +23728.00 | -10479.00 | +0.00 | +1.37 | -1.16 | -56771.00 |

## Decile profiles (fwd 7h return in bp, IS quantile bins applied to both segments)


**upper_shadow_pct** (monthly-IC t = 3.13, IS spr = 0.00947, OOS spr = 0.00294)

| bin | IS | OOS |
|---:|---:|---:|
| +1.00 | +3.59 | +8.62 |
| +2.00 | +2.62 | +5.34 |
| +3.00 | +3.38 | +7.11 |
| +4.00 | +3.70 | +6.64 |
| +5.00 | +3.23 | +6.85 |
| +6.00 | +4.83 | +9.06 |
| +7.00 | +5.38 | +7.34 |
| +8.00 | +4.02 | +5.66 |
| +9.00 | +4.16 | +8.44 |
| +10.00 | +4.31 | +7.80 |


**clv** (monthly-IC t = -2.17, IS spr = -0.00294, OOS spr = -0.00685)

| bin | IS | OOS |
|---:|---:|---:|
| +1.00 | +3.36 | +9.68 |
| +2.00 | +3.96 | +6.81 |
| +3.00 | +4.25 | +6.54 |
| +4.00 | +4.33 | +6.74 |
| +5.00 | +3.61 | +8.47 |
| +6.00 | +4.19 | +6.61 |
| +7.00 | +4.78 | +7.46 |
| +8.00 | +3.97 | +7.42 |
| +9.00 | +3.39 | +7.00 |
| +10.00 | +3.38 | +6.11 |


**tr_pct** (monthly-IC t = -1.83, IS spr = -0.00938, OOS spr = 0.02784)

| bin | IS | OOS |
|---:|---:|---:|
| +1.00 | +6.07 | +6.61 |
| +2.00 | +4.64 | +6.48 |
| +3.00 | +4.85 | +9.98 |
| +4.00 | +4.05 | +9.96 |
| +5.00 | +4.27 | +9.40 |
| +6.00 | +3.50 | +9.17 |
| +7.00 | +4.13 | +9.34 |
| +8.00 | +4.05 | +7.26 |
| +9.00 | +3.52 | +5.95 |
| +10.00 | +0.16 | +4.60 |


**hl_range_pct** (monthly-IC t = -1.82, IS spr = -0.00927, OOS spr = 0.02777)

| bin | IS | OOS |
|---:|---:|---:|
| +1.00 | +6.08 | +6.53 |
| +2.00 | +4.66 | +6.44 |
| +3.00 | +4.80 | +9.96 |
| +4.00 | +4.02 | +10.03 |
| +5.00 | +4.26 | +9.46 |
| +6.00 | +3.58 | +8.99 |
| +7.00 | +4.04 | +9.42 |
| +8.00 | +4.05 | +7.34 |
| +9.00 | +3.62 | +6.04 |
| +10.00 | +0.13 | +4.52 |


**hv_20** (monthly-IC t = -1.64, IS spr = -0.01002, OOS spr = 0.03421)

| bin | IS | OOS |
|---:|---:|---:|
| +1.00 | +6.60 | +7.71 |
| +2.00 | +4.27 | +8.91 |
| +3.00 | +5.50 | +8.62 |
| +4.00 | +6.42 | +7.85 |
| +5.00 | +3.69 | +7.20 |
| +6.00 | +3.62 | +6.19 |
| +7.00 | +0.40 | +9.80 |
| +8.00 | +1.50 | +9.69 |
| +9.00 | +3.49 | +8.26 |
| +10.00 | +3.77 | +4.04 |

## Caveats

- **Multiple testing**: 864 IS configurations were ranked; the best IS Sharpe is inflated by selection. The OOS columns are the honest check (same sign & similar magnitude = robust).
- IC uses overlapping forward returns (monthly blocks mitigate but do not eliminate cross-correlation); treat |t| < 3 as noise given ~27 IS months.
- Rolling z-scores need a warm-up (min_periods = W/2); early IS bars are inactive for some configs.
- 22 holiday flat candles produce structural NaNs in 4 factors; NaN never generates entries (comparisons with NaN are False).
- No volume data exists on Gate.io TradFi klines; volume factors out of scope.
- Margin/leverage not modeled (fixed 100 oz ~ 2.6x notional on $100k).
