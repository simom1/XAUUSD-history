# XAUUSD 5m - Combination Matrix + Walk-Forward Report

- data: `xauusd_5m_indicators.csv.gz` (211,242 bars, 2023-09-13 -> 2026-09-09)
- **SEALED holdout: 2026-03-10 -> 2026-09-09 (35,767 bars) - not used anywhere in this report**
- research period: 2023-09-13 -> 2026-03-09 (175,475 bars); the previous 70/30 OOS block is inside it
- cost model: all-in $0.16/oz round trip; 1 unit = 100 oz; grid: W [4032, 6048, 8640], T [1.25, 1.5, 1.75, 2.0], H [24, 36, 84, 120]

## Walk-forward folds (expanding train, 6-month tests)

| name | test_start | test_end | test_hi | train_hi |
|---:|---:|---:|---:|---:|
| f1 | 2024-03-07 | 2024-09-06 | 69782 | 34,183 |
| f2 | 2024-09-08 | 2025-03-07 | 104801 | 69,782 |
| f3 | 2025-03-09 | 2025-09-07 | 140126 | 104,801 |
| f4 | 2025-09-07 | 2026-03-09 | 175474 | 140,126 |

## Method

1. **Survivor neighborhood**: the 4 surviving factors x {long, short} x W x T x H (384 configs). Long = survivor direction (aroon_up_25/close_vs_ema200/plus_di_14 long@high, gap_pct long@low).
2. **Combination matrix**: all 288 pairwise AND-confirmed longs - both factors must be in their trigger state on the same decision bar.
3. **Walk-forward simulation**: per fold, the best train-Sharpe config (train trades >= gate, train avg > 0) is applied to the untouched test fold; fold equities are concatenated per pool.
4. **Candidate ranking**: positive-fold count, then mean fold-test Sharpe, then research Sharpe. Final judgment happens on the sealed holdout via `--final SPEC` - run once, after research is frozen.

## Fast-model calibration (research slice)

EMA 9/21: engine $-34,942 vs fast $-34,942 - delta $0.0000.

## Walk-forward simulation


**pool = singles**

| fold | test_window | spec | train_sharpe | train_trades | test_sharpe | test_pnl | test_trades | test_avg | test_pf |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| f1 | 2024-03-07 -> 2024-09-06 | single|aroon_up_25|long|W4032|T1.5|H120 | 3.55 | 43 | 0.74 | 2633.00 | 12 | 219.42 | 1.56 |
| f2 | 2024-09-08 -> 2025-03-07 | single|aroon_up_25|long|W4032|T1.5|H120 | 2.20 | 55 | 1.35 | 1699.00 | 1 | 1699.00 | inf |
| f3 | 2025-03-09 -> 2025-09-07 | single|aroon_up_25|long|W4032|T1.5|H120 | 1.93 | 56 | -0.15 | -354.00 | 3 | -118.00 | 0.73 |
| f4 | 2025-09-07 -> 2026-03-09 | single|aroon_up_25|short|W6048|T1.5|H24 | 2.31 | 168 | 0.36 | 9988.00 | 146 | 68.41 | 1.07 |

| folds | folds_positive | wf_pnl | wf_trades | wf_avg | wf_sharpe |
|---:|---:|---:|---:|---:|---:|
| 4.00 | 3.00 | 13966.00 | 162.00 | 86.21 | 0.25 |


**pool = combos**

| fold | test_window | spec | train_sharpe | train_trades | test_sharpe | test_pnl | test_trades | test_avg | test_pf |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| f1 | 2024-03-07 -> 2024-09-06 | combo|aroon_up_25+plus_di_14|long|W4032|T1.5|H24 | 2.82 | 60 | -1.85 | -4645.00 | 16 | -290.31 | 0.32 |
| f2 | 2024-09-08 -> 2025-03-07 | combo|aroon_up_25+close_vs_ema200|long|W4032|T1.5|H120 | 1.78 | 21 | 0.00 | 0.00 | 0 | - | - |
| f3 | 2025-03-09 -> 2025-09-07 | combo|aroon_up_25+close_vs_ema200|long|W4032|T1.5|H120 | 1.45 | 21 | 0.00 | 0.00 | 0 | - | - |
| f4 | 2025-09-07 -> 2026-03-09 | combo|aroon_up_25+plus_di_14|long|W8640|T1.25|H120 | 2.43 | 779 | 1.29 | 55728.00 | 204 | 273.18 | 1.21 |

| folds | folds_positive | wf_pnl | wf_trades | wf_avg | wf_sharpe |
|---:|---:|---:|---:|---:|---:|
| 4.00 | 1.00 | 51083.00 | 220.00 | 232.20 | 0.59 |


**pool = all**

| fold | test_window | spec | train_sharpe | train_trades | test_sharpe | test_pnl | test_trades | test_avg | test_pf |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| f1 | 2024-03-07 -> 2024-09-06 | single|aroon_up_25|long|W4032|T1.5|H120 | 3.55 | 43 | 0.74 | 2633.00 | 12 | 219.42 | 1.56 |
| f2 | 2024-09-08 -> 2025-03-07 | single|aroon_up_25|long|W4032|T1.5|H120 | 2.20 | 55 | 1.35 | 1699.00 | 1 | 1699.00 | inf |
| f3 | 2025-03-09 -> 2025-09-07 | single|aroon_up_25|long|W4032|T1.5|H120 | 1.93 | 56 | -0.15 | -354.00 | 3 | -118.00 | 0.73 |
| f4 | 2025-09-07 -> 2026-03-09 | combo|aroon_up_25+plus_di_14|long|W8640|T1.25|H120 | 2.43 | 779 | 1.29 | 55728.00 | 204 | 273.18 | 1.21 |

| folds | folds_positive | wf_pnl | wf_trades | wf_avg | wf_sharpe |
|---:|---:|---:|---:|---:|---:|
| 4.00 | 3.00 | 59706.00 | 220.00 | 271.39 | 0.69 |

## Candidate ranking - singles (min 120 research trades, res_avg > 0)

| spec | res_sharpe | res_pnl | res_trades | res_avg | res_pf | f1_test_sharpe | f2_test_sharpe | f3_test_sharpe | f4_test_sharpe | f1_test_trades | f2_test_trades | f3_test_trades | f4_test_trades | pos_folds | wf_mean_sharpe |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| single|plus_di_14|long|W6048|T1.5|H120 | 2.51 | 265974.00 | 906 | 293.57 | 1.54 | 0.18 | 3.05 | 3.77 | 3.69 | 191 | 179 | 183 | 181 | 4 | 2.67 |
| single|plus_di_14|long|W4032|T1.25|H120 | 2.20 | 252641.00 | 1031 | 245.04 | 1.42 | 0.49 | 2.52 | 3.68 | 3.12 | 210 | 208 | 207 | 206 | 4 | 2.45 |
| single|plus_di_14|long|W8640|T1.5|H120 | 2.19 | 240162.00 | 905 | 265.37 | 1.47 | 0.10 | 3.04 | 3.62 | 2.87 | 193 | 180 | 184 | 181 | 4 | 2.41 |
| single|plus_di_14|long|W4032|T2|H120 | 2.16 | 188336.00 | 648 | 290.64 | 1.56 | 0.71 | 1.64 | 4.09 | 2.87 | 133 | 130 | 127 | 125 | 4 | 2.33 |
| single|plus_di_14|long|W4032|T1.5|H120 | 2.05 | 223502.00 | 920 | 242.94 | 1.43 | 0.28 | 2.64 | 3.57 | 2.78 | 191 | 184 | 187 | 182 | 4 | 2.32 |
| single|plus_di_14|long|W6048|T2|H120 | 2.07 | 183325.00 | 645 | 284.22 | 1.53 | 0.74 | 1.55 | 4.07 | 2.57 | 135 | 131 | 127 | 122 | 4 | 2.23 |
| single|plus_di_14|long|W6048|T1.25|H120 | 2.03 | 233645.00 | 1034 | 225.96 | 1.38 | 0.36 | 2.10 | 3.82 | 2.58 | 210 | 211 | 210 | 210 | 4 | 2.21 |
| single|plus_di_14|long|W8640|T1.25|H120 | 1.97 | 237871.00 | 1020 | 233.21 | 1.39 | 0.46 | 2.12 | 3.93 | 2.30 | 209 | 212 | 207 | 209 | 4 | 2.20 |
| single|plus_di_14|long|W8640|T2|H120 | 2.11 | 184959.00 | 645 | 286.76 | 1.54 | 0.23 | 1.56 | 4.02 | 2.95 | 132 | 133 | 127 | 126 | 4 | 2.19 |
| single|plus_di_14|long|W6048|T2|H84 | 1.87 | 152367.00 | 717 | 212.51 | 1.44 | 0.34 | 0.71 | 3.76 | 2.87 | 149 | 150 | 136 | 136 | 4 | 1.92 |
| single|aroon_up_25|short|W6048|T1.5|H24 | 0.81 | 53537.00 | 314 | 170.50 | 1.30 | 1.29 | 1.50 | 4.38 | 0.36 | 8 | 105 | 55 | 146 | 4 | 1.88 |
| single|aroon_up_25|short|W6048|T1.5|H120 | 1.04 | 90561.00 | 139 | 651.52 | 1.72 | 0.77 | 1.61 | 4.13 | 1.02 | 4 | 50 | 22 | 63 | 4 | 1.88 |

## Candidate ranking - AND combos (min 50 research trades, res_avg > 0)

| spec | res_sharpe | res_pnl | res_trades | res_avg | res_pf | f1_test_sharpe | f2_test_sharpe | f3_test_sharpe | f4_test_sharpe | f1_test_trades | f2_test_trades | f3_test_trades | f4_test_trades | pos_folds | wf_mean_sharpe |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| combo|aroon_up_25+plus_di_14|long|W4032|T1.25|H120 | 2.02 | 216600.00 | 954 | 227.04 | 1.39 | 0.12 | 2.49 | 4.90 | 2.00 | 204 | 189 | 189 | 182 | 4 | 2.38 |
| combo|aroon_up_25+plus_di_14|long|W6048|T1.25|H120 | 1.91 | 210132.00 | 984 | 213.55 | 1.36 | 0.09 | 2.47 | 4.74 | 1.81 | 204 | 204 | 195 | 196 | 4 | 2.28 |
| combo|aroon_up_25+plus_di_14|long|W8640|T1.25|H120 | 1.70 | 198560.00 | 983 | 201.99 | 1.32 | 0.16 | 2.46 | 4.77 | 1.29 | 204 | 203 | 194 | 204 | 4 | 2.17 |
| combo|plus_di_14+gap_pct|long|W4032|T1.25|H84 | 0.96 | 24296.00 | 54 | 449.93 | 1.95 | 0.50 | 0.60 | 2.97 | 1.60 | 15 | 11 | 4 | 13 | 4 | 1.42 |
| combo|plus_di_14+gap_pct|long|W4032|T1.25|H36 | 1.08 | 20172.00 | 56 | 360.21 | 2.04 | 0.52 | 0.34 | 2.94 | 1.80 | 15 | 12 | 4 | 14 | 4 | 1.40 |
| combo|close_vs_ema200+plus_di_14|long|W4032|T1.25|H120 | 2.10 | 151882.00 | 391 | 388.45 | 1.76 | -1.25 | 1.89 | 3.89 | 3.49 | 78 | 79 | 87 | 75 | 3 | 2.00 |
| combo|aroon_up_25+close_vs_ema200|long|W4032|T1.25|H120 | 1.78 | 123381.00 | 391 | 315.55 | 1.57 | -1.10 | 1.62 | 4.39 | 2.50 | 80 | 79 | 85 | 70 | 3 | 1.85 |
| combo|close_vs_ema200+plus_di_14|long|W6048|T1.25|H120 | 1.58 | 120391.00 | 385 | 312.70 | 1.54 | -1.44 | 2.54 | 3.12 | 2.34 | 76 | 73 | 85 | 82 | 3 | 1.64 |
| combo|aroon_up_25+close_vs_ema200|long|W8640|T1.25|H120 | 1.70 | 127371.00 | 392 | 324.93 | 1.54 | -1.78 | 1.93 | 3.47 | 2.74 | 77 | 82 | 81 | 90 | 3 | 1.59 |
| combo|close_vs_ema200+plus_di_14|long|W8640|T1.25|H120 | 1.66 | 126274.00 | 368 | 343.14 | 1.57 | -1.73 | 2.15 | 3.21 | 2.64 | 74 | 70 | 78 | 85 | 3 | 1.57 |
| combo|aroon_up_25+close_vs_ema200|long|W6048|T1.25|H120 | 1.46 | 105486.00 | 404 | 261.10 | 1.44 | -1.25 | 1.90 | 3.58 | 1.90 | 77 | 85 | 87 | 82 | 3 | 1.53 |
| combo|close_vs_ema200+plus_di_14|long|W4032|T1.25|H84 | 1.62 | 113641.00 | 437 | 260.05 | 1.50 | -1.21 | 1.30 | 2.70 | 3.04 | 85 | 86 | 93 | 91 | 3 | 1.46 |

## Engine confirmation (top candidates, research slice)

| spec | engine_pnl | engine_trades | fast_pnl | delta | res_sharpe | pos_folds |
|---:|---:|---:|---:|---:|---:|---:|
| single|plus_di_14|long|W6048|T1.5|H120 | 265974.00 | 906 | 265974.00 | 0.00 | 2.51 | 4 |
| single|plus_di_14|long|W4032|T1.25|H120 | 252641.00 | 1031 | 252641.00 | 0.00 | 2.20 | 4 |
| combo|aroon_up_25+plus_di_14|long|W4032|T1.25|H120 | 216600.00 | 954 | 216600.00 | 0.00 | 2.02 | 4 |
| combo|aroon_up_25+plus_di_14|long|W6048|T1.25|H120 | 210132.00 | 984 | 210132.00 | 0.00 | 1.91 | 4 |

## Locked candidates for holdout judgment

- `single|plus_di_14|long|W6048|T1.5|H120`  (pos_folds 4, wf_mean_sharpe 2.67, res Sharpe 2.51)
- `combo|aroon_up_25+plus_di_14|long|W4032|T1.25|H120`  (pos_folds 4, wf_mean_sharpe 2.38, res Sharpe 2.02)

Judgment (run once, when research is frozen):

```
python scripts/run_combo_matrix.py --final "single|plus_di_14|long|W6048|T1.5|H120"
```
## Caveats

- 540 configs were ranked (multiple testing); the walk-forward folds are the honest selection surface, the sealed holdout is the only truly untouched data.
- Fold test metrics attribute a trade to its ENTRY bar; a position open across a fold boundary is counted in the entry fold (engine-identical accounting, boundary effects <= 1 trade).
- Combos share the same W and T for both legs (same-scale extremes); per-leg asymmetry is a possible later refinement.
- NaN z-scores (warm-up, holiday flat candles) never trigger entries.
- Margin/leverage not modeled (fixed 100 oz).
