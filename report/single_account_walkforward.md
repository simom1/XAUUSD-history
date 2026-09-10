# Single-account nested walk-forward (0.01 lot = 1 oz)

- research: 2023-09-13 04:55:00 -> 2026-03-09 23:55:00
- development excluded from selection: 2026-03-10 -> 2026-09-09 03:45:00
- each fold selects long/short components and exit rules from its training prefix only.
- exits are always evaluated by the event engine; component preselection is fast-path only.

## Fold selections

| fold | window | long | short | exit | train_sharpe | test_pnl | test_sharpe | test_maxdd | test_trades | conflicts |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| f1 | 2024-03-07->2024-09-06 | long:plus_di_14:W6048:T1.5:H12:trend_not_choppy:new_york | short:rsi_14:W2016:T2:H84:trend_adx:all | none | 4.58 | -105.99 | -1.774 | -108.47 | 136 | 0 |
| f2 | 2024-09-08->2025-03-07 | long:aroon_up_25:W6048:T1.5:H84:none:new_york | short:rsi_14:W6048:T2:H84:trend:all | stop2_5 | 2.445 | -24.25 | -3.518 | -30.09 | 5 | 0 |
| f3 | 2025-03-09->2025-09-07 | long:natr_14:W2016:T1.5:H84:none:all | short:close_vs_ema200:W2016:T2:H12:trend_not_choppy:new_york | none | 2.69 | 16.63 | 0.163 | -203.01 | 107 | 0 |
| f4 | 2025-09-07->2026-03-09 | long:di_ratio:W6048:T1.5:H84:none:london | short:close_vs_ema200:W2016:T1.5:H12:trend_not_choppy:new_york | none | 2.643 | 571.52 | 1.649 | -263.56 | 159 | 0 |

## Consensus

| picks | positives | mean_sharpe | trades |
|---:|---:|---:|---:|
| 1.0 | 1.0 | 1.649 | 159.0 |
| 1.0 | 0.0 | -1.774 | 136.0 |
| 1.0 | 1.0 | 0.163 | 107.0 |
| 1.0 | 0.0 | -3.518 | 5.0 |

## Outcome

No static development candidate was independently selected in at least three folds with at least three positive test folds and 100 total test trades.

## Capacity sensitivity

No table is produced: capacity sensitivity is intentionally calculated only for a locked candidate. Selecting a size or reporting scaled performance here would turn a failed selection into an implied candidate. The fixed research unit remains 0.01 lot = 1 oz; 0.05 and 0.10 lot remain reserved for a future locked specification.

