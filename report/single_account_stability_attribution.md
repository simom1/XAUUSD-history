# Single-account stability attribution

- research only: 2023-09-13 04:55:00 -> 2026-03-09 23:55:00
- excluded and unread: consumed development set from 2026-03-10 onward.
- shapes: long-only, short-only, and long-short; all use a 1 oz maximum, next-open execution, and $0.16/oz round-trip cost.
- each fold selects on its training prefix only; all full-system exit comparisons use the event engine.

## Fold-selected systems

| fold   | shape      | window                 | long                                                     | short                                                          | exit    |   test_pnl |   test_sharpe |   test_maxdd |   test_trades |   test_avg |   completed_trade_pnl |   conflicts |
|:-------|:-----------|:-----------------------|:---------------------------------------------------------|:---------------------------------------------------------------|:--------|-----------:|--------------:|-------------:|--------------:|-----------:|----------------------:|------------:|
| f1     | long_only  | 2024-03-07->2024-09-06 | long:plus_di_14:W6048:T1.5:H12:trend_not_choppy:new_york | nan                                                            | none    |     -86.35 |        -1.509 |       -88.83 |           129 |      -0.67 |                -86.35 |           0 |
| f1     | long_short | 2024-03-07->2024-09-06 | long:plus_di_14:W6048:T1.5:H12:trend_not_choppy:new_york | short:rsi_14:W2016:T2:H84:trend_adx:all                        | none    |    -105.99 |        -1.774 |      -108.47 |           136 |      -0.78 |               -105.99 |           0 |
| f2     | long_only  | 2024-09-08->2025-03-07 | long:aroon_up_25:W6048:T1.5:H84:none:new_york            | nan                                                            | stop2_5 |       0    |         0     |         0    |             0 |       0    |                  0    |           0 |
| f2     | long_short | 2024-09-08->2025-03-07 | long:aroon_up_25:W6048:T1.5:H84:none:new_york            | short:rsi_14:W6048:T2:H84:trend:all                            | stop2_5 |     -24.25 |        -3.518 |       -30.09 |             5 |      -4.85 |                -24.25 |           0 |
| f3     | long_only  | 2025-03-09->2025-09-07 | long:natr_14:W2016:T1.5:H84:none:all                     | nan                                                            | none    |      39.17 |         0.53  |      -129.97 |            61 |       0.64 |                 39.17 |           0 |
| f3     | short_only | 2025-03-09->2025-09-07 | nan                                                      | short:close_vs_ema200:W2016:T2:H12:trend_not_choppy:new_york   | none    |     -22.54 |        -0.319 |      -126.69 |            46 |      -0.49 |                -22.54 |           0 |
| f3     | long_short | 2025-03-09->2025-09-07 | long:natr_14:W2016:T1.5:H84:none:all                     | short:close_vs_ema200:W2016:T2:H12:trend_not_choppy:new_york   | none    |      16.63 |         0.163 |      -203.01 |           107 |       0.16 |                 16.63 |           0 |
| f4     | long_only  | 2025-09-07->2026-03-09 | long:di_ratio:W6048:T1.5:H84:none:london                 | nan                                                            | none    |     285.72 |         1.329 |      -162.79 |            88 |       3.25 |                285.72 |           0 |
| f4     | short_only | 2025-09-07->2026-03-09 | nan                                                      | short:close_vs_ema200:W2016:T1.5:H12:trend_not_choppy:new_york | none    |     295.08 |         1.066 |      -264.98 |            71 |       4.16 |                295.08 |           0 |
| f4     | long_short | 2025-09-07->2026-03-09 | long:di_ratio:W6048:T1.5:H84:none:london                 | short:close_vs_ema200:W2016:T1.5:H12:trend_not_choppy:new_york | none    |     571.52 |         1.649 |      -263.56 |           159 |       3.59 |                571.52 |           0 |

## Complete-specification consensus

| shape      |   selections |   positive_folds |   trades |   completed_pnl |   mean_sharpe |   mean_pnl |   avg_trade |
|:-----------|-------------:|-----------------:|---------:|----------------:|--------------:|-----------:|------------:|
| long_only  |            1 |                1 |       88 |          285.72 |         1.329 |     285.72 |    3.24682  |
| long_only  |            1 |                0 |      129 |          -86.35 |        -1.509 |     -86.35 |   -0.66938  |
| long_only  |            1 |                1 |       61 |           39.17 |         0.53  |      39.17 |    0.642131 |
| long_only  |            1 |                0 |        0 |            0    |         0     |       0    |  nan        |
| long_short |            1 |                1 |      159 |          571.52 |         1.649 |     571.52 |    3.59447  |
| long_short |            1 |                0 |      136 |         -105.99 |        -1.774 |    -105.99 |   -0.779338 |
| long_short |            1 |                1 |      107 |           16.63 |         0.163 |      16.63 |    0.155421 |
| long_short |            1 |                0 |        5 |          -24.25 |        -3.518 |     -24.25 |   -4.85     |
| short_only |            1 |                1 |       71 |          295.08 |         1.066 |     295.08 |    4.15606  |
| short_only |            1 |                0 |       46 |          -22.54 |        -0.319 |     -22.54 |   -0.49     |

## Component-level repetition (evidence only)

| component                                                      |   training_selections |
|:---------------------------------------------------------------|----------------------:|
| long:plus_di_14:W6048:T1.5:H12:trend_not_choppy:new_york       |                     1 |
| long:aroon_up_25:W6048:T1.5:H84:none:new_york                  |                     1 |
| long:natr_14:W2016:T1.5:H84:none:all                           |                     1 |
| long:di_ratio:W6048:T1.5:H84:none:london                       |                     1 |
| short:rsi_14:W2016:T2:H84:trend_adx:all                        |                     1 |
| short:rsi_14:W6048:T2:H84:trend:all                            |                     1 |
| short:close_vs_ema200:W2016:T2:H12:trend_not_choppy:new_york   |                     1 |
| short:close_vs_ema200:W2016:T1.5:H12:trend_not_choppy:new_york |                     1 |

## Parameter drift

| shape      | exit    |   selections |   positive_folds |   mean_pnl |
|:-----------|:--------|-------------:|-----------------:|-----------:|
| long_only  | none    |            3 |                2 |    79.5133 |
| long_only  | stop2_5 |            1 |                0 |     0      |
| long_short | none    |            3 |                2 |   160.72   |
| long_short | stop2_5 |            1 |                0 |   -24.25   |
| short_only | none    |            2 |                1 |   136.27   |

## Test-trade contribution

| shape      | contribution    |   trades |     pnl |   costs |
|:-----------|:----------------|---------:|--------:|--------:|
| long_only  | session         |        2 |   33.9  |    0.32 |
| long_only  | signal          |      276 |  204.64 |   44.16 |
| long_short | session         |        2 |   33.9  |    0.32 |
| long_short | signal          |      388 |  753.07 |   62.08 |
| long_short | signal_reversal |       12 | -304.81 |    1.92 |
| long_short | stop_loss       |        5 |  -24.25 |    0.8  |
| short_only | signal          |      117 |  272.54 |   18.72 |

## Outcome

No static candidate: no complete specification met the 3/4 independent-selection, 3/4 positive-fold, and 100-trade gates.
Component repetition is descriptive evidence only and does not authorize a development diagnostic or capacity table.

## Stable component hypotheses (not candidates)

(none)
