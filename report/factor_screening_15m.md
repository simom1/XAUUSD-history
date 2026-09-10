# XAUUSD 15m - Factor Screening Report

> Research-only revision: 2026-03-10 onward is excluded from selection and remains a consumed development set.

- data: `xauusd_15m_indicators.csv.gz` (58,731 bars, 2023-09-13 -> 2026-03-09)
- IS/OOS split: first 70% IS (2023-09-13 -> 2025-06-10), last 30% OOS (2025-06-10 -> 2026-03-09)
- cost model: all-in $0.16/oz round trip ($0.08/side); 1 unit = 1 oz
- data quality: see `report/data_quality_5m.md` (verdict: clean; 22 holiday flat candles -> 88 structural NaN cells in 4 columns)

## Method

1. **Factor universe**: 61 scale-free factors derived from the 64-indicator set (price-level indicators converted to % distance / channel position).
2. **IC study**: monthly Spearman rank IC vs forward returns h in (12, 84, 288) bars (15m bars -> 3h / 21h / 72h); selection uses IS months only, OOS Spearman reported as stability check.
3. **Grid backtest**: entry when trailing z-score (windows [672, 2016]) crosses +/-[1.5, 2.5], fixed hold [4, 28] bars, long-when-high (momentum) vs long-when-low (reversal) both evaluated; exact engine accounting (next-open fills, session flat 21:00 UTC / Fri 20:45, entry block 15 min, $0.16 RT cost). Direction & params selected on IS; OOS untouched.

## Fast-model calibration

EMA 9/21 baseline: engine vs vectorized accounting (net $ over full sample): engine $1,093 vs fast $1,093 - delta $0.0000 (float noise).

## IC results (h = 84 bars ~ 7h, top 15 by |t|)

| factor | ic_mean | icir | t | pos_pct | is_spr | oos_spr | months |
|---:|---:|---:|---:|---:|---:|---:|---:|
| hl_range_pct | -0.0308 | -0.4820 | -2.2600 | +0.3640 | -0.0181 | -0.0105 | 22 |
| tr_pct | -0.0306 | -0.4780 | -2.2400 | +0.3640 | -0.0180 | -0.0105 | 22 |
| atr_28_pct | -0.0659 | -0.4590 | -2.1500 | +0.2730 | -0.0410 | -0.0134 | 22 |
| upper_shadow_pct | +0.0119 | +0.4390 | +2.0600 | +0.5910 | +0.0127 | +0.0023 | 22 |
| hv_20 | -0.0440 | -0.4050 | -1.9000 | +0.4550 | -0.0330 | +0.0014 | 22 |
| hv_96 | -0.0759 | -0.3980 | -1.8700 | +0.4090 | -0.0477 | +0.0131 | 22 |
| clv | -0.0068 | -0.3890 | -1.8300 | +0.5000 | -0.0030 | -0.0055 | 22 |
| natr_14 | -0.0487 | -0.3800 | -1.7800 | +0.3640 | -0.0327 | -0.0134 | 22 |
| bb_width | -0.0338 | -0.3580 | -1.6800 | +0.3180 | -0.0251 | -0.0184 | 22 |
| atr_7_pct | -0.0391 | -0.3520 | -1.6500 | +0.4090 | -0.0253 | -0.0135 | 22 |
| lower_shadow_pct | -0.0087 | -0.3250 | -1.5200 | +0.4090 | -0.0084 | -0.0128 | 22 |
| choppiness_14 | +0.0135 | +0.2750 | +1.2900 | +0.4550 | +0.0098 | +0.0245 | 22 |
| minus_di_14 | -0.0190 | -0.1830 | -0.8600 | +0.4550 | -0.0336 | -0.0535 | 22 |
| close_vs_sma200 | -0.0265 | -0.1480 | -0.6900 | +0.4090 | +0.0096 | +0.0148 | 22 |
| di_spread | +0.0139 | +0.1460 | +0.6900 | +0.5910 | +0.0332 | +0.0505 | 22 |

(full table: `report/factor_ic_results_15m.csv`, horizons 12/84/288)

## Single-factor grid - top 25 by IS Sharpe (min 150 IS trades)

| rank | factor | win | thr | long_when | hold | is_sharpe | is_pnl | is_trades | is_avg_usd | is_pf | oos_sharpe | oos_pnl | oos_trades | oos_avg_usd | oos_pf |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | hv_96 | 2016 | +2.50 | low | 4 | +2.29 | +421.00 | 286 | +1.47 | +1.71 | +2.23 | +1011.00 | 207 | +4.88 | +1.53 |
| 2 | atr_28_pct | 2016 | +2.50 | low | 4 | +2.22 | +415.00 | 282 | +1.47 | +1.65 | +1.67 | +747.00 | 191 | +3.91 | +1.43 |
| 3 | hv_96 | 672 | +2.50 | low | 4 | +2.15 | +424.00 | 427 | +0.99 | +1.56 | +2.31 | +910.00 | 205 | +4.44 | +1.65 |
| 4 | macd_hist_pct | 672 | +2.50 | low | 28 | +1.93 | +574.00 | 201 | +2.79 | +1.57 | +0.95 | +434.00 | 81 | +5.53 | +1.35 |
| 5 | macd_hist_pct | 2016 | +2.50 | low | 28 | +1.91 | +572.00 | 185 | +3.09 | +1.67 | +0.73 | +362.00 | 86 | +4.21 | +1.31 |
| 6 | hv_96 | 672 | +1.50 | low | 4 | +1.80 | +546.00 | 1423 | +0.39 | +1.22 | +1.71 | +872.00 | 730 | +1.19 | +1.22 |
| 7 | psar_dist_pct | 2016 | +1.50 | low | 28 | +1.66 | +792.00 | 550 | +1.44 | +1.30 | +0.26 | +169.00 | 264 | +0.64 | +1.05 |
| 8 | atr_7_pct | 672 | +2.50 | low | 4 | +1.61 | +364.00 | 330 | +1.10 | +1.38 | -0.40 | -153.00 | 163 | -0.94 | +0.91 |
| 9 | atr_7_pct | 672 | +1.50 | low | 28 | +1.52 | +619.00 | 411 | +1.51 | +1.32 | +0.76 | +453.00 | 205 | +2.21 | +1.17 |
| 10 | bb_width | 672 | +1.50 | low | 28 | +1.48 | +499.00 | 284 | +1.76 | +1.38 | -0.49 | -241.00 | 145 | -1.66 | +0.88 |
| 11 | hv_96 | 672 | +1.50 | low | 28 | +1.48 | +540.00 | 343 | +1.55 | +1.36 | +1.38 | +784.00 | 164 | +4.82 | +1.41 |
| 12 | macd_hist_pct | 2016 | +2.50 | low | 4 | +1.45 | +308.00 | 317 | +0.97 | +1.36 | +2.25 | +872.00 | 138 | +6.32 | +1.75 |
| 13 | natr_14 | 672 | +1.50 | low | 28 | +1.44 | +544.00 | 368 | +1.48 | +1.32 | +1.08 | +635.00 | 188 | +3.38 | +1.29 |
| 14 | vol_percentile | 2016 | +1.50 | low | 28 | +1.40 | +588.00 | 598 | +0.98 | +1.25 | -1.62 | -732.00 | 248 | -2.95 | +0.73 |
| 15 | hv_96 | 2016 | +1.50 | low | 4 | +1.33 | +351.00 | 1012 | +0.35 | +1.17 | +1.38 | +678.00 | 547 | +1.24 | +1.22 |
| 16 | upper_shadow_pct | 2016 | +1.50 | high | 28 | +1.31 | +716.00 | 1060 | +0.68 | +1.17 | +0.24 | +152.00 | 476 | +0.31 | +1.03 |
| 17 | atr_28_pct | 672 | +1.50 | low | 28 | +1.30 | +466.00 | 339 | +1.38 | +1.31 | +1.70 | +1001.00 | 180 | +5.56 | +1.54 |
| 18 | natr_14 | 672 | +1.50 | low | 4 | +1.28 | +388.00 | 1060 | +0.37 | +1.17 | +1.01 | +501.00 | 560 | +0.89 | +1.14 |
| 19 | macd_hist_pct | 672 | +2.50 | low | 4 | +1.23 | +253.00 | 323 | +0.78 | +1.28 | +1.98 | +644.00 | 130 | +4.95 | +1.75 |
| 20 | close_vs_sma200 | 672 | +1.50 | high | 28 | +1.21 | +491.00 | 449 | +1.09 | +1.26 | +1.31 | +716.00 | 197 | +3.64 | +1.33 |
| 21 | atr_7_pct | 672 | +1.50 | low | 4 | +1.19 | +383.00 | 1009 | +0.38 | +1.16 | +1.31 | +661.00 | 499 | +1.32 | +1.19 |
| 22 | psar_dist_pct | 672 | +1.50 | low | 28 | +1.18 | +571.00 | 586 | +0.95 | +1.20 | -0.58 | -357.00 | 275 | -1.26 | +0.90 |
| 23 | upper_shadow_pct | 672 | +1.50 | high | 28 | +1.16 | +634.00 | 1084 | +0.59 | +1.15 | +0.27 | +174.00 | 473 | +0.36 | +1.04 |
| 24 | atr_28_pct | 672 | +2.50 | low | 4 | +1.15 | +227.00 | 280 | +0.81 | +1.30 | +2.22 | +953.00 | 173 | +5.51 | +1.60 |
| 25 | kc_pos | 2016 | +2.50 | low | 28 | +1.07 | +340.00 | 241 | +1.41 | +1.29 | -0.14 | -62.00 | 102 | -0.61 | +0.96 |

Full grid: `report/factor_grid_results.csv` (888 configs). Columns `is_*`/`oos_*` are in/out-of-sample; `pnl` in USD on 1 oz; `avg_usd` = average NET PnL per trade after the $0.16 cost hurdle.

## Engine confirmation (top configs, full sample)

| config | engine_pnl | engine_trades | engine_pf | engine_costs | fast_pnl | delta | is_sharpe | oos_sharpe | oos_pnl |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| hv_96 | W2016 T2.5 long@low H4 | +1432.00 | 493 | +1.57 | +79.00 | +1432.00 | +0.00 | +2.29 | +2.23 | +1011.00 |
| atr_28_pct | W2016 T2.5 long@low H4 | +1162.00 | 473 | +1.49 | +76.00 | +1162.00 | +0.00 | +2.22 | +1.67 | +747.00 |
| macd_hist_pct | W672 T2.5 long@low H28 | +1008.00 | 282 | +1.45 | +45.00 | +1008.00 | +0.00 | +1.93 | +0.95 | +434.00 |
| psar_dist_pct | W2016 T1.5 long@low H28 | +962.00 | 814 | +1.16 | +130.00 | +962.00 | +0.00 | +1.66 | +0.26 | +169.00 |
| atr_7_pct | W672 T2.5 long@low H4 | +211.00 | 493 | +1.08 | +79.00 | +211.00 | +0.00 | +1.61 | -0.40 | -153.00 |
| bb_width | W672 T1.5 long@low H28 | +258.00 | 429 | +1.08 | +69.00 | +258.00 | +0.00 | +1.48 | -0.49 | -241.00 |

## Decile profiles (fwd 7h return in bp, IS quantile bins applied to both segments)


**hl_range_pct** (monthly-IC t = -2.26, IS spr = -0.01806, OOS spr = -0.0105)

| bin | IS | OOS |
|---:|---:|---:|
| +1.00 | +14.32 | +22.93 |
| +2.00 | +15.43 | +31.29 |
| +3.00 | +14.70 | +28.11 |
| +4.00 | +9.80 | +23.99 |
| +5.00 | +14.38 | +26.75 |
| +6.00 | +13.19 | +28.86 |
| +7.00 | +10.84 | +32.76 |
| +8.00 | +10.80 | +27.97 |
| +9.00 | +8.65 | +20.14 |
| +10.00 | +5.93 | +5.67 |


**tr_pct** (monthly-IC t = -2.24, IS spr = -0.01802, OOS spr = -0.01048)

| bin | IS | OOS |
|---:|---:|---:|
| +1.00 | +13.95 | +22.86 |
| +2.00 | +15.64 | +31.20 |
| +3.00 | +14.82 | +27.93 |
| +4.00 | +9.62 | +24.32 |
| +5.00 | +14.51 | +26.59 |
| +6.00 | +13.34 | +28.36 |
| +7.00 | +10.86 | +33.40 |
| +8.00 | +10.85 | +27.94 |
| +9.00 | +8.52 | +19.90 |
| +10.00 | +5.94 | +5.77 |


**atr_28_pct** (monthly-IC t = -2.15, IS spr = -0.04099, OOS spr = -0.01342)

| bin | IS | OOS |
|---:|---:|---:|
| +1.00 | +19.08 | +58.03 |
| +2.00 | +20.58 | +21.77 |
| +3.00 | +24.12 | +6.61 |
| +4.00 | +10.31 | +16.87 |
| +5.00 | +7.51 | +17.80 |
| +6.00 | +6.07 | +30.60 |
| +7.00 | +9.76 | +37.49 |
| +8.00 | +11.31 | +40.58 |
| +9.00 | +9.43 | +35.97 |
| +10.00 | +0.03 | +5.52 |


**upper_shadow_pct** (monthly-IC t = 2.06, IS spr = 0.01267, OOS spr = 0.00229)

| bin | IS | OOS |
|---:|---:|---:|
| +1.00 | +9.40 | +24.18 |
| +2.00 | +10.41 | +17.58 |
| +3.00 | +9.55 | +20.11 |
| +4.00 | +11.67 | +23.11 |
| +5.00 | +9.48 | +23.87 |
| +6.00 | +14.67 | +21.80 |
| +7.00 | +12.98 | +14.75 |
| +8.00 | +12.86 | +22.52 |
| +9.00 | +14.25 | +21.34 |
| +10.00 | +12.72 | +27.73 |


**hv_20** (monthly-IC t = -1.9, IS spr = -0.03296, OOS spr = 0.00137)

| bin | IS | OOS |
|---:|---:|---:|
| +1.00 | +23.45 | +39.22 |
| +2.00 | +14.06 | +31.28 |
| +3.00 | +13.15 | +19.29 |
| +4.00 | +12.80 | +24.62 |
| +5.00 | +13.50 | +24.54 |
| +6.00 | +14.06 | +24.12 |
| +7.00 | +6.52 | +42.48 |
| +8.00 | +9.55 | +42.54 |
| +9.00 | +10.47 | +7.80 |
| +10.00 | +0.57 | +8.73 |

## Caveats

- **Multiple testing**: 888 IS configurations were ranked; the best IS Sharpe is inflated by selection. The OOS columns are the honest check (same sign & similar magnitude = robust).
- IC uses overlapping forward returns (monthly blocks mitigate but do not eliminate cross-correlation); treat |t| < 3 as noise given ~27 IS months.
- Rolling z-scores need a warm-up (min_periods = W/2); early IS bars are inactive for some configs.
- 22 holiday flat candles produce structural NaNs in 4 factors; NaN never generates entries (comparisons with NaN are False).
- No volume data exists on Gate.io TradFi klines; volume factors out of scope.
- Margin/leverage not modeled (fixed 1 oz).
