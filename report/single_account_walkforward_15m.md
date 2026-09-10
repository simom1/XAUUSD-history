# Single-account nested walk-forward on 15m bars (0.01 lot = 1 oz)

- research: 2023-09-13 04:45:00 -> 2026-03-09 23:45:00
- development excluded from selection: 2026-03-10 -> 2026-09-09 03:45:00
- bars: 58,731 research (15m), windows W672/W2016, holds H4/H28, Sharpe annualized with 96 bars/day
- each fold selects long/short components and exit rules from its training prefix only.
- exits are always evaluated by the event engine; component preselection is fast-path only.
- trade gates scaled for 15m frequency: 12 per training prefix, 40 total test trades.

## Fold selections

| fold | window | long | short | exit | train_sharpe | test_pnl | test_sharpe | test_maxdd | test_trades | conflicts |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| f1 | 2024-03-07->2024-09-06 | long:bb_squeeze:W672:T1.5:H4:trend_adx:new_york | short:close_vs_ema200:W2016:T1.5:H28:trend_adx:all | none | 4.264 | -70.86 | -0.914 | -131.31 | 84 | 0 |
| f2 | 2024-09-08->2025-03-07 | long:atr_28_pct:W2016:T1.5:H28:trend:london | short:rsi_14:W672:T2:H4:none:overlap | none | 2.793 | -50.7 | -1.631 | -84.28 | 35 | 0 |
| f3 | 2025-03-09->2025-09-07 | long:natr_14:W672:T1.5:H28:none:all | short:close_vs_ema200:W672:T2:H28:trend_adx:overlap | none | 2.253 | 24.62 | 0.256 | -179.33 | 58 | 0 |
| f4 | 2025-09-07->2026-03-09 | long:natr_14:W672:T1.5:H28:trend_not_choppy:all | short:aroon_down_25:W672:T2:H28:none:all | none | 2.428 | 407.37 | 1.449 | -252.98 | 42 | 2 |

## Consensus

| picks | positives | mean_sharpe | trades |
|---:|---:|---:|---:|
| 1.0 | 0.0 | -0.914 | 84.0 |
| 1.0 | 0.0 | -1.631 | 35.0 |
| 1.0 | 1.0 | 0.256 | 58.0 |
| 1.0 | 1.0 | 1.449 | 42.0 |

## Outcome

No static development candidate was independently selected in at least three folds with at least three positive test folds and the required total test trades.

## Capacity sensitivity

No table is produced: capacity sensitivity is intentionally calculated only for a locked candidate. Selecting a size or reporting scaled performance here would turn a failed selection into an implied candidate. The fixed research unit remains 0.01 lot = 1 oz; 0.05 and 0.10 lot remain reserved for a future locked specification.

