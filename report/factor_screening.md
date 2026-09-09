# XAUUSD 5m - Factor Screening Report

-   data: `xauusd_5m_indicators.csv.gz` (211,242 bars, 2023-09-13 -> 2026-09-09)
-   IS/OOS split: first 70% IS (2023-09-13 -> 2025-10-16), last 30% OOS (2025-10-16 -> 2026-09-09)
-   cost model: all-in $0.16/oz round trip ($0.08/side); 1 unit = 100 oz
-   data quality: see `report/data_quality_5m.md` (verdict: clean; 22 holiday flat candles -> 88 structural NaN cells in 4 columns)

## Method

1.  **Factor universe**: 56 scale-free factors derived from the 64-indicator set (price-level indicators converted to % distance / channel position).
2.  **IC study**: monthly Spearman rank IC vs forward returns h in (12, 84, 288) bars (1h / ~7h / ~24h); selection uses IS months only, OOS Spearman reported as stability check.
3.  **Grid backtest**: entry when trailing z-score (windows \[2016, 6048\]) crosses +/-\[1.5, 2.5\], fixed hold \[12, 84\] bars, long-when-high (momentum) vs long-when-low (reversal) both evaluated; exact engine accounting (next-open fills, session flat 21:00 UTC / Fri 20:45, entry block 15 min, $0.16 RT cost). Direction & params selected on IS; OOS untouched.

## Fast-model calibration

EMA 9/21 baseline: engine vs vectorized accounting (net $ over full sample): engine $51,598 vs fast $51,598 - delta $0.0000 (float noise).

## IC results (h = 84 bars ~ 7h, top 15 by |t|)

| factor | ic\_mean | icir | t | pos\_pct | is\_spr | oos\_spr | months |
| --- | --- | --- | --- | --- | --- | --- | --- |
| clv | \-0.0074 | \-0.5010 | \-2.5500 | +0.2690 | \-0.0028 | \-0.0025 | 26 |
| upper\_shadow\_pct | +0.0067 | +0.4550 | +2.3200 | +0.6540 | +0.0066 | +0.0044 | 26 |
| kdj\_k | \-0.0180 | \-0.3250 | \-1.6600 | +0.4620 | \-0.0036 | \-0.0029 | 26 |
| kdj\_d | \-0.0199 | \-0.3210 | \-1.6400 | +0.4620 | \-0.0039 | \-0.0044 | 26 |
| kdj\_j | \-0.0119 | \-0.3190 | \-1.6300 | +0.4620 | \-0.0020 | \-0.0008 | 26 |
| lower\_shadow\_pct | \-0.0043 | \-0.2960 | \-1.5100 | +0.3850 | \-0.0028 | \-0.0047 | 26 |
| atr\_7\_pct | \-0.0237 | \-0.2940 | \-1.5000 | +0.5000 | +0.0043 | +0.0167 | 26 |
| hl\_range\_pct | \-0.0179 | \-0.2920 | \-1.4900 | +0.4230 | +0.0029 | +0.0129 | 26 |
| tr\_pct | \-0.0180 | \-0.2930 | \-1.4900 | +0.4230 | +0.0027 | +0.0132 | 26 |
| hv\_20 | \-0.0238 | \-0.2790 | \-1.4200 | +0.4620 | +0.0036 | +0.0200 | 26 |
| adx\_14 | \-0.0227 | \-0.2660 | \-1.3600 | +0.4620 | \-0.0152 | \-0.0105 | 26 |
| stoch\_d\_14 | \-0.0152 | \-0.2590 | \-1.3200 | +0.4620 | \-0.0003 | \-0.0023 | 26 |
| natr\_14 | \-0.0219 | \-0.2600 | \-1.3200 | +0.4230 | +0.0062 | +0.0144 | 26 |
| stoch\_k\_14 | \-0.0138 | \-0.2550 | \-1.3000 | +0.4620 | +0.0003 | \-0.0014 | 26 |
| williams\_r\_14 | \-0.0138 | \-0.2550 | \-1.3000 | +0.4620 | +0.0003 | \-0.0014 | 26 |

(full table: `report/factor_ic_results.csv`, horizons 12/84/288)

## Single-factor grid - top 25 by IS Sharpe (min 150 IS trades)

| rank | factor | win | thr | long\_when | hold | is\_sharpe | is\_pnl | is\_trades | is\_avg\_usd | is\_pf | oos\_sharpe | oos\_pnl | oos\_trades | oos\_avg\_usd | oos\_pf |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | upper\_shadow\_pct | 6048 | +1.50 | high | 84 | +1.63 | +125023.00 | 1572 | +78.29 | +1.18 | \-0.57 | \-60094.00 | 689 | \-84.39 | +0.94 |
| 2 | upper\_shadow\_pct | 2016 | +1.50 | high | 84 | +1.62 | +125310.00 | 1598 | +77.20 | +1.18 | \-0.82 | \-86271.00 | 689 | \-122.38 | +0.92 |
| 3 | hl\_range\_pct | 6048 | +1.50 | high | 84 | +1.52 | +111310.00 | 1003 | +110.56 | +1.21 | \-1.23 | \-123384.00 | 443 | \-277.58 | +0.85 |
| 4 | gap\_pct | 6048 | +1.50 | low | 84 | +1.51 | +54492.00 | 261 | +208.78 | +1.49 | +0.54 | +33114.00 | 77 | +430.05 | +1.20 |
| 5 | tr\_pct | 6048 | +1.50 | high | 84 | +1.49 | +108197.00 | 993 | +108.54 | +1.20 | \-1.26 | \-125702.00 | 439 | \-285.39 | +0.85 |
| 6 | lower\_shadow\_pct | 2016 | +1.50 | high | 84 | +1.47 | +113584.00 | 1597 | +70.02 | +1.16 | \-0.95 | \-98649.00 | 688 | \-140.82 | +0.91 |
| 7 | aroon\_up\_25 | 6048 | +1.50 | high | 12 | +1.46 | +29367.00 | 370 | +79.37 | +1.37 | +1.08 | +44522.00 | 463 | +96.16 | +1.16 |
| 8 | lower\_shadow\_pct | 6048 | +1.50 | high | 84 | +1.44 | +110983.00 | 1578 | +69.21 | +1.16 | \-1.17 | \-121897.00 | 688 | \-174.61 | +0.88 |
| 9 | stoch\_d\_14 | 6048 | +1.50 | low | 84 | +1.40 | +102355.00 | 1427 | +70.38 | +1.17 | \-0.55 | \-55320.00 | 623 | \-85.70 | +0.94 |
| 10 | close\_vs\_wma20 | 2016 | +2.50 | low | 84 | +1.39 | +81657.00 | 605 | +134.97 | +1.26 | \-1.62 | \-135093.00 | 265 | \-509.78 | +0.75 |
| 11 | plus\_di\_14 | 6048 | +2.50 | high | 84 | +1.30 | +53372.00 | 392 | +136.15 | +1.32 | +0.44 | +21564.00 | 165 | +130.69 | +1.11 |
| 12 | upper\_shadow\_pct | 2016 | +2.50 | high | 84 | +1.28 | +76641.00 | 977 | +78.45 | +1.19 | \-0.42 | \-34896.00 | 418 | \-83.48 | +0.94 |
| 13 | stoch\_d\_14 | 2016 | +1.50 | low | 84 | +1.25 | +91346.00 | 1435 | +62.43 | +1.14 | \-0.66 | \-65948.00 | 623 | \-103.03 | +0.93 |
| 14 | hl\_range\_pct | 2016 | +1.50 | high | 84 | +1.18 | +86856.00 | 1038 | +83.68 | +1.16 | \-1.22 | \-121240.00 | 474 | \-255.78 | +0.85 |
| 15 | tr\_pct | 2016 | +1.50 | high | 84 | +1.14 | +83904.00 | 1026 | +81.78 | +1.15 | \-1.22 | \-120254.00 | 469 | \-256.41 | +0.85 |
| 16 | close\_vs\_sma10 | 2016 | +2.50 | low | 84 | +1.09 | +65820.00 | 651 | +101.11 | +1.19 | \-1.61 | \-137197.00 | 292 | \-469.85 | +0.76 |
| 17 | close\_vs\_ema12 | 2016 | +2.50 | low | 84 | +1.06 | +63509.00 | 633 | +100.33 | +1.19 | \-1.59 | \-134941.00 | 288 | \-468.55 | +0.76 |
| 18 | close\_vs\_sma200 | 2016 | +2.50 | low | 12 | +1.05 | +27004.00 | 482 | +56.02 | +1.22 | \-0.15 | \-7865.00 | 259 | \-30.37 | +0.97 |
| 19 | aroon\_up\_25 | 6048 | +1.50 | high | 84 | +1.04 | +32603.00 | 158 | +206.35 | +1.50 | +2.63 | +162726.00 | 186 | +874.87 | +1.77 |
| 20 | macd\_hist\_pct | 2016 | +2.50 | low | 84 | +1.02 | +51906.00 | 440 | +117.97 | +1.22 | \-0.71 | \-53603.00 | 196 | \-273.48 | +0.87 |
| 21 | upper\_shadow\_pct | 6048 | +2.50 | high | 84 | +1.01 | +59608.00 | 962 | +61.96 | +1.14 | \-0.78 | \-64663.00 | 417 | \-155.07 | +0.89 |
| 22 | donchian\_pos | 6048 | +1.50 | low | 84 | +0.99 | +74047.00 | 1530 | +47.68 | +1.11 | \-0.07 | \-7065.00 | 667 | \-8.94 | +0.99 |
| 23 | close\_vs\_ema200 | 6048 | +1.50 | high | 84 | +0.99 | +57596.00 | 615 | +93.65 | +1.19 | +1.16 | +96337.00 | 261 | +369.11 | +1.24 |
| 24 | close\_vs\_ema200\_pct | 6048 | +1.50 | high | 84 | +0.99 | +57596.00 | 615 | +93.65 | +1.19 | +1.16 | +96337.00 | 261 | +369.11 | +1.24 |
| 25 | minus\_di\_14 | 6048 | +2.50 | high | 84 | +0.97 | +45158.00 | 415 | +108.81 | +1.22 | \-1.94 | \-131460.00 | 166 | \-791.93 | +0.64 |

Full grid: `report/factor_grid_results.csv` (800 configs). Columns `is_*`/`oos_*` are in/out-of-sample; `pnl` in USD on 100 oz; `avg_usd` = average NET PnL per trade after the $16 cost hurdle.

## Engine confirmation (top configs, full sample)

| config | engine\_pnl | engine\_trades | engine\_pf | engine\_costs | fast\_pnl | delta | is\_sharpe | oos\_sharpe | oos\_pnl |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| upper\_shadow\_pct | W6048 T1.5 long@high H84 | +64929.00 | 2261 | +1.04 | +36176.00 | +64929.00 | +0.00 | +1.63 | \-0.57 |
| hl\_range\_pct | W6048 T1.5 long@high H84 | \-12074.00 | 1446 | +0.99 | +23136.00 | \-12074.00 | +0.00 | +1.52 | \-1.23 |
| gap\_pct | W6048 T1.5 long@low H84 | +87606.00 | 338 | +1.31 | +5408.00 | +87606.00 | +0.00 | +1.51 | +0.54 |
| tr\_pct | W6048 T1.5 long@high H84 | \-17505.00 | 1432 | +0.99 | +22912.00 | \-17505.00 | +0.00 | +1.49 | \-1.26 |
| lower\_shadow\_pct | W2016 T1.5 long@high H84 | +14935.00 | 2285 | +1.01 | +36560.00 | +14935.00 | +0.00 | +1.47 | \-0.95 |
| aroon\_up\_25 | W6048 T1.5 long@high H12 | +73889.00 | 833 | +1.21 | +13328.00 | +73889.00 | +0.00 | +1.46 | +1.08 |

## Decile profiles (fwd 7h return in bp, IS quantile bins applied to both segments)

**clv** (monthly-IC t = -2.55, IS spr = -0.00277, OOS spr = -0.00248)

| bin | IS | OOS |
| --- | --- | --- |
| +1.00 | +4.38 | +1.89 |
| +2.00 | +4.46 | +1.54 |
| +3.00 | +4.90 | +0.53 |
| +4.00 | +5.11 | \-0.72 |
| +5.00 | +4.43 | +1.90 |
| +6.00 | +4.92 | \-0.20 |
| +7.00 | +5.22 | +2.08 |
| +8.00 | +4.62 | +0.45 |
| +9.00 | +4.12 | +1.56 |
| +10.00 | +4.26 | +0.14 |

**upper\_shadow\_pct** (monthly-IC t = 2.32, IS spr = 0.00657, OOS spr = 0.00436)

| bin | IS | OOS |
| --- | --- | --- |
| +1.00 | +4.23 | +3.36 |
| +2.00 | +3.88 | \-2.33 |
| +3.00 | +4.35 | +0.05 |
| +4.00 | +4.31 | +1.05 |
| +5.00 | +3.98 | +0.59 |
| +6.00 | +5.51 | +2.03 |
| +7.00 | +5.96 | +0.76 |
| +8.00 | +4.57 | +0.62 |
| +9.00 | +4.87 | +3.14 |
| +10.00 | +4.77 | +0.39 |

**kdj\_k** (monthly-IC t = -1.66, IS spr = -0.0036, OOS spr = -0.00286)

| bin | IS | OOS |
| --- | --- | --- |
| +1.00 | +5.03 | +0.24 |
| +2.00 | +4.59 | +2.26 |
| +3.00 | +4.45 | \-0.31 |
| +4.00 | +4.30 | +1.39 |
| +5.00 | +4.27 | \-0.31 |
| +6.00 | +4.28 | +2.04 |
| +7.00 | +5.16 | +0.89 |
| +8.00 | +5.16 | +2.25 |
| +9.00 | +4.42 | +1.32 |
| +10.00 | +4.79 | \-0.79 |

**kdj\_d** (monthly-IC t = -1.64, IS spr = -0.00394, OOS spr = -0.00443)

| bin | IS | OOS |
| --- | --- | --- |
| +1.00 | +5.10 | +1.23 |
| +2.00 | +4.33 | +1.93 |
| +3.00 | +4.22 | \-0.15 |
| +4.00 | +4.59 | +0.79 |
| +5.00 | +4.37 | \-0.31 |
| +6.00 | +4.29 | +1.32 |
| +7.00 | +5.03 | +1.21 |
| +8.00 | +5.62 | +1.95 |
| +9.00 | +4.97 | +2.58 |
| +10.00 | +3.93 | \-1.43 |

**kdj\_j** (monthly-IC t = -1.63, IS spr = -0.00197, OOS spr = -0.00081)

| bin | IS | OOS |
| --- | --- | --- |
| +1.00 | +5.33 | \-0.27 |
| +2.00 | +4.88 | +1.99 |
| +3.00 | +4.36 | +0.36 |
| +4.00 | +4.28 | \-0.38 |
| +5.00 | +3.92 | +1.67 |
| +6.00 | +4.81 | +2.27 |
| +7.00 | +4.20 | +2.47 |
| +8.00 | +4.26 | +0.46 |
| +9.00 | +5.59 | +0.82 |
| +10.00 | +4.83 | \-0.50 |

## Caveats

-   **Multiple testing**: 800 IS configurations were ranked; the best IS Sharpe is inflated by selection. The OOS columns are the honest check (same sign & similar magnitude = robust).
-   IC uses overlapping forward returns (monthly blocks mitigate but do not eliminate cross-correlation); treat |t| < 3 as noise given ~27 IS months.
-   Rolling z-scores need a warm-up (min\_periods = W/2); early IS bars are inactive for some configs.
-   22 holiday flat candles produce structural NaNs in 4 factors; NaN never generates entries (comparisons with NaN are False).
-   No volume data exists on [Gate.io](http://Gate.io) TradFi klines; volume factors out of scope.
-   Margin/leverage not modeled (fixed 100 oz ~ 2.6x notional on $100k).