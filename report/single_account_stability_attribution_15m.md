# Single-account stability attribution (15m bars)

- research only: 2023-09-13 04:45:00 -> 2026-03-09 23:45:00
- excluded and unread: consumed development set from 2026-03-10 onward.
- shapes: long-only, short-only, and long-short; all use a 1 oz maximum, next-open execution, and $0.16/oz round-trip cost.
- component ladder W672/W2016, holds H4/H28 (the 15m analogs of the 5m W2016/W6048, H12/H84); Sharpe annualized with 96 bars/day.
- each fold selects on its training prefix only; all full-system exit comparisons use the event engine.

## Fold-selected systems

| fold   | shape      | window                 | long                                            | short                                                | exit    |   test_pnl |   test_sharpe |   test_maxdd |   test_trades |   test_avg |   completed_trade_pnl |   conflicts |
|:-------|:-----------|:-----------------------|:------------------------------------------------|:-----------------------------------------------------|:--------|-----------:|--------------:|-------------:|--------------:|-----------:|----------------------:|------------:|
| f1     | long_only  | 2024-03-07->2024-09-06 | long:bb_squeeze:W672:T1.5:H4:trend_adx:new_york | nan                                                  | stop1_5 |    -198.12 |        -5.277 |      -202.99 |            41 |      -4.83 |               -198.12 |           0 |
| f1     | short_only | 2024-03-07->2024-09-06 | nan                                             | short:close_vs_ema200:W2016:T1.5:H28:trend_adx:all   | none    |      59.41 |         0.892 |      -104.62 |            43 |       1.38 |                 59.41 |           0 |
| f1     | long_short | 2024-03-07->2024-09-06 | long:bb_squeeze:W672:T1.5:H4:trend_adx:new_york | short:close_vs_ema200:W2016:T1.5:H28:trend_adx:all   | none    |     -70.86 |        -0.914 |      -131.31 |            84 |      -0.84 |                -70.86 |           0 |
| f2     | long_only  | 2024-09-08->2025-03-07 | long:natr_14:W672:T1.5:H28:trend_not_choppy:all | nan                                                  | none    |      24.75 |         0.862 |       -32.11 |            13 |       1.9  |                 24.75 |           0 |
| f2     | short_only | 2024-09-08->2025-03-07 | nan                                             | short:rsi_14:W672:T2:H4:none:overlap                 | none    |      -6.24 |        -0.273 |       -46.36 |            26 |      -0.24 |                 -6.24 |           0 |
| f2     | long_short | 2024-09-08->2025-03-07 | long:atr_28_pct:W2016:T1.5:H28:trend:london     | short:rsi_14:W672:T2:H4:none:overlap                 | none    |     -50.7  |        -1.631 |       -84.28 |            35 |      -1.45 |                -50.7  |           0 |
| f3     | long_only  | 2025-03-09->2025-09-07 | long:natr_14:W672:T1.5:H28:none:all             | nan                                                  | none    |      54.16 |         0.725 |      -140.88 |            44 |       1.23 |                 54.16 |           0 |
| f3     | short_only | 2025-03-09->2025-09-07 | nan                                             | short:close_vs_ema200:W672:T2:H28:trend_adx:new_york | none    |     -22.41 |        -0.354 |       -82.55 |            18 |      -1.25 |                -22.41 |           0 |
| f3     | long_short | 2025-03-09->2025-09-07 | long:natr_14:W672:T1.5:H28:none:all             | short:close_vs_ema200:W672:T2:H28:trend_adx:overlap  | none    |      24.62 |         0.256 |      -179.33 |            58 |       0.42 |                 24.62 |           0 |
| f4     | long_only  | 2025-09-07->2026-03-09 | long:natr_14:W672:T1.5:H28:trend_not_choppy:all | nan                                                  | none    |     121.51 |         1.497 |       -55.69 |            24 |       5.06 |                121.51 |           0 |
| f4     | short_only | 2025-09-07->2026-03-09 | nan                                             | short:aroon_down_25:W672:T2:H28:none:all             | none    |     285.86 |         1.062 |      -252.98 |            18 |      15.88 |                285.86 |           0 |
| f4     | long_short | 2025-09-07->2026-03-09 | long:natr_14:W672:T1.5:H28:trend_not_choppy:all | short:aroon_down_25:W672:T2:H28:none:all             | none    |     407.37 |         1.449 |      -252.98 |            42 |       9.7  |                407.37 |           2 |

## Complete-specification consensus

| shape      |   selections |   positive_folds |   trades |   completed_pnl |   mean_sharpe |   mean_pnl |   avg_trade |
|:-----------|-------------:|-----------------:|---------:|----------------:|--------------:|-----------:|------------:|
| long_only  |            1 |                1 |       44 |           54.16 |        0.725  |      54.16 |    1.23091  |
| long_only  |            2 |                2 |       37 |          146.26 |        1.1795 |      73.13 |    3.95297  |
| long_only  |            1 |                0 |       41 |         -198.12 |       -5.277  |    -198.12 |   -4.8322   |
| long_short |            1 |                0 |       84 |          -70.86 |       -0.914  |     -70.86 |   -0.843571 |
| long_short |            1 |                0 |       35 |          -50.7  |       -1.631  |     -50.7  |   -1.44857  |
| long_short |            1 |                1 |       58 |           24.62 |        0.256  |      24.62 |    0.424483 |
| long_short |            1 |                1 |       42 |          407.37 |        1.449  |     407.37 |    9.69929  |
| short_only |            1 |                1 |       43 |           59.41 |        0.892  |      59.41 |    1.38163  |
| short_only |            1 |                0 |       18 |          -22.41 |       -0.354  |     -22.41 |   -1.245    |
| short_only |            1 |                1 |       18 |          285.86 |        1.062  |     285.86 |   15.8811   |
| short_only |            1 |                0 |       26 |           -6.24 |       -0.273  |      -6.24 |   -0.24     |

## Component-level repetition (evidence only)

| component                                            |   training_selections |
|:-----------------------------------------------------|----------------------:|
| long:natr_14:W672:T1.5:H28:trend_not_choppy:all      |                     2 |
| long:bb_squeeze:W672:T1.5:H4:trend_adx:new_york      |                     1 |
| long:atr_28_pct:W2016:T1.5:H28:trend:london          |                     1 |
| long:natr_14:W672:T1.5:H28:none:all                  |                     1 |
| short:close_vs_ema200:W2016:T1.5:H28:trend_adx:all   |                     1 |
| short:rsi_14:W672:T2:H4:none:overlap                 |                     1 |
| short:close_vs_ema200:W672:T2:H28:trend_adx:new_york |                     1 |
| short:close_vs_ema200:W672:T2:H28:trend_adx:overlap  |                     1 |
| short:aroon_down_25:W672:T2:H28:none:all             |                     1 |

## Parameter drift

| shape      | exit    |   selections |   positive_folds |   mean_pnl |
|:-----------|:--------|-------------:|-----------------:|-----------:|
| long_only  | none    |            3 |                3 |    66.8067 |
| long_only  | stop1_5 |            1 |                0 |  -198.12   |
| long_short | none    |            4 |                2 |    77.6075 |
| short_only | none    |            4 |                2 |    79.155  |

## Test-trade contribution

| shape      | contribution   |   trades |     pnl |   costs |
|:-----------|:---------------|---------:|--------:|--------:|
| long_only  | session        |        4 |    3.34 |    0.64 |
| long_only  | signal         |       96 |  215.4  |   15.36 |
| long_only  | stop_loss      |       22 | -216.44 |    3.52 |
| long_short | session        |       16 |   88.86 |    2.56 |
| long_short | signal         |      203 |  221.57 |   32.48 |
| short_only | session        |       12 |   85.52 |    1.92 |
| short_only | signal         |       93 |  231.1  |   14.88 |

## Outcome

No static candidate: no complete specification met the 3/4 independent-selection, 3/4 positive-fold, and 40-trade gates.
Component repetition is descriptive evidence only and does not authorize a development diagnostic or capacity table.

## Stable component hypotheses (not candidates)

(none)
