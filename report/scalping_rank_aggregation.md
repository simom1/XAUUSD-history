# Rank-aggregation research -- scalping factor adaptation (5m)

- research: 2023-09-13 04:55:00 -> 2026-03-09 23:55:00 (175475 bars)
- dev (excluded): 2026-03-10 -> 2026-09-09 03:45:00
- folds: 4 x 183-day test, expanding train prefix
- aggregation: 3 methods, N=(5, 7, 10), W=(288, 576), T=(1.5, 2.0), V=(2, 3, 4), H=(6, 12, 24)
- regimes: ('none', 'trend', 'trend_adx', 'trend_not_choppy')
- sessions: ('all', 'london', 'new_york', 'overlap')
- exits: ('none', 'stop1_5', 'trail2')

## Phase 1 -- baseline: original nested-WF (factor-pair)

Reproduces `run_scalping_nested_wf.py`: for each fold, IC screening -> component screen -> exit ladder on the train prefix, then evaluate the selected factor pair on the test period.

- existing report: `report\scalping_nested_wf.md`
- (see that report for per-fold details)

- known result: **2/4 positive folds** (factor-pair selection overfits)
- root cause: 4 folds selected 4 different long + 4 different short factors
- structural dimensions were stable (exit=none, window=288-576, family=reversal, regime=trend variants, session=active)

## Phase 2 -- factor family (IC screening, reversal factors)

- full-period top-15 reversal factors (by |ICIR|@h=12):
  `candle_body_pct, clv, close_vs_ema9, zscore_20, bb_pct_b, close_vs_ema12, kc_pos, donchian_pos, close_vs_sma10, rsi_6, close_vs_sma20_pct, close_vs_sma20, close_vs_wma20, momentum_10_pct, cci_14`

  fold f1: `di_spread, di_ratio, linreg_slope_20, kc_pos, plus_di_14, close_vs_ema21, close_vs_ema26, rsi_14, close_vs_sma20, close_vs_sma20_pct`
  fold f2: `close_vs_ema26, di_ratio, di_spread, close_vs_ema21, plus_di_14, kc_pos, rsi_14, close_vs_ema12, clv, close_vs_ema9`
  fold f3: `candle_body_pct, kc_pos, close_vs_ema9, close_vs_ema21, close_vs_ema12, rsi_6, close_vs_ema26, cci_14, clv, bb_pct_b`
  fold f4: `clv, close_vs_ema9, close_vs_sma10, close_vs_ema12, candle_body_pct, rsi_6, bb_pct_b, zscore_20, close_vs_wma20, kc_pos`

- avg pairwise Jaccard (top-10): 0.331
- factors common to all 4 folds (top-10): `kc_pos` (1 factors)
- this is the **stable family** that rank aggregation exploits

## Phase 3 -- aggregation parameter grid (research period)

- family: `candle_body_pct, clv, close_vs_ema9, zscore_20, bb_pct_b, close_vs_ema12, kc_pos, donchian_pos, close_vs_sma10, rsi_6, close_vs_sma20_pct, close_vs_sma20, close_vs_wma20, momentum_10_pct, cci_14`
- grid size: 15552 configs (3 methods x 3 N x 2 W x 2 T x 3 V x 3 H x 4 R x 4 S x 3 E)
- z_cache: pre-computing rolling z-scores for 2 windows x 15 factors = 30 arrays

- eligible (avg > 0, trades >= 20): 6303 / 15552

### Top 15 -- `vote`

| N | W | T | V | H | regime | session | exit | pnl | sharpe | trades |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 10 | 288 | 1.500 | 3 | 24 | trend_adx | overlap | trail2 | 1054.920 | 2.518 | 632 |
| 10 | 288 | 1.500 | 3 | 24 | trend_adx | overlap | stop1_5 | 1054.920 | 2.518 | 632 |
| 10 | 288 | 1.500 | 3 | 24 | trend_adx | overlap | none | 1054.920 | 2.518 | 632 |
| 10 | 288 | 1.500 | 3 | 24 | trend_adx | new_york | trail2 | 1162.950 | 2.409 | 936 |
| 10 | 288 | 1.500 | 3 | 24 | trend_adx | new_york | stop1_5 | 1162.950 | 2.409 | 936 |
| 10 | 288 | 1.500 | 3 | 24 | trend_adx | new_york | none | 1162.950 | 2.409 | 936 |
| 10 | 576 | 1.500 | 3 | 24 | trend_adx | new_york | none | 1104.490 | 2.356 | 875 |
| 10 | 576 | 1.500 | 3 | 24 | trend_adx | new_york | stop1_5 | 1104.490 | 2.356 | 875 |
| 10 | 576 | 1.500 | 3 | 24 | trend_adx | new_york | trail2 | 1104.490 | 2.356 | 875 |
| 10 | 576 | 1.500 | 3 | 24 | trend_adx | overlap | trail2 | 953.840 | 2.321 | 589 |
| 10 | 576 | 1.500 | 3 | 24 | trend_adx | overlap | stop1_5 | 953.840 | 2.321 | 589 |
| 10 | 576 | 1.500 | 3 | 24 | trend_adx | overlap | none | 953.840 | 2.321 | 589 |
| 10 | 288 | 1.500 | 4 | 24 | trend_adx | overlap | stop1_5 | 859.740 | 2.238 | 480 |
| 10 | 288 | 1.500 | 4 | 24 | trend_adx | overlap | trail2 | 859.740 | 2.238 | 480 |
| 10 | 288 | 1.500 | 4 | 24 | trend_adx | overlap | none | 859.740 | 2.238 | 480 |


### Top 15 -- `rank_avg`

(none)


### Top 15 -- `z_composite`

| N | W | T | V | H | regime | session | exit | pnl | sharpe | trades |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 5 | 288 | 1.500 | 3 | 24 | trend_adx | overlap | none | 1128.350 | 2.757 | 566 |
| 5 | 288 | 1.500 | 3 | 24 | trend_adx | overlap | trail2 | 1128.350 | 2.757 | 566 |
| 5 | 288 | 1.500 | 3 | 24 | trend_adx | overlap | stop1_5 | 1128.350 | 2.757 | 566 |
| 5 | 288 | 1.500 | 2 | 24 | trend_adx | overlap | stop1_5 | 1128.350 | 2.757 | 566 |
| 5 | 288 | 1.500 | 2 | 24 | trend_adx | overlap | none | 1128.350 | 2.757 | 566 |
| 5 | 288 | 1.500 | 4 | 24 | trend_adx | overlap | trail2 | 1128.350 | 2.757 | 566 |
| 5 | 288 | 1.500 | 4 | 24 | trend_adx | overlap | none | 1128.350 | 2.757 | 566 |
| 5 | 288 | 1.500 | 2 | 24 | trend_adx | overlap | trail2 | 1128.350 | 2.757 | 566 |
| 5 | 288 | 1.500 | 4 | 24 | trend_adx | overlap | stop1_5 | 1128.350 | 2.757 | 566 |
| 5 | 288 | 1.500 | 4 | 24 | trend_adx | new_york | stop1_5 | 1278.840 | 2.678 | 966 |
| 5 | 288 | 1.500 | 3 | 24 | trend_adx | new_york | trail2 | 1278.840 | 2.678 | 966 |
| 5 | 288 | 1.500 | 4 | 24 | trend_adx | new_york | none | 1278.840 | 2.678 | 966 |
| 5 | 288 | 1.500 | 4 | 24 | trend_adx | new_york | trail2 | 1278.840 | 2.678 | 966 |
| 5 | 288 | 1.500 | 2 | 24 | trend_adx | new_york | stop1_5 | 1278.840 | 2.678 | 966 |
| 5 | 288 | 1.500 | 2 | 24 | trend_adx | new_york | trail2 | 1278.840 | 2.678 | 966 |


### Engine re-score (top 20)

| method | N | W | H | regime | session | exit | pnl | sharpe | maxdd | trades | wr | pf |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| z_composite | 5 | 288 | 24 | trend_adx | overlap | none | 1128.350 | 2.757 | -109.550 | 283 | 58.700 | 2.357 |
| z_composite | 5 | 288 | 24 | trend_adx | overlap | none | 1128.350 | 2.757 | -109.550 | 283 | 58.700 | 2.357 |
| z_composite | 5 | 288 | 24 | trend_adx | overlap | none | 1128.350 | 2.757 | -109.550 | 283 | 58.700 | 2.357 |
| z_composite | 5 | 288 | 24 | trend_adx | new_york | none | 1267.480 | 2.675 | -113.620 | 478 | 56.900 | 2.021 |
| z_composite | 5 | 288 | 24 | trend_adx | new_york | none | 1267.480 | 2.675 | -113.620 | 478 | 56.900 | 2.021 |
| z_composite | 5 | 288 | 24 | trend_adx | new_york | none | 1267.480 | 2.675 | -113.620 | 478 | 56.900 | 2.021 |
| z_composite | 10 | 288 | 24 | trend_adx | overlap | stop1_5 | 609.110 | 1.730 | -100.790 | 261 | 41.400 | 1.601 |
| z_composite | 5 | 288 | 24 | trend_adx | overlap | stop1_5 | 494.460 | 1.382 | -138.700 | 283 | 40.300 | 1.442 |
| z_composite | 5 | 288 | 24 | trend_adx | overlap | stop1_5 | 494.460 | 1.382 | -138.700 | 283 | 40.300 | 1.442 |
| z_composite | 5 | 288 | 24 | trend_adx | overlap | stop1_5 | 494.460 | 1.382 | -138.700 | 283 | 40.300 | 1.442 |
| z_composite | 5 | 288 | 24 | trend_adx | new_york | stop1_5 | 464.960 | 1.115 | -178.370 | 478 | 43.500 | 1.284 |
| z_composite | 5 | 288 | 24 | trend_adx | new_york | stop1_5 | 464.960 | 1.115 | -178.370 | 478 | 43.500 | 1.284 |
| z_composite | 5 | 288 | 24 | trend_adx | new_york | stop1_5 | 464.960 | 1.115 | -178.370 | 478 | 43.500 | 1.284 |
| z_composite | 10 | 288 | 24 | trend_adx | overlap | trail2 | -275.680 | -1.085 | -342.990 | 261 | 32.200 | 0.697 |
| z_composite | 5 | 288 | 24 | trend_adx | overlap | trail2 | -348.190 | -1.329 | -407.440 | 283 | 32.200 | 0.644 |
| z_composite | 5 | 288 | 24 | trend_adx | overlap | trail2 | -348.190 | -1.329 | -407.440 | 283 | 32.200 | 0.644 |
| z_composite | 5 | 288 | 24 | trend_adx | overlap | trail2 | -348.190 | -1.329 | -407.440 | 283 | 32.200 | 0.644 |
| z_composite | 5 | 288 | 24 | trend_adx | new_york | trail2 | -534.620 | -1.596 | -588.950 | 478 | 36.600 | 0.646 |
| z_composite | 5 | 288 | 24 | trend_adx | new_york | trail2 | -534.620 | -1.596 | -588.950 | 478 | 36.600 | 0.646 |
| z_composite | 5 | 288 | 24 | trend_adx | new_york | trail2 | -534.620 | -1.596 | -588.950 | 478 | 36.600 | 0.646 |


- **best aggregation config**: `z_composite:N5:W288:T1.5:V3:H24:trend_adx:overlap:none`
  Sharpe +2.757, PnL $+1,128.35, 283 trades, WR 58.7%, maxDD $-109.55

## Phase 4 -- fully nested walk-forward (aggregation)

For each fold, re-run IC screening -> aggregation grid -> engine re-score on the **train prefix only**, then evaluate the selected aggregation config on the test period.

### Per-fold results

#### Fold f1 (2024-03-07 -> 2024-09-06)

- **config**: `vote:N5:W576:T2:V4:H24:trend_adx:all:none`
- factors: `di_spread, di_ratio, linreg_slope_20, kc_pos, plus_di_14`
- train: Sharpe +2.847, 19 trades
- **test: Sharpe -0.438, PnL $-3.73, 8 trades, WR 37.5%, PF 0.683, maxDD $-12.09**

Top-5 on train:

| key | sharpe | pnl |
|---:|---:|---:|
| vote:N5:W576:T2:V4:H24:trend_adx:all:none | 2.847 | 27.710 |
| vote:N5:W288:T2:V4:H24:trend_adx:all:none | 2.675 | 31.360 |
| vote:N5:W576:T2:V4:H24:trend_adx:all:stop1_5 | 2.550 | 21.400 |
| vote:N5:W288:T2:V2:H6:trend:london:none | 2.494 | 28.820 |
| vote:N5:W576:T1.5:V4:H24:trend_adx:all:none | 2.308 | 43.970 |


#### Fold f2 (2024-09-08 -> 2025-03-07)

- **config**: `z_composite:N10:W288:T1.5:V2:H24:trend_adx:overlap:none`
- factors: `close_vs_ema26, di_ratio, di_spread, close_vs_ema21, plus_di_14, kc_pos, rsi_14, close_vs_ema12, clv, close_vs_ema9`
- train: Sharpe +2.654, 75 trades
- **test: Sharpe +0.540, PnL $+21.51, 34 trades, WR 55.9%, PF 1.192, maxDD $-64.29**

Top-5 on train:

| key | sharpe | pnl |
|---:|---:|---:|
| z_composite:N10:W288:T1.5:V2:H24:trend_adx:overlap:none | 2.654 | 205.880 |
| z_composite:N10:W288:T1.5:V3:H24:trend_adx:overlap:none | 2.654 | 205.880 |
| z_composite:N10:W288:T1.5:V4:H24:trend_adx:overlap:none | 2.654 | 205.880 |
| vote:N5:W288:T2:V4:H6:trend_adx:all:none | 2.648 | 40.780 |
| vote:N7:W288:T2:V3:H6:trend_adx:overlap:none | 2.404 | 63.410 |


#### Fold f3 (2025-03-09 -> 2025-09-07)

- **config**: `z_composite:N5:W288:T2:V2:H24:trend:overlap:none`
- factors: `candle_body_pct, kc_pos, close_vs_ema9, close_vs_ema21, close_vs_ema12`
- train: Sharpe +2.499, 165 trades
- **test: Sharpe -0.626, PnL $-44.34, 57 trades, WR 45.6%, PF 0.852, maxDD $-114.40**

Top-5 on train:

| key | sharpe | pnl |
|---:|---:|---:|
| z_composite:N5:W288:T2:V2:H24:trend:overlap:none | 2.499 | 338.760 |
| z_composite:N5:W288:T2:V3:H24:trend:overlap:none | 2.499 | 338.760 |
| z_composite:N5:W288:T2:V4:H24:trend:overlap:none | 2.499 | 338.760 |
| z_composite:N5:W288:T2:V2:H24:trend:new_york:none | 2.431 | 367.000 |
| z_composite:N5:W288:T2:V3:H24:trend:new_york:none | 2.431 | 367.000 |


#### Fold f4 (2025-09-07 -> 2026-03-09)

- **config**: `z_composite:N10:W576:T1.5:V2:H24:trend:new_york:none`
- factors: `clv, close_vs_ema9, close_vs_sma10, close_vs_ema12, candle_body_pct, rsi_6, bb_pct_b, zscore_20, close_vs_wma20, kc_pos`
- train: Sharpe +2.369, 645 trades
- **test: Sharpe +0.512, PnL $+105.74, 159 trades, WR 52.8%, PF 1.097, maxDD $-248.76**

Top-5 on train:

| key | sharpe | pnl |
|---:|---:|---:|
| z_composite:N10:W576:T1.5:V2:H24:trend:new_york:none | 2.369 | 729.050 |
| z_composite:N10:W576:T1.5:V3:H24:trend:new_york:none | 2.369 | 729.050 |
| z_composite:N10:W576:T1.5:V4:H24:trend:new_york:none | 2.369 | 729.050 |
| vote:N10:W288:T1.5:V4:H24:trend:new_york:none | 2.279 | 714.680 |
| vote:N5:W288:T1.5:V3:H24:trend:new_york:none | 2.256 | 690.500 |


### Summary

| fold | method | N | W | H | exit | train_sh | test_pnl | test_sh | test_trades | test_wr | positive |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| f1 | vote | 5 | 576 | 24 | none | 2.847 | -3.730 | -0.438 | 8 | 37.500 | 0 |
| f2 | z_composite | 10 | 288 | 24 | none | 2.654 | 21.510 | 0.540 | 34 | 55.900 | 1 |
| f3 | z_composite | 5 | 288 | 24 | none | 2.499 | -44.340 | -0.626 | 57 | 45.600 | 0 |
| f4 | z_composite | 10 | 576 | 24 | none | 2.369 | 105.740 | 0.512 | 159 | 52.800 | 1 |


- positive folds: 2 / 4
- total test PnL: $+79.18
- total test trades: 258
- average test Sharpe: -0.003

### Selection stability across folds

- methods: ['vote', 'z_composite', 'z_composite', 'z_composite']
- N_factors: [5, 10, 5, 10]
- windows: [576, 288, 288, 576]
- holds: [24, 24, 24, 24]
- exits: ['none', 'none', 'none', 'none']
- unique methods: 2
- unique N: 2
- unique windows: 2
- unique holds: 1
- unique exits: 1

## Phase 5 -- comparison: aggregation vs factor-pair

| metric | factor-pair (original) | rank aggregation |
| --- | --- | --- |
| nested-WF positive folds | 2/4 | 2/4 |
| nested-WF total trades | ~227 | 258 |
| research Sharpe (best) | +3.46 (williams_r_14+donchian_pos) | +2.757 |
| research PnL (best) | — | $+1,128.35 |
| research trades (best) | 290 | 283 |
| selection variance | 4 long + 4 short factors | 2 methods, 2 N values |

## Verdict

**NOT CONFIRMED**: rank aggregation produces 2/4 positive folds with 258 total test trades, failing the preregistered gate (>= 3 positive folds, >= 100 trades). The aggregation approach does not fully resolve the selection-variance problem.

