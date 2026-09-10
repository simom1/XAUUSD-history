# Volatility-targeted sizing vs fixed 1 oz (15m bars)

- data: XAUUSD 15m only; research period excludes the consumed development set.
- research: 2023-09-13 04:45:00 -> 2026-03-09 23:45:00
- development segment (untouched): 2026-03-10 -> 2026-09-09 03:45:00
- signals (unchanged, 15m transfer spec from scripts/run_15m_transfer_test.py): long `long:plus_di_14:W2016:T2:H28:none:new_york`, short `short:aroon_up_25:W2016:T1.5:H28:none:london`, no protective exit; 15m Sharpe annualized with 96 bars/day.
- sizing rule (pre-specified): oz_t = clip(1.0 * median(atr_14, 672)_t / atr_14_t, 0.25, 2.0); 672 15m bars = the 5m study's 7-day median window; size and signal decided at the same bar close, trailing data only; the size is frozen for the whole position episode (entry/reversal bar decides), keeping the trade stream identical to fixed sizing.
- sanity: fixed-1oz research PnL reproduces the corrected transfer-test research row ($+1,158.81).

## Walk-forward fold comparison

| fold | case | PnL | 15m Sharpe | maxDD | trades | avg oz | costs |
|---|---|---:|---:|---:|---:|---:|---:|
| f1 | fixed | $-7.73 | -0.08 | $-122.72 | 74 | 1.0 | $11.84 |
| f1 | vol | $+22.36 | 0.28 | $-84.84 | 74 | 0.87 | $10.30 |
| f2 | fixed | $+192.78 | 2.25 | $-88.28 | 75 | 1.0 | $12.00 |
| f2 | vol | $+154.70 | 1.96 | $-64.77 | 75 | 0.888 | $10.65 |
| f3 | fixed | $+333.61 | 2.91 | $-67.93 | 60 | 1.0 | $9.60 |
| f3 | vol | $+231.01 | 2.43 | $-68.46 | 60 | 0.882 | $8.47 |
| f4 | fixed | $+578.19 | 1.46 | $-421.13 | 95 | 1.0 | $15.20 |
| f4 | vol | $+403.66 | 1.33 | $-232.93 | 95 | 0.965 | $14.67 |

## Whole research period

| case           |     pnl |   sharpe |   maxdd |   trades |   avg_oz |   costs |
|:---------------|--------:|---------:|--------:|---------:|---------:|--------:|
| research fixed | 1158.81 |    1.202 | -421.13 |      350 |    1     |   56    |
| research vol   |  849.76 |    1.127 | -232.93 |      350 |    0.886 |   49.62 |

`avg_oz` is the mean trade size realized inside the segment; `maxdd` is in USD on the 1-account equity path.

## Sensitivity (whole research period, reported not selected)

| floor | cap | PnL | 15m Sharpe | maxDD | trades | avg oz | costs |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 0.25 | 1.5 | $+878.25 | 1.19 | $-232.93 | 350 | 0.88 | $49.27 |
| 0.25 | 2.0 | $+849.76 | 1.13 | $-232.93 | 350 | 0.886 | $49.62 |
| 0.25 | 3.0 | $+847.39 | 1.12 | $-232.93 | 350 | 0.887 | $49.66 |
| 0.5 | 1.5 | $+892.86 | 1.18 | $-232.93 | 350 | 0.884 | $49.48 |
| 0.5 | 2.0 | $+864.38 | 1.11 | $-232.93 | 350 | 0.89 | $49.84 |
| 0.5 | 3.0 | $+862.00 | 1.11 | $-232.93 | 350 | 0.891 | $49.87 |

## Interpretation

Vol targeting trades the same signal stream: trade count is identical (session-boundary effects aside), so differences come purely from sizing. This is a sizing-layer diagnostic on the 15m transfer spec, not a new candidate; no parameter is selected from the sensitivity grid.

