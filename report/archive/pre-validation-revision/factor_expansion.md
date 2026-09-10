# Phase 4: New Composite Factor Screening

- data: `xauusd_5m_indicators.csv.gz` (211,242 bars)
- research: 2023-09-13 -> 2026-03-09 (175,475 bars)
- dev holdout (insight only): 2026-03-10 -> 2026-09-09 (35,767 bars)
- new factors: di_spread, aroon_osc, di_ratio, bb_squeeze, vol_percentile

## IC study (12-bar forward return, Spearman)

| factor | ic_mean | ic_std | ic_ir | direction |
|---:|---:|---:|---:|---:|
| di_spread | -0.02 | 0.03 | -0.71 | high |
| aroon_osc | -0.02 | 0.04 | -0.52 | high |
| di_ratio | -0.02 | 0.03 | -0.71 | high |
| bb_squeeze | 0.01 | 0.05 | 0.28 | low |
| vol_percentile | 0.01 | 0.06 | 0.12 | low |

## Walk-forward results


**long**

| fold | test_window | spec | train_sharpe | train_trades | test_sharpe | test_pnl | test_trades | test_avg | test_pf |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| f1 | 2024-03-07 -> 2024-09-06 | single|aroon_osc|long|W6048|T1.5|H84 | 3.86 | 175 | 1.99 | 21334.00 | 177 | 120.53 | 1.32 |
| f2 | 2024-09-08 -> 2025-03-07 | single|aroon_osc|long|W6048|T1.5|H84 | 2.71 | 352 | 0.02 | 160.00 | 95 | 1.68 | 1.00 |
| f3 | 2025-03-09 -> 2025-09-07 | single|aroon_osc|long|W8640|T1.5|H84 | 2.15 | 460 | 1.96 | 27488.00 | 155 | 177.34 | 1.34 |
| f4 | 2025-09-07 -> 2026-03-09 | single|di_spread|long|W8640|T1.5|H120 | 2.49 | 637 | 2.54 | 86030.00 | 152 | 565.99 | 1.53 |

| folds | folds_positive | wf_pnl | wf_trades | wf_avg | wf_sharpe |
|---:|---:|---:|---:|---:|---:|
| 4.00 | 4.00 | 135012.00 | 579.00 | 233.18 | 1.74 |


**short**

| fold | test_window | spec | train_sharpe | train_trades | test_sharpe | test_pnl | test_trades | test_avg | test_pf |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| f1 | 2024-03-07 -> 2024-09-06 | single|aroon_osc|short|W4032|T1.5|H24 | 0.59 | 263 | -0.97 | -9126.00 | 314 | -29.06 | 0.90 |
| f2 | 2024-09-08 -> 2025-03-07 | single|aroon_osc|short|W4032|T1.75|H84 | 1.68 | 61 | 0.53 | 4083.00 | 73 | 55.93 | 1.12 |
| f3 | 2025-03-09 -> 2025-09-07 | single|aroon_osc|short|W4032|T1.75|H84 | 1.15 | 134 | -0.28 | -2701.00 | 38 | -71.08 | 0.92 |
| f4 | 2025-09-07 -> 2026-03-09 | single|aroon_osc|short|W6048|T1.75|H84 | 0.93 | 161 | -0.10 | -3888.00 | 102 | -38.12 | 0.98 |

| folds | folds_positive | wf_pnl | wf_trades | wf_avg | wf_sharpe |
|---:|---:|---:|---:|---:|---:|
| 4.00 | 1.00 | -11632.00 | 527.00 | -22.07 | -0.14 |

## Top candidates (research)


**long**

| spec | res_sharpe | res_pnl | res_trades | res_avg | pos_folds |
|---:|---:|---:|---:|---:|---:|
| single|aroon_osc|long|W8640|T1.5|H36 | 2.42 | 115370.00 | 948 | 121.70 | 4 |
| single|aroon_osc|long|W8640|T1.5|H120 | 2.30 | 149096.00 | 618 | 241.26 | 4 |
| single|di_spread|long|W6048|T1.25|H120 | 2.25 | 248759.00 | 956 | 260.21 | 4 |
| single|di_spread|long|W8640|T1.25|H120 | 2.16 | 236125.00 | 948 | 249.08 | 4 |
| single|aroon_osc|long|W8640|T1.5|H84 | 2.09 | 124194.00 | 714 | 173.94 | 4 |
| single|di_spread|long|W4032|T1.25|H120 | 2.08 | 229205.00 | 960 | 238.76 | 4 |
| single|di_ratio|long|W8640|T2|H120 | 2.05 | 169598.00 | 624 | 271.79 | 4 |
| single|aroon_osc|long|W4032|T1.5|H36 | 2.03 | 103964.00 | 943 | 110.25 | 4 |
| single|di_ratio|long|W6048|T2|H120 | 2.01 | 169834.00 | 625 | 271.73 | 4 |
| single|aroon_osc|long|W4032|T1.25|H36 | 1.93 | 179281.00 | 1878 | 95.46 | 4 |


**short**

| spec | res_sharpe | res_pnl | res_trades | res_avg | pos_folds |
|---:|---:|---:|---:|---:|---:|
| single|aroon_osc|short|W8640|T1.75|H84 | 0.38 | 36048.00 | 245 | 147.13 | 3 |
| single|aroon_osc|short|W6048|T1.75|H84 | 0.24 | 22551.00 | 263 | 85.75 | 3 |
| single|di_spread|short|W4032|T1.75|H36 | -0.06 | -6068.00 | 961 | -6.31 | 3 |
| single|aroon_osc|short|W8640|T1.75|H24 | -0.06 | -3830.00 | 304 | -12.60 | 3 |
| single|aroon_osc|short|W6048|T1.75|H36 | -0.16 | -11789.00 | 319 | -36.96 | 3 |
| single|aroon_osc|short|W4032|T1.75|H120 | -0.22 | -21875.00 | 249 | -87.85 | 3 |
| single|aroon_osc|short|W6048|T1.75|H24 | -0.28 | -17264.00 | 334 | -51.69 | 3 |
| single|aroon_osc|short|W6048|T1.75|H120 | -0.33 | -31774.00 | 239 | -132.95 | 3 |
| single|di_spread|short|W4032|T1.5|H36 | 0.29 | 33408.00 | 1321 | 25.29 | 2 |
| single|di_spread|short|W8640|T1.5|H36 | 0.22 | 25924.00 | 1296 | 20.00 | 2 |

