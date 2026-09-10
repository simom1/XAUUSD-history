# Volatility-targeted sizing vs fixed 1 oz

- data: XAUUSD 5m only; research period excludes the consumed development set.
- research: 2023-09-13 04:55:00 -> 2026-03-09 23:55:00
- development segment (untouched): 2026-03-10 -> 2026-09-09 03:45:00
- signals (unchanged, from report/system_attribution.md): long `long:plus_di_14:W6048:T1.5:H120:trend_adx:all`, short `short:close_vs_ema200:W6048:T1.5:H120:trend_adx:all`, no protective exit.
- sizing rule (pre-specified): oz_t = clip(1.0 * median(atr_14, 2016)_t / atr_14_t, 0.25, 2.0); size and signal decided at the same bar close, trailing data only; the size is frozen for the whole position episode (entry/reversal bar decides), keeping the trade stream identical to fixed sizing.
- sanity: fixed-1oz research PnL reproduces the attribution report ($+1,162.17).

## Walk-forward fold comparison

| fold | case | PnL | 5m Sharpe | maxDD | trades | avg oz | costs |
|---|---|---:|---:|---:|---:|---:|---:|
| f1 | fixed | $-8.74 | -0.06 | $-220.55 | 265 | 1.0 | $42.40 |
| f1 | vol | $+64.77 | 0.49 | $-162.30 | 265 | 0.809 | $34.32 |
| f2 | fixed | $+158.09 | 1.11 | $-182.36 | 253 | 1.0 | $40.48 |
| f2 | vol | $+183.73 | 1.29 | $-190.34 | 253 | 0.932 | $37.75 |
| f3 | fixed | $+464.42 | 2.07 | $-225.17 | 251 | 1.0 | $40.16 |
| f3 | vol | $+489.64 | 2.30 | $-243.56 | 251 | 0.897 | $36.02 |
| f4 | fixed | $+475.31 | 0.88 | $-902.47 | 248 | 1.0 | $39.68 |
| f4 | vol | $+452.24 | 1.10 | $-546.72 | 248 | 0.88 | $34.93 |

## Whole research period

| case           |     pnl |   sharpe |   maxdd |   trades |   avg_oz |   costs |
|:---------------|--------:|---------:|--------:|---------:|---------:|--------:|
| research fixed | 1162.17 |    0.833 | -902.47 |     1240 |    1     |  198.4  |
| research vol   | 1289.76 |    1.137 | -546.72 |     1240 |    0.872 |  172.93 |

`avg_oz` is the mean trade size realized inside the segment; `maxdd` is in USD on the 1-account equity path.

## Sensitivity (whole research period, reported not selected)

| floor | cap | PnL | 5m Sharpe | maxDD | trades | avg oz | costs |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 0.25 | 1.5 | $+1256.55 | 1.15 | $-548.63 | 1240 | 0.854 | $169.48 |
| 0.25 | 2.0 | $+1289.76 | 1.14 | $-546.72 | 1240 | 0.872 | $172.93 |
| 0.25 | 3.0 | $+1334.19 | 1.14 | $-541.74 | 1240 | 0.877 | $173.95 |
| 0.5 | 1.5 | $+1315.75 | 1.16 | $-608.44 | 1240 | 0.869 | $172.36 |
| 0.5 | 2.0 | $+1348.96 | 1.14 | $-606.68 | 1240 | 0.886 | $175.81 |
| 0.5 | 3.0 | $+1393.39 | 1.15 | $-606.68 | 1240 | 0.891 | $176.83 |

## Interpretation

Vol targeting trades the same signal stream: trade count is identical (session-boundary effects aside), so differences come purely from sizing. Compare Sharpe (cost-aware, leverage-sensitive) and maxDD (absolute risk) against the avg-oz exposure actually taken.

