# XAUUSD 5m - Short-Side Study

- data: `xauusd_5m_indicators.csv.gz` (211,242 bars)
- research: 2023-09-13 -> 2026-03-09 (175,475 bars)
- DEV holdout (insight, not judgment): 2026-03-10 -> 2026-09-09 (35,767 bars, down regime)
- factors: ['aroon_up_25', 'aroon_down_25', 'minus_di_14', 'close_vs_ema200', 'rsi_14']
- grid: W [4032, 6048, 8640], T [1.25, 1.5, 1.75, 2.0], H [24, 36, 84, 120], all side=short

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
| 4.00 | 2.00 | 16370.00 | 534.00 | 30.66 | 0.24 |

| fold | test_window | spec | train_sharpe | train_trades | test_sharpe | test_pnl | test_trades | test_avg | test_pf |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| f1 | 2024-03-07 -> 2024-09-06 | single|aroon_down_25|short|W6048|T1.5|H120 | 1.55 | 139 | -1.05 | -16646.00 | 229 | -72.69 | 0.88 |
| f2 | 2024-09-08 -> 2025-03-07 | single|close_vs_ema200|short|W4032|T1.5|H36 | 1.32 | 221 | -0.49 | -4050.00 | 131 | -30.92 | 0.93 |
| f3 | 2025-03-09 -> 2025-09-07 | single|aroon_up_25|short|W6048|T1.5|H84 | 1.01 | 63 | 2.84 | 27078.00 | 28 | 967.07 | 4.21 |
| f4 | 2025-09-07 -> 2026-03-09 | single|aroon_up_25|short|W6048|T1.5|H24 | 2.31 | 168 | 0.36 | 9988.00 | 146 | 68.41 | 1.07 |


## Candidate ranking (min 120 trades, res_avg > 0)

| spec | res_sharpe | res_pnl | res_trades | res_avg | res_pf | f1_test_sharpe | f1_test_pnl | f2_test_sharpe | f2_test_pnl | f3_test_sharpe | f3_test_pnl | f4_test_sharpe | f4_test_pnl | pos_folds | wf_mean_sharpe |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| single|aroon_up_25|short|W6048|T1.5|H24 | 0.81 | 53537.00 | 314 | 170.50 | 1.30 | 1.29 | 1190.00 | 1.50 | 7592.00 | 4.38 | 34767.00 | 0.36 | 9988.00 | 4 | 1.88 |
| single|aroon_up_25|short|W6048|T1.5|H120 | 1.04 | 90561.00 | 139 | 651.52 | 1.72 | 0.77 | 1132.00 | 1.61 | 10895.00 | 4.13 | 40463.00 | 1.02 | 38071.00 | 4 | 1.88 |
| single|aroon_up_25|short|W6048|T1.5|H36 | 1.03 | 71641.00 | 258 | 277.68 | 1.49 | 1.35 | 1541.00 | 1.17 | 6502.00 | 3.70 | 32431.00 | 1.06 | 31167.00 | 4 | 1.82 |
| single|aroon_up_25|short|W6048|T1.5|H84 | 1.42 | 123079.00 | 170 | 723.99 | 1.96 | 0.50 | 638.00 | 1.67 | 11245.00 | 2.84 | 27078.00 | 2.27 | 84118.00 | 4 | 1.82 |
| single|close_vs_ema200|short|W8640|T1.25|H36 | 0.33 | 36284.00 | 726 | 49.98 | 1.08 | 1.47 | 13450.00 | 0.34 | 3127.00 | 0.33 | 4793.00 | 0.33 | 15130.00 | 4 | 0.62 |
| single|close_vs_ema200|short|W4032|T1.5|H120 | 0.43 | 47677.00 | 349 | 136.61 | 1.17 | 1.16 | 10797.00 | 0.44 | 4211.00 | 0.28 | 4201.00 | 0.51 | 22773.00 | 4 | 0.60 |
| single|close_vs_ema200|short|W8640|T1.25|H84 | 0.38 | 43391.00 | 458 | 94.74 | 1.12 | 0.63 | 6270.00 | 0.65 | 6457.00 | 0.30 | 4551.00 | 0.71 | 33261.00 | 4 | 0.57 |
| single|close_vs_ema200|short|W6048|T1.25|H120 | 0.53 | 61994.00 | 418 | 148.31 | 1.19 | 0.52 | 5413.00 | 0.32 | 3296.00 | 0.42 | 6844.00 | 1.01 | 47775.00 | 4 | 0.57 |
| single|close_vs_ema200|short|W8640|T1.25|H120 | 0.48 | 56904.00 | 402 | 141.55 | 1.17 | 0.24 | 2504.00 | 0.53 | 5441.00 | 0.55 | 8821.00 | 0.95 | 45332.00 | 4 | 0.57 |
| single|close_vs_ema200|short|W8640|T1.25|H24 | 0.25 | 27484.00 | 924 | 29.74 | 1.06 | 1.13 | 9943.00 | 0.29 | 2529.00 | 0.46 | 6382.00 | 0.30 | 13370.00 | 4 | 0.54 |
| single|close_vs_ema200|short|W8640|T1.5|H120 | 0.47 | 51592.00 | 323 | 159.73 | 1.18 | 0.50 | 4623.00 | 0.09 | 874.00 | 0.60 | 8828.00 | 0.88 | 39655.00 | 4 | 0.52 |
| single|close_vs_ema200|short|W6048|T1.25|H84 | 0.36 | 41467.00 | 482 | 86.03 | 1.11 | 1.13 | 11269.00 | 0.22 | 2177.00 | 0.01 | 149.00 | 0.63 | 28938.00 | 4 | 0.50 |
| single|aroon_up_25|short|W8640|T1.5|H36 | 0.69 | 29140.00 | 155 | 188.00 | 1.30 | 0.00 | 0.00 | 0.18 | 742.00 | 2.56 | 19716.00 | 0.51 | 8682.00 | 3 | 0.81 |
| single|close_vs_ema200|short|W8640|T2|H120 | 0.54 | 54805.00 | 186 | 294.65 | 1.33 | 1.43 | 10591.00 | 1.11 | 8668.00 | -0.30 | -3780.00 | 0.99 | 41549.00 | 3 | 0.81 |
| single|close_vs_ema200|short|W6048|T1.25|H36 | 0.53 | 57464.00 | 767 | 74.92 | 1.14 | 1.57 | 14452.00 | -0.16 | -1512.00 | 0.49 | 7018.00 | 0.81 | 35623.00 | 3 | 0.68 |

## Engine confirmation (research slice)

| spec | engine_pnl | delta | pos_folds |
|---:|---:|---:|---:|
| single|aroon_up_25|short|W6048|T1.5|H24 | 53537.00 | 0.00 | 4 |
| single|aroon_up_25|short|W6048|T1.5|H120 | 90561.00 | 0.00 | 4 |
| single|aroon_up_25|short|W6048|T1.5|H36 | 71641.00 | 0.00 | 4 |

## Short-side factor logic

| factor | long-when | short trigger | logic |
|---|:---|---|---|
| minus_di_14 | low | z > +T | down-pressure dominant |
| aroon_down_25 | low | z > +T | fresh lows |
| aroon_up_25 | high | z < -T | no fresh highs -> decline |
| close_vs_ema200 | high | z < -T | below long MA |
| rsi_14 | low | z > +T | overbought reversal |
