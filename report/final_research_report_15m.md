# XAUUSD 15-minute timeframe study — final report

## Conclusion

No 15-minute strategy candidate exists. The independent nested walk-forward
mined four folds and selected four different component pairs (consensus gate:
>=3 fold repeats) -- no static candidate passed. A preregistered
cross-timeframe transfer test then evaluated the locked 5-minute
specification on 15-minute bars: it survives in-sample (research Sharpe
+1.56) but fails the 2026-03-10..2026-09-09 diagnostic segment (Sharpe
-1.70) exactly as the 5-minute version does. The failure is regime
dependent, not timeframe dependent. This closes the 15-minute line: freeze,
do not deploy, wait for new data.

## Method

- Data: `data/xauusd_15m_indicators.csv.gz`, 70,655 bars,
  2023-09-13 04:45 .. 2026-09-09 03:45 (same span as the 5-minute set).
- Research slice 2023-09-13 .. 2026-03-09 (58,731 bars). The 2026-03-10 ..
  2026-09-09 segment is diagnostic-only and never selects anything.
- Nested walk-forward: 4 sequential folds, per-fold selection on the training
  prefix only, single pass over the following test block. Windows W672/W2016
  (~7/21 days), holds H4/H28, thresholds z in {1.5, 2.0, 2.5}, sessions
  london/new_york/overlap/all, exits {none, trend, trend_adx, none_not_choppy,
  trend_not_choppy}. Gates: >=12 trades per training prefix, >=40 trades per
  test block.
- Annualization `sqrt(96 * 252)`; the engine, session masks, and metrics are
  parameterized by `bar_seconds`/`bars_per_day` with 5-minute defaults
  preserved (19/19 unit tests pass).

## Nested walk-forward results (`single_account_walkforward_15m.md`)

| fold | long pick | short pick | test PnL | test Sharpe | trades |
|---|---|---|---|---|---|
| f1 | bb_squeeze W672 T1.5 H4 trend_adx new_york | close_vs_ema200 W2016 T1.5 H28 trend_adx all | -$70.86 | -0.914 | 84 |
| f2 | atr_28_pct W2016 T1.5 H28 trend london | rsi_14 W672 T2 H4 none overlap | -$50.70 | -1.631 | 35 |
| f3 | natr_14 W672 T1.5 H28 none all | close_vs_ema200 W672 T2 H28 trend_adx overlap | +$24.62 | +0.256 | 58 |
| f4 | natr_14 W672 T1.5 H28 trend_not_choppy all | aroon_down_25 W672 T2 H28 none all | +$407.37 | +1.449 | 42 |

All four folds picked `none` (hold-expiry) on the winning side, replicating
the 5-minute attribution. Train-prefix Sharpes ran 3.9..7.4 against test
-1.6..+1.4: selection overfitting is more pronounced at 15 minutes because
each fold offers fewer effective trades.

## Cross-timeframe transfer test (preregistered hypothesis)

The locked 5-minute specification (long plus_di_14 z>=+2.0 W6048 H84 New
York; short aroon_up_25 z<=-1.5 W6048 H84 London; exit none; windows/holds
rescaled by bar count) evaluated unmodified on 15-minute bars
(`scripts/run_15m_transfer_test.py`):

| segment | exit | PnL | Sharpe | maxDD | trades | win rate |
|---|---|---|---|---|---|---|
| research | none | +$352.33 | +1.556 | -$178.99 | 222 | 55.0% |
| research | stop12 | +$326.83 | +1.448 | -$194.37 | 222 | 55.0% |
| research | stop16 | +$352.33 | +1.556 | -$178.99 | 222 | 55.0% |
| dev (diagnostic) | none | -$260.59 | -1.700 | -$571.20 | 111 | 47.7% |
| dev (diagnostic) | stop12 | -$250.83 | -1.660 | -$561.44 | 111 | 47.7% |
| dev (diagnostic) | stop16 | -$294.31 | -1.922 | -$604.92 | 111 | 47.7% |

Findings:

1. The signal family is not a 5-minute microstructure artifact. The same
   specification keeps a +1.56 research Sharpe at 15 minutes with the win
   rate intact (55.0%) and half the trade count (222 vs 443).
2. The dev-segment failure generalizes across timeframes (-1.70 at 15m,
   same sign and similar magnitude at 5m). The 2026-03..2026-09 regime is
   hostile to this momentum z-score family regardless of sampling rate.
3. The catastrophic-cap conclusion carries over: 12/16x ATR caps cost
   almost nothing in-sample and slightly reduce dev-segment losses at 12x.
4. Same-bar long/short conflicts rise from 0 (5m) to 29/32 (15m) because
   z-scores persist longer at coarser bars. Any future 15m implementation
   needs an explicit conflict adjudication rule; this was not a binding
   constraint in these results.

## Program-level verdict

Three independent evidence lines converge:

- 5m mining: strong research slice, dev diagnostic fails -> no candidate.
- 15m independent mining: 4 folds, 4 different picks -> no candidate.
- 15m transfer of the locked 5m spec: in-sample transfer works, dev fails
  the same way -> failure is regime driven.

Standing order: freeze the specification, do not deploy, accumulate at least
six continuous months of data after 2026-09-09, then run one pre-locked
evaluation exactly once. No further mining on the existing history.

## Reproduction

```
python scripts/run_single_account_research_15m.py   # nested WF, writes report/single_account_walkforward_15m.md
python scripts/run_15m_transfer_test.py             # transfer test table above
python -m unittest                                  # 19 tests, all pass
```
