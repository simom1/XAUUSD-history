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
| f1 | 2024-03-07 -> 2024-09-06 | single|aroon_up_25|long|W4032|T1.5|H84 | 3.10 | 48 | 0.55 | 1804.00 | 14 | 128.86 | 1.37 |
| f2 | 2024-09-08 -> 2025-03-07 | single|aroon_up_25|long|W4032|T1.5|H84 | 1.89 | 62 | 0.00 | 0.00 | 0 | - | - |
| f3 | 2025-03-09 -> 2025-09-07 | single|gap_pct|long|W4032|T2|H36 | 2.10 | 40 | 1.43 | 4706.00 | 9 | 522.89 | 4.21 |
| f4 | 2025-09-07 -> 2026-03-09 | single|aroon_up_25|short|W6048|T1.5|H24 | 2.31 | 168 | 0.36 | 9988.00 | 146 | 68.41 | 1.07 |

| folds | folds_positive | wf_pnl | wf_trades | wf_avg | wf_sharpe |
|---:|---:|---:|---:|---:|---:|
| 4.00 | 3.00 | 16498.00 | 169.00 | 97.62 | 0.29 |


**pool = combos**

| fold | test_window | spec | train_sharpe | train_trades | test_sharpe | test_pnl | test_trades | test_avg | test_pf |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| f1 | 2024-03-07 -> 2024-09-06 | combo|aroon_up_25+close_vs_ema200|long|W4032|T1.5|H36 | 2.69 | 27 | -0.60 | -1448.00 | 7 | -206.86 | 0.50 |
| f2 | 2024-09-08 -> 2025-03-07 | combo|aroon_up_25+close_vs_ema200|long|W4032|T1.5|H120 | 1.78 | 21 | 0.00 | 0.00 | 0 | - | - |
| f3 | 2025-03-09 -> 2025-09-07 | combo|aroon_up_25+close_vs_ema200|long|W4032|T1.5|H120 | 1.45 | 21 | 0.00 | 0.00 | 0 | - | - |
| f4 | 2025-09-07 -> 2026-03-09 | combo|aroon_up_25+plus_di_14|long|W4032|T1.25|H120 | 2.12 | 708 | 2.17 | 81217.00 | 172 | 472.19 | 1.44 |

| folds | folds_positive | wf_pnl | wf_trades | wf_avg | wf_sharpe |
|---:|---:|---:|---:|---:|---:|
| 4.00 | 1.00 | 79769.00 | 179.00 | 445.64 | 1.06 |


**pool = all**

| fold | test_window | spec | train_sharpe | train_trades | test_sharpe | test_pnl | test_trades | test_avg | test_pf |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| f1 | 2024-03-07 -> 2024-09-06 | single|aroon_up_25|long|W4032|T1.5|H84 | 3.10 | 48 | 0.55 | 1804.00 | 14 | 128.86 | 1.37 |
| f2 | 2024-09-08 -> 2025-03-07 | single|aroon_up_25|long|W4032|T1.5|H84 | 1.89 | 62 | 0.00 | 0.00 | 0 | - | - |
| f3 | 2025-03-09 -> 2025-09-07 | single|gap_pct|long|W4032|T2|H36 | 2.10 | 40 | 1.43 | 4706.00 | 9 | 522.89 | 4.21 |
| f4 | 2025-09-07 -> 2026-03-09 | single|aroon_up_25|short|W6048|T1.5|H24 | 2.31 | 168 | 0.36 | 9988.00 | 146 | 68.41 | 1.07 |

| folds | folds_positive | wf_pnl | wf_trades | wf_avg | wf_sharpe |
|---:|---:|---:|---:|---:|---:|
| 4.00 | 3.00 | 16498.00 | 169.00 | 97.62 | 0.29 |

## Candidate ranking - singles (min 120 research trades, res_avg > 0)

| spec | res_sharpe | res_pnl | res_trades | res_avg | res_pf | f1_test_sharpe | f2_test_sharpe | f3_test_sharpe | f4_test_sharpe | f1_test_trades | f2_test_trades | f3_test_trades | f4_test_trades | pos_folds | wf_mean_sharpe |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| single|plus_di_14|long|W4032|T2|H120 | 2.24 | 192163.00 | 622 | 308.94 | 1.61 | 0.87 | 1.15 | 3.87 | 3.28 | 128 | 125 | 122 | 122 | 4 | 2.29 |
| single|plus_di_14|long|W4032|T1.25|H120 | 2.17 | 241017.00 | 951 | 253.44 | 1.44 | 0.39 | 2.18 | 3.10 | 3.34 | 196 | 192 | 192 | 194 | 4 | 2.25 |
| single|plus_di_14|long|W6048|T2|H120 | 2.08 | 181860.00 | 620 | 293.32 | 1.55 | 0.97 | 1.09 | 3.80 | 2.77 | 129 | 126 | 122 | 121 | 4 | 2.16 |
| single|plus_di_14|long|W8640|T1.25|H120 | 2.08 | 232857.00 | 948 | 245.63 | 1.42 | 0.56 | 1.81 | 3.12 | 2.99 | 196 | 195 | 192 | 195 | 4 | 2.12 |
| single|plus_di_14|long|W8640|T2|H120 | 2.14 | 185576.00 | 622 | 298.35 | 1.56 | 0.35 | 1.04 | 3.84 | 3.23 | 127 | 129 | 122 | 124 | 4 | 2.12 |
| single|plus_di_14|long|W6048|T1.25|H120 | 1.89 | 212805.00 | 958 | 222.13 | 1.37 | 0.32 | 1.79 | 3.08 | 2.69 | 196 | 195 | 194 | 198 | 4 | 1.97 |
| single|plus_di_14|long|W6048|T2|H84 | 1.95 | 156439.00 | 687 | 227.71 | 1.48 | 0.66 | 0.12 | 3.99 | 2.96 | 141 | 145 | 130 | 134 | 4 | 1.93 |
| single|plus_di_14|long|W4032|T2|H84 | 1.96 | 157861.00 | 692 | 228.12 | 1.49 | 0.59 | 0.17 | 3.81 | 3.03 | 141 | 144 | 133 | 135 | 4 | 1.90 |
| single|aroon_up_25|short|W6048|T1.5|H24 | 0.81 | 53537.00 | 314 | 170.50 | 1.30 | 1.29 | 1.50 | 4.38 | 0.36 | 8 | 105 | 55 | 146 | 4 | 1.88 |
| single|aroon_up_25|short|W6048|T1.5|H120 | 1.04 | 90561.00 | 139 | 651.52 | 1.72 | 0.77 | 1.61 | 4.13 | 1.02 | 4 | 50 | 22 | 63 | 4 | 1.88 |
| single|aroon_up_25|short|W6048|T1.5|H36 | 1.03 | 71641.00 | 258 | 277.68 | 1.49 | 1.35 | 1.17 | 3.70 | 1.06 | 7 | 85 | 45 | 121 | 4 | 1.82 |
| single|aroon_up_25|short|W6048|T1.5|H84 | 1.42 | 123079.00 | 170 | 723.99 | 1.96 | 0.50 | 1.67 | 2.84 | 2.27 | 4 | 59 | 28 | 79 | 4 | 1.82 |

## Candidate ranking - AND combos (min 50 research trades, res_avg > 0)

| spec | res_sharpe | res_pnl | res_trades | res_avg | res_pf | f1_test_sharpe | f2_test_sharpe | f3_test_sharpe | f4_test_sharpe | f1_test_trades | f2_test_trades | f3_test_trades | f4_test_trades | pos_folds | wf_mean_sharpe |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| combo|aroon_up_25+plus_di_14|long|W8640|T1.25|H120 | 1.55 | 176551.00 | 916 | 192.74 | 1.30 | 0.16 | 2.09 | 3.94 | 1.40 | 192 | 186 | 180 | 191 | 4 | 1.90 |
| combo|aroon_up_25+plus_di_14|long|W4032|T1.25|H84 | 1.27 | 126484.00 | 1039 | 121.74 | 1.23 | 0.10 | 0.78 | 3.56 | 1.31 | 224 | 203 | 208 | 201 | 4 | 1.44 |
| combo|aroon_up_25+plus_di_14|long|W8640|T1.25|H84 | 1.23 | 127566.00 | 1078 | 118.34 | 1.22 | 0.04 | 0.36 | 3.42 | 1.31 | 227 | 223 | 210 | 221 | 4 | 1.28 |
| combo|aroon_up_25+plus_di_14|long|W4032|T1.25|H120 | 1.92 | 199571.00 | 880 | 226.79 | 1.39 | -0.01 | 2.10 | 4.26 | 2.17 | 191 | 171 | 174 | 172 | 3 | 2.13 |
| combo|close_vs_ema200+plus_di_14|long|W4032|T1.25|H120 | 2.10 | 151882.00 | 391 | 388.45 | 1.76 | -1.25 | 1.89 | 3.89 | 3.49 | 78 | 79 | 87 | 75 | 3 | 2.00 |
| combo|aroon_up_25+plus_di_14|long|W6048|T1.25|H120 | 1.76 | 187567.00 | 913 | 205.44 | 1.34 | -0.04 | 2.11 | 4.00 | 1.94 | 191 | 188 | 180 | 184 | 3 | 2.00 |
| combo|aroon_up_25+close_vs_ema200|long|W4032|T1.25|H120 | 1.78 | 123381.00 | 391 | 315.55 | 1.57 | -1.10 | 1.62 | 4.39 | 2.50 | 80 | 79 | 85 | 70 | 3 | 1.85 |
| combo|close_vs_ema200+plus_di_14|long|W6048|T1.25|H120 | 1.58 | 120391.00 | 385 | 312.70 | 1.54 | -1.44 | 2.54 | 3.12 | 2.34 | 76 | 73 | 85 | 82 | 3 | 1.64 |
| combo|aroon_up_25+close_vs_ema200|long|W8640|T1.25|H120 | 1.70 | 127371.00 | 392 | 324.93 | 1.54 | -1.78 | 1.93 | 3.47 | 2.74 | 77 | 82 | 81 | 90 | 3 | 1.59 |
| combo|close_vs_ema200+plus_di_14|long|W8640|T1.25|H120 | 1.66 | 126274.00 | 368 | 343.14 | 1.57 | -1.73 | 2.15 | 3.21 | 2.64 | 74 | 70 | 78 | 85 | 3 | 1.57 |
| combo|aroon_up_25+close_vs_ema200|long|W6048|T1.25|H120 | 1.46 | 105486.00 | 404 | 261.10 | 1.44 | -1.25 | 1.90 | 3.58 | 1.90 | 77 | 85 | 87 | 82 | 3 | 1.53 |
| combo|close_vs_ema200+plus_di_14|long|W4032|T1.25|H84 | 1.62 | 113641.00 | 437 | 260.05 | 1.50 | -1.21 | 1.30 | 2.70 | 3.04 | 85 | 86 | 93 | 91 | 3 | 1.46 |

## Engine confirmation (top candidates, research slice)

| spec | engine_pnl | engine_trades | fast_pnl | delta | res_sharpe | pos_folds |
|---:|---:|---:|---:|---:|---:|---:|
| single|plus_di_14|long|W4032|T2|H120 | 192163.00 | 622 | 192163.00 | 0.00 | 2.24 | 4 |
| single|plus_di_14|long|W4032|T1.25|H120 | 241017.00 | 951 | 241017.00 | 0.00 | 2.17 | 4 |
| combo|aroon_up_25+plus_di_14|long|W8640|T1.25|H120 | 176551.00 | 916 | 176551.00 | 0.00 | 1.55 | 4 |
| combo|aroon_up_25+plus_di_14|long|W4032|T1.25|H84 | 126484.00 | 1039 | 126484.00 | 0.00 | 1.27 | 4 |

## Locked candidates for holdout judgment

- `single|plus_di_14|long|W4032|T2|H120`  (pos_folds 4, wf_mean_sharpe 2.29, res Sharpe 2.24)
- `combo|aroon_up_25+plus_di_14|long|W8640|T1.25|H120`  (pos_folds 4, wf_mean_sharpe 1.90, res Sharpe 1.55)

Judgment (run once, when research is frozen):

```
python scripts/run_combo_matrix.py --final "single|plus_di_14|long|W4032|T2|H120"
```
## Caveats

- 540 configs were ranked (multiple testing); the walk-forward folds are the honest selection surface, the sealed holdout is the only truly untouched data.
- Fold test metrics attribute a trade to its ENTRY bar; a position open across a fold boundary is counted in the entry fold (engine-identical accounting, boundary effects <= 1 trade).
- Combos share the same W and T for both legs (same-scale extremes); per-leg asymmetry is a possible later refinement.
- NaN z-scores (warm-up, holiday flat candles) never trigger entries.
- Margin/leverage not modeled (fixed 100 oz).
