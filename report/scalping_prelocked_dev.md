# Pre-locked dev evaluation -- rank-aggregation scalping config (5m)

- research: 2023-09-13 04:55:00 -> 2026-03-09 23:55:00 (175475 bars)
- dev: 2026-03-10 00:00:00 -> 2026-09-09 03:45:00 (35767 bars)
- acceptance gates: Sharpe > 0.0, maxDD > -15.0%, trades >= 50

## Step 1 -- freeze config on research period

- config: `z_composite:N5:W288:T1.5:V2:H24:trend_adx:overlap:none`
- method: `z_composite`, N=5, window=288, threshold=1.5, vote_min=2, hold=24
- regime: `trend_adx`, session: `overlap`, exit: `none`
- factor family (top-15): `candle_body_pct, clv, close_vs_ema9, zscore_20, bb_pct_b, close_vs_ema12, kc_pos, donchian_pos, close_vs_sma10, rsi_6, close_vs_sma20_pct, close_vs_sma20, close_vs_wma20, momentum_10_pct, cci_14`
- active factors (top-5): `candle_body_pct, clv, close_vs_ema9, zscore_20, bb_pct_b`
- research Sharpe: +2.757
- research PnL: $+1,128.35
- research maxDD: $-109.55
- research trades: 283, WR 58.7%, PF 2.357
- research avg hold: 23.2 bars

## Step 2 -- dev evaluation (frozen config)

- dev period: 2026-03-10 00:00:00 -> 2026-09-09 03:45:00 (35767 bars)
- config is frozen from Step 1; no re-selection on dev.

- dev Sharpe: +1.763
- dev PnL: $+191.70
- dev maxDD: $-156.08
- dev trades: 49, WR 53.1%, PF 1.678
- dev avg hold: 23.0 bars
- dev best trade: $+53.89
- dev worst trade: $-26.21

## Step 3 -- diagnostics

### 3a -- research vs dev comparison

| period | bars | sharpe | pnl | maxdd | trades | wr | pf | avg_hold |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| research | 175475 | 2.757 | 1128.350 | -109.550 | 283 | 58.700 | 2.357 | 23.200 |
| dev | 35767 | 1.763 | 191.700 | -156.080 | 49 | 53.100 | 1.678 | 23.000 |


- Sharpe decay: -36.0% (dev vs research)
- PnL per bar: research $+0.0064, dev $+0.0054
- Trade frequency: research 1.61/kbar, dev 1.37/kbar

### 3b -- dev monthly breakdown

| month | n | pnl | wr |
|---:|---:|---:|---:|
| 2026-03 | 6 | 98.440 | 100.000 |
| 2026-04 | 8 | 20.440 | 37.500 |
| 2026-05 | 6 | 20.660 | 66.700 |
| 2026-06 | 6 | -45.810 | 33.300 |
| 2026-07 | 12 | -69.850 | 33.300 |
| 2026-08 | 7 | 150.980 | 85.700 |
| 2026-09 | 4 | 16.840 | 25.000 |


### 3c -- factor family IC on dev (reversal stability)

| factor | dev_ic | dev_icir | still_reversal |
|---:|---:|---:|---:|
| candle_body_pct | -0.008 | -1.126 | yes |
| clv | -0.010 | -1.006 | yes |
| close_vs_ema9 | -0.003 | -0.126 | yes |
| zscore_20 | 0.002 | 0.066 | NO |
| bb_pct_b | 0.002 | 0.066 | NO |

- factors still reversal on dev: 3 / 5
- UNSTABLE: < 70% of factors retain reversal IC on dev

### 3d -- dev trade list (first 10 + last 10)

**First 10 trades:**

| entry_time | side | bars_held | net_pnl |
|---:|---:|---:|---:|
| 2026-03-11 14:05:00 | S | 23 | 19.420 |
| 2026-03-18 14:05:00 | S | 23 | 21.570 |
| 2026-03-19 13:55:00 | S | 23 | 13.570 |
| 2026-03-20 16:15:00 | S | 23 | 20.630 |
| 2026-03-27 16:40:00 | L | 23 | 2.570 |
| 2026-03-30 14:20:00 | L | 23 | 20.680 |
| 2026-04-07 14:35:00 | S | 23 | -9.740 |
| 2026-04-09 16:50:00 | L | 23 | -14.050 |
| 2026-04-14 15:05:00 | L | 23 | 13.670 |
| 2026-04-16 15:10:00 | S | 23 | 16.070 |

**Last 10 trades:**

| entry_time | side | bars_held | net_pnl |
|---:|---:|---:|---:|
| 2026-08-04 15:20:00 | L | 23 | 23.140 |
| 2026-08-05 13:00:00 | L | 23 | 53.890 |
| 2026-08-05 16:00:00 | L | 23 | 16.410 |
| 2026-08-11 13:55:00 | L | 23 | -11.230 |
| 2026-08-21 13:35:00 | L | 23 | 28.900 |
| 2026-08-26 13:50:00 | S | 23 | 20.570 |
| 2026-09-01 13:45:00 | S | 23 | -2.440 |
| 2026-09-02 15:15:00 | L | 23 | -2.870 |
| 2026-09-03 13:50:00 | L | 23 | 36.600 |
| 2026-09-04 13:45:00 | S | 23 | -14.450 |


### 3e -- regime/session distribution (research vs dev)

Regime active percentage (long side):

| regime | research_pct | dev_pct |
|---:|---:|---:|
| none | 100.000 | 100.000 |
| trend | 58.100 | 46.400 |
| trend_adx | 22.500 | 20.900 |
| trend_not_choppy | 28.700 | 23.600 |


Session active percentage:

| session | research_pct | dev_pct |
|---:|---:|---:|
| all | 100.000 | 100.000 |
| london | 43.800 | 43.600 |
| new_york | 34.800 | 34.500 |
| overlap | 17.500 | 17.400 |


## Verdict

- dev Sharpe +1.763 > 0.0: PASS
- dev maxDD -1.6% > -15.0%: PASS
- dev trades 49 >= 50: FAIL

**MARGINAL**: 2/3 gates pass. The config shows partial out-of-sample viability but does not fully meet all criteria. Review the failing gate(s) before deployment.

