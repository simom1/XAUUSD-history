# XAUUSD 5m - Short-Side Study

- data: `xauusd_5m_indicators.csv.gz` (211,242 bars)
- research: 2023-09-13 -> 2026-03-09 (175,475 bars)
- DEV holdout (insight, not judgment): 2026-03-10 -> 2026-09-09 (35,767 bars, down regime)
- factors: ['aroon_up_25', 'aroon_down_25', 'minus_di_14', 'close_vs_ema200', 'rsi_14']
- grid: W [4032, 6048, 8640], T [1.25, 1.5, 1.75, 2.0], H [24, 36, 84, 120], all side=short
- short gate: trend_down,adx_strong

## Walk-forward folds

| name | test_start | test_end |
|---:|---:|---:|
| f1 | 2024-03-07 | 2024-09-06 |
| f2 | 2024-09-08 | 2025-03-07 |
| f3 | 2025-03-09 | 2025-09-07 |
| f4 | 2025-09-07 | 2026-03-09 |

## Walk-forward simulation

| folds | folds_positive | wf_pnl | wf_trades | wf_avg | wf_sharpe |
|---:|---:|---:|---:|---:|---:|
| 4.00 | 1.00 | -16361.00 | 318.00 | -51.45 | -0.31 |

| fold | test_window | spec | train_sharpe | train_trades | test_sharpe | test_pnl | test_trades | test_avg | test_pf |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| f1 | 2024-03-07 -> 2024-09-06 | single|aroon_down_25|short|W6048|T1.5|H36 | 1.86 | 133 | -0.65 | -6676.00 | 210 | -31.79 | 0.92 |
| f2 | 2024-09-08 -> 2025-03-07 | single|rsi_14|short|W8640|T1.5|H36 | 1.10 | 43 | -2.79 | -5918.00 | 15 | -394.53 | 0.19 |
| f3 | 2025-03-09 -> 2025-09-07 | single|close_vs_ema200|short|W8640|T2|H120 | 0.62 | 100 | -0.53 | -6448.00 | 37 | -174.27 | 0.82 |
| f4 | 2025-09-07 -> 2026-03-09 | single|aroon_up_25|short|W6048|T1.5|H24 | 1.67 | 58 | 0.13 | 2681.00 | 56 | 47.87 | 1.04 |


## Candidate ranking (min 120 trades, res_avg > 0)

| spec | res_sharpe | res_pnl | res_trades | res_avg | res_pf | f1_test_sharpe | f1_test_pnl | f2_test_sharpe | f2_test_pnl | f3_test_sharpe | f3_test_pnl | f4_test_sharpe | f4_test_pnl | pos_folds | wf_mean_sharpe |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| single|close_vs_ema200|short|W4032|T1.5|H120 | 0.34 | 35544.00 | 321 | 110.73 | 1.14 | 0.47 | 4193.00 | 0.26 | 2380.00 | 0.59 | 8479.00 | 0.34 | 14834.00 | 4 | 0.41 |
| single|close_vs_ema200|short|W6048|T1.5|H120 | 0.20 | 20482.00 | 308 | 66.50 | 1.08 | 0.11 | 939.00 | 0.42 | 3923.00 | 0.08 | 1084.00 | 0.24 | 9964.00 | 4 | 0.21 |
| single|aroon_up_25|short|W4032|T1.5|H36 | 0.22 | 14068.00 | 135 | 104.21 | 1.14 | 1.90 | 3229.00 | -0.71 | -2725.00 | 0.74 | 3565.00 | 0.34 | 9506.00 | 3 | 0.57 |
| single|close_vs_ema200|short|W8640|T1.5|H120 | 0.53 | 55825.00 | 289 | 193.17 | 1.24 | 0.37 | 3280.00 | -0.54 | -5032.00 | 1.44 | 20060.00 | 0.88 | 37529.00 | 3 | 0.54 |
| single|close_vs_ema200|short|W8640|T2|H120 | 0.34 | 32923.00 | 179 | 183.93 | 1.20 | 1.20 | 8587.00 | 0.76 | 5715.00 | -0.53 | -6448.00 | 0.69 | 27660.00 | 3 | 0.53 |
| single|close_vs_ema200|short|W6048|T1.25|H120 | 0.51 | 54889.00 | 372 | 147.55 | 1.20 | 0.88 | 8682.00 | -0.71 | -7083.00 | 0.89 | 13885.00 | 0.94 | 40782.00 | 3 | 0.50 |
| single|close_vs_ema200|short|W8640|T1.25|H120 | 0.34 | 38851.00 | 363 | 107.03 | 1.13 | 0.24 | 2325.00 | -0.41 | -4071.00 | 1.11 | 16921.00 | 0.56 | 25769.00 | 3 | 0.38 |
| single|close_vs_ema200|short|W6048|T1.25|H84 | 0.27 | 29404.00 | 429 | 68.54 | 1.09 | 1.52 | 14662.00 | -0.81 | -7688.00 | 0.16 | 2340.00 | 0.46 | 20128.00 | 3 | 0.33 |
| single|close_vs_ema200|short|W8640|T1.75|H120 | 0.24 | 23839.00 | 232 | 102.75 | 1.12 | 0.71 | 5641.00 | -0.35 | -2995.00 | 0.27 | 3508.00 | 0.49 | 20181.00 | 3 | 0.28 |
| single|close_vs_ema200|short|W8640|T1.5|H84 | 0.29 | 30838.00 | 328 | 94.02 | 1.12 | 0.86 | 7500.00 | -1.02 | -9072.00 | 0.72 | 9620.00 | 0.47 | 20469.00 | 3 | 0.26 |
| single|close_vs_ema200|short|W4032|T1.75|H120 | 0.19 | 19013.00 | 260 | 73.13 | 1.08 | 0.87 | 7013.00 | -0.51 | -4374.00 | 0.55 | 7331.00 | 0.10 | 4136.00 | 3 | 0.25 |
| single|close_vs_ema200|short|W8640|T2|H84 | 0.26 | 24920.00 | 192 | 129.79 | 1.13 | 0.98 | 6860.00 | 0.30 | 2122.00 | -1.13 | -12736.00 | 0.74 | 30082.00 | 3 | 0.22 |
| single|close_vs_ema200|short|W6048|T1.5|H84 | 0.21 | 21951.00 | 345 | 63.63 | 1.08 | 0.72 | 6382.00 | 0.17 | 1459.00 | -0.43 | -5941.00 | 0.41 | 17515.00 | 3 | 0.22 |
| single|close_vs_ema200|short|W4032|T2|H120 | 0.05 | 5267.00 | 208 | 25.32 | 1.03 | 0.07 | 480.00 | -0.34 | -2622.00 | 0.04 | 470.00 | 0.10 | 4053.00 | 3 | -0.03 |
| single|rsi_14|short|W4032|T1.25|H84 | 0.12 | 3834.00 | 134 | 28.61 | 1.06 | -0.79 | -3442.00 | 0.15 | 769.00 | 0.01 | 47.00 | 0.40 | 3790.00 | 3 | -0.06 |

## Engine confirmation (research slice)

| spec | engine_pnl | delta | pos_folds |
|---:|---:|---:|---:|
| single|close_vs_ema200|short|W4032|T1.5|H120 | 35544.00 | 0.00 | 4 |
| single|close_vs_ema200|short|W6048|T1.5|H120 | 20482.00 | 0.00 | 4 |
| single|aroon_up_25|short|W4032|T1.5|H36 | 14068.00 | 0.00 | 3 |

## Dev holdout insight (2026-03->09, down regime)

| spec | dev_pnl | dev_trades | dev_avg | dev_sharpe | dev_pf |
|---:|---:|---:|---:|---:|---:|
| single|close_vs_ema200|short|W4032|T1.5|H120 | 58805.00 | 60 | 980.08 | 2.05 | 1.67 |
| single|close_vs_ema200|short|W6048|T1.5|H120 | 78200.00 | 59 | 1325.42 | 2.65 | 2.04 |

Note: the holdout is CONSUMED (used for the long-side judgment). These short results are development insight, not independent judgment.

## Short-side factor logic

| factor | long-when | short trigger | logic |
|---|:---|---|---|
| minus_di_14 | low | z > +T | down-pressure dominant |
| aroon_down_25 | low | z > +T | fresh lows |
| aroon_up_25 | high | z < -T | no fresh highs -> decline |
| close_vs_ema200 | high | z < -T | below long MA |
| rsi_14 | low | z > +T | overbought reversal |
