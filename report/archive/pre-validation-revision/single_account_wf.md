# Single-Account Complete-System Walk-Forward (research period only)

- folds within research 2023-09-13 -> 2026-03-09; consumed dev set 2026-03-10 -> 2026-09-09 untouched here.
- factor universe (established robust subset): aroon_down_25, aroon_up_25, close_vs_ema200, gap_pct, minus_di_14, plus_di_14, rsi_14
- grid: W[4032, 6048, 8640] x T[1.25, 1.5, 1.75, 2.0] x H[24, 36, 84, 120]; fast no-exit screen -> top3 legs/side -> 3x3 unified systems
- filters: regime ['all', 'trend_up', 'trend_down', 'not_choppy'] x session ['all', 'asia', 'london', 'ny'] (top-2 per system); exits ['none', 'stop2', 'stop2.5', 'stop3', 'trail3', 'target3', 'stop2+target3'] scored by the event engine on train only
- per fold the test segment executes only the train-chosen complete system.
- sizing 1 oz; cost $0.16/oz round trip; PnL USD. Selection never sees test data.

## Per-fold execution

| fold | test_window | spec | train_sharpe | train_trades | test_sharpe | test_pnl | test_trades | test_avg | test_maxdd |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| f1 | 2024-03-07 -> 2024-09-06 | L:aroon_up_25|W4032|T1.5|H120 + S:gap_pct|W4032|T1.25|H84|regime=trend_down|session=ny|exit=none | 5.22 | 38 | 0.51 | 26.81 | 35 | 0.77 | -74.40 |
| f2 | 2024-09-08 -> 2025-03-07 | L:aroon_up_25|W4032|T1.5|H120 + S:gap_pct|W4032|T2|H120|regime=all|session=ny|exit=stop3 | 2.96 | 99 | -1.40 | -52.47 | 49 | -1.07 | -69.99 |
| f3 | 2025-03-09 -> 2025-09-07 | L:aroon_up_25|W4032|T1.5|H120 + S:gap_pct|W6048|T2|H120|regime=trend_up|session=asia|exit=none | 2.72 | 30 | -0.65 | -14.74 | 2 | -7.37 | -28.17 |
| f4 | 2025-09-07 -> 2026-03-09 | L:plus_di_14|W6048|T1.5|H120 + S:aroon_up_25|W6048|T1.5|H120|regime=all|session=asia|exit=none | 3.32 | 410 | 2.05 | 748.15 | 128 | 5.84 | -508.25 |

## Walk-forward aggregate (fold-chosen systems)

| folds | folds_positive | wf_pnl | wf_trades | wf_avg | wf_sharpe |
|---:|---:|---:|---:|---:|---:|
| 4.00 | 2.00 | 707.75 | 214.00 | 3.31 | 0.95 |

- candidate gates (>=3/4 folds positive, >=100 trades, positive avg): FAIL

## Spec selection frequency across folds

| spec | times_chosen |
|---:|---:|
| L:aroon_up_25|W4032|T1.5|H120 + S:gap_pct|W4032|T1.25|H84|regime=trend_down|session=ny|exit=none | 1 |
| L:aroon_up_25|W4032|T1.5|H120 + S:gap_pct|W4032|T2|H120|regime=all|session=ny|exit=stop3 | 1 |
| L:aroon_up_25|W4032|T1.5|H120 + S:gap_pct|W6048|T2|H120|regime=trend_up|session=asia|exit=none | 1 |
| L:plus_di_14|W6048|T1.5|H120 + S:aroon_up_25|W6048|T1.5|H120|regime=all|session=asia|exit=none | 1 |

- **No static candidate: no complete system was independently chosen by >= 3 folds.**
- No dev-set diagnostic is run; the next judgment requires >= 6 new continuous months of data.

- runtime: 90s
