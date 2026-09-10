# XAUUSD 15-minute timeframe study — final report

## Conclusion

No 15-minute strategy candidate exists. The independent nested walk-forward  
mined four folds and selected four different component pairs (consensus gate:  
>=3 fold repeats) -- no static candidate passed. A preregistered  
cross-timeframe transfer test then evaluated the locked 5-minute  
specification on 15-minute bars: it survives in-sample (research Sharpe  
+1.20) but fails the 2026-03-10..2026-09-09 diagnostic segment (Sharpe  
-0.89) exactly as the 5-minute version does. The failure is regime  
dependent, not timeframe dependent. This closes the 15-minute line: freeze,  
do not deploy, wait for new data.

## Method

-   Data: `data/xauusd_15m_indicators.csv.gz`, 70,655 bars,  
    2023-09-13 04:45 .. 2026-09-09 03:45 (same span as the 5-minute set).
-   Research slice 2023-09-13 .. 2026-03-09 (58,731 bars). The 2026-03-10 ..  
    2026-09-09 segment is diagnostic-only and never selects anything.
-   Nested walk-forward: 4 sequential folds, per-fold selection on the training  
    prefix only, single pass over the following test block. Windows W672/W2016  
    (~7/21 days), holds H4/H28, thresholds z in {1.5, 2.0, 2.5}, sessions  
    london/new\_york/overlap/all, exits {none, trend, trend\_adx, none\_not\_choppy,  
    trend\_not\_choppy}. Gates: >=12 trades per training prefix, >=40 trades per  
    test block.
-   Annualization `sqrt(96 * 252)`; the engine, session masks, and metrics are  
    parameterized by `bar_seconds`/`bars_per_day` with 5-minute defaults  
    preserved (26/26 unit tests pass).

## Nested walk-forward results (`single_account_walkforward_15m.md`)

| fold | long pick | short pick | test PnL | test Sharpe | trades |
| --- | --- | --- | --- | --- | --- |
| f1 | bb\_squeeze W672 T1.5 H4 trend\_adx new\_york | close\_vs\_ema200 W2016 T1.5 H28 trend\_adx all | \-$70.86 | \-0.914 | 84 |
| f2 | atr\_28\_pct W2016 T1.5 H28 trend london | rsi\_14 W672 T2 H4 none overlap | \-$50.70 | \-1.631 | 35 |
| f3 | natr\_14 W672 T1.5 H28 none all | close\_vs\_ema200 W672 T2 H28 trend\_adx overlap | +$24.62 | +0.256 | 58 |
| f4 | natr\_14 W672 T1.5 H28 trend\_not\_choppy all | aroon\_down\_25 W672 T2 H28 none all | +$407.37 | +1.449 | 42 |

All four folds picked `none` (hold-expiry) on the winning side, replicating  
the 5-minute attribution. Train-prefix Sharpes ran 3.9..7.4 against test  
\-1.6..+1.4: selection overfitting is more pronounced at 15 minutes because  
each fold offers fewer effective trades.

## Cross-timeframe transfer test (preregistered hypothesis)

The locked 5-minute specification (long plus\_di\_14 z>=+2.0 W6048 H84 New  
York; short aroon\_up\_25 z>=+1.5 W6048 H84 London -- the short leg fades  
extreme fresh-high strength, direction "high"; exit none; windows/holds  
rescaled by bar count) evaluated unmodified on 15-minute bars  
(`scripts/run_15m_transfer_test.py`):

| segment | exit | PnL | Sharpe | maxDD | trades | win rate |
| --- | --- | --- | --- | --- | --- | --- |
| research | none | +$1,158.81 | +1.202 | \-$421.13 | 350 | 55.7% |
| research | stop12 | +$1,133.31 | +1.176 | \-$421.13 | 350 | 55.7% |
| research | stop16 | +$1,158.81 | +1.202 | \-$421.13 | 350 | 55.7% |
| dev (diagnostic) | none | \-$147.07 | \-0.890 | \-$346.42 | 40 | 42.5% |
| dev (diagnostic) | stop12 | \-$137.31 | \-0.864 | \-$336.66 | 40 | 42.5% |
| dev (diagnostic) | stop16 | \-$180.79 | \-1.098 | \-$380.14 | 40 | 42.5% |

Audit note: two earlier transfer runs are superseded. The first used an
inverted short-leg direction (z extreme low instead of extreme high) and
produced 29 spurious conflicts; the second fixed the direction but reported
Sharpes annualized with the 5m constant sqrt(288\*252), inflating them by
sqrt(3). The table above is the corrected, authoritative run: short-leg
direction "high" (zero same-bar conflicts) and Sharpe annualized with
sqrt(96\*252), the correct constant for 15-minute bars.

Findings:

1.  The signal family is not a 5-minute microstructure artifact. The same
    specification keeps a positive research edge at 15 minutes (+1.20
    Sharpe vs +2.44 at 5m, each annualized at its own bar frequency), the
    win rate is intact (55.7%), and trade count drops to 350. The
    risk-adjusted edge is materially weaker at the coarser timeframe but
    retains its character.
2.  The dev-segment failure generalizes across timeframes (-0.89 at 15m with
    only 40 trades, same sign at 5m). The 2026-03..2026-09 regime is hostile
    to this momentum z-score family regardless of sampling rate.
3.  The catastrophic-cap conclusion carries over: 12/16x ATR caps cost  
    almost nothing in-sample (93-100% retention) and slightly reduce  
    dev-segment losses at 12x.
4.  With the correct leg direction, same-bar long/short conflicts are zero  
    at 15 minutes; no conflict adjudication rule is needed for the  
    transferred pair.

## Program-level verdict

Three independent evidence lines converge:

-   5m mining: strong research slice, dev diagnostic fails -> no candidate.
-   15m independent mining: 4 folds, 4 different picks -> no candidate.
-   15m transfer of the locked 5m spec: in-sample transfer works, dev fails  
    the same way -> failure is regime driven.

Standing order: freeze the specification, do not deploy, accumulate at least  
six continuous months of data after 2026-09-09, then run one pre-locked  
evaluation exactly once. No further mining on the existing history.

## Reproduction

```
python scripts/run_single_account_research_15m.py   # nested WF, writes report/single_account_walkforward_15m.md
python scripts/run_15m_transfer_test.py             # transfer test table above
python -m unittest                                  # 26 tests, all pass

```