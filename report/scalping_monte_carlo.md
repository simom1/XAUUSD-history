# Monte Carlo robustness -- rank-aggregation scalping config (5m)

- research: 2023-09-13 04:55:00 -> 2026-03-09 23:55:00 (175475 bars)
- dev (excluded): 2026-03-10 -> 2026-09-09 03:45:00
- bootstrap: 2000 samples, block size 288 bars (1 day)
- RNG seed: 20260911

- selected config: `z_composite:N5:W288:T1.5:V2:H24:trend_adx:overlap:none`
- factor family (top-15): `candle_body_pct, clv, close_vs_ema9, zscore_20, bb_pct_b, close_vs_ema12, kc_pos, donchian_pos, close_vs_sma10, rsi_6, close_vs_sma20_pct, close_vs_sma20, close_vs_wma20, momentum_10_pct, cci_14`
- active factors (top-5): `candle_body_pct, clv, close_vs_ema9, zscore_20, bb_pct_b`
- train Sharpe: +2.757, 283 trades

## Test 1 -- factor-family perturbation

Drop 1-2 factors from the top-5 set and re-evaluate. This measures sensitivity to the specific factor choice.

- base family (top-5): `candle_body_pct, clv, close_vs_ema9, zscore_20, bb_pct_b`

- base: Sharpe +2.757, PnL $+1,128.35, 283 trades

### Drop 1 factor

| dropped | n | sharpe | pnl | trades | wr | delta_sh |
|---:|---:|---:|---:|---:|---:|---:|
| bb_pct_b | 4 | 2.736 | 1159.200 | 322 | 59.600 | -0.022 |
| zscore_20 | 4 | 2.736 | 1159.200 | 322 | 59.600 | -0.022 |
| candle_body_pct | 4 | 2.674 | 1073.120 | 258 | 59.700 | -0.084 |
| clv | 4 | 2.552 | 1032.640 | 269 | 56.900 | -0.205 |
| close_vs_ema9 | 4 | 2.339 | 893.930 | 245 | 57.100 | -0.418 |


### Drop 2 factors (sampled)

| dropped | n | sharpe | pnl | trades | delta_sh |
|---:|---:|---:|---:|---:|---:|
| candle_body_pct+bb_pct_b | 3 | 2.877 | 1216.260 | 298 | 0.120 |
| candle_body_pct+zscore_20 | 3 | 2.877 | 1216.260 | 298 | 0.120 |
| candle_body_pct+close_vs_ema9 | 3 | 2.596 | 979.090 | 224 | -0.161 |
| clv+zscore_20 | 3 | 2.591 | 1087.120 | 309 | -0.166 |
| clv+bb_pct_b | 3 | 2.591 | 1087.120 | 309 | -0.166 |
| close_vs_ema9+bb_pct_b | 3 | 2.526 | 1004.310 | 273 | -0.232 |
| close_vs_ema9+zscore_20 | 3 | 2.526 | 1004.310 | 273 | -0.232 |
| zscore_20+bb_pct_b | 3 | 2.241 | 1038.520 | 421 | -0.516 |
| clv+close_vs_ema9 | 3 | 2.079 | 776.500 | 223 | -0.678 |
| candle_body_pct+clv | 3 | 1.973 | 724.800 | 240 | -0.785 |


- drop-1 Sharpe range: [+2.339, +2.736]
- drop-1 mean |delta Sharpe|: 0.150
- all perturbations: mean |delta Sharpe| = 0.262
- all perturbations: max |delta Sharpe| = 0.785
- robustness: MODERATE

## Test 2 -- parameter perturbation

Shift each aggregation parameter by +/-1 grid step and re-evaluate. Measures sensitivity to parameter choice.

- base config: `z_composite:N5:W288:T1.5:V2:H24:trend_adx:overlap:none`

- base: Sharpe +2.757, PnL $+1,128.35, 283 trades

### Parameter perturbations

| perturbation | new_val | sharpe | pnl | trades | wr | delta_sh |
|---:|---:|---:|---:|---:|---:|---:|
| N+ | 7 | 2.757 | 1128.350 | 283 | 58.700 | 0.000 |
| window+ | 576 | 2.173 | 752.100 | 253 | 59.300 | -0.584 |
| hold- | 12 | 1.807 | 552.960 | 303 | 57.400 | -0.951 |
| thr+ | 2 | 1.069 | 221.450 | 132 | 57.600 | -1.688 |


- mean |delta Sharpe|: 0.806
- max |delta Sharpe|: 1.688
- robustness: LOW

## Test 3 -- block bootstrap (Sharpe CI)

Resample per-bar returns in blocks of B=288 bars (1 day) with replacement, recompute Sharpe. 2000 bootstrap samples.

- base: Sharpe +2.757, 175475 bars, 609 blocks of 288
- trades: 283, WR 58.7%

- bootstrap mean Sharpe: +2.747
- bootstrap std: 0.583
- 95% CI: [+1.550, +3.850]
- P(Sharpe > 0): 100.0%
- base Sharpe +2.757 is inside the CI

### Bootstrap Sharpe distribution

  [ +0.97]  (3)
  [ +1.14] ## (10)
  [ +1.31] #### (24)
  [ +1.49] ####### (36)
  [ +1.66] ########## (51)
  [ +1.83] ################ (82)
  [ +2.01] ###################### (111)
  [ +2.18] ################################### (175)
  [ +2.35] ######################################## (200)
  [ +2.53] ################################################## (244)
  [ +2.70] ############################################### (231)
  [ +2.87] ########################################## (206)
  [ +3.05] ############################################ (216)
  [ +3.22] ############################ (137)
  [ +3.39] ##################### (104)
  [ +3.57] ################# (86)
  [ +3.74] ########## (50)
  [ +3.91] #### (20)
  [ +4.09] # (7)
  [ +4.26]  (2)

## Overall robustness verdict

- factor-family max |delta Sharpe|: 0.785
- parameter max |delta Sharpe|: 1.688
- bootstrap 95% CI: [+1.550, +3.850]
- P(Sharpe > 0): 100.0%

**MODERATELY ROBUST**: 2/3 tests pass. The config is moderately stable under perturbation.

