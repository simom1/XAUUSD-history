# Single-Account Attribution — integrated long/short system

- data: 2023-09-13 -> 2026-09-09 (211,242 bars); research [0, 175475), dev [175475, 211242)
- sizing: 1 oz (0.01 lot); cost $0.16/oz round trip all-in; all PnL in USD.
- long `single|plus_di_14|long|W6048|T1.5|H120` gate `trend_up,adx_strong`; short `single|close_vs_ema200|short|W6048|T1.5|H120` gate `trend_down,adx_strong`
- unified account: opposing signals reverse at next open; same-bar dual signals flatten (1123 reversals observed).
- 'fast(close-fill)' = research fast path, protective exits marked at bar CLOSE, exits at next open, immediate re-entry allowed.
- 'engine(extreme-fill)' = BacktestEngine, protective exits fill at the adverse bar EXTREME, position locked flat until the target goes flat or opposing.

## 1. Leg x exit x accounting (research / dev, USD @ 1 oz)

| run | seg | pnl | sharpe | maxdd | trades | avg | costs |
|---|---|---:|---:|---:|---:|---:|---:|
| long_gated|fast(close-fill)|none | research | +1,807 | 1.94 | -338 | 700 | +2.58 | +112 |
| long_gated|fast(close-fill)|none | dev | -264 | -0.76 | -510 | 134 | -1.97 | +21 |
| long_gated|fast(close-fill)|stop2.5 | research | +1,072 | 1.43 | -261 | 844 | +1.27 | +135 |
| long_gated|fast(close-fill)|stop2.5 | dev | +138 | 0.50 | -468 | 163 | +0.85 | +26 |
| long_gated|engine(extreme-fill)|none | research | +1,166 | 1.14 | -467 | 843 | +1.38 | +135 |
| long_gated|engine(extreme-fill)|none | dev | -319 | -0.89 | -668 | 152 | -2.10 | +24 |
| long_gated|engine(extreme-fill)|stop2.5 | research | -609 | -0.92 | -698 | 843 | -0.72 | +135 |
| long_gated|engine(extreme-fill)|stop2.5 | dev | -210 | -0.82 | -501 | 152 | -1.38 | +24 |
| short_gated|fast(close-fill)|none | research | +205 | 0.20 | -587 | 308 | +0.67 | +49 |
| short_gated|fast(close-fill)|none | dev | +782 | 2.65 | -355 | 59 | +13.25 | +9 |
| short_gated|fast(close-fill)|stop2.5 | research | +0 | 0.00 | -634 | 372 | +0.00 | +60 |
| short_gated|fast(close-fill)|stop2.5 | dev | +546 | 2.04 | -314 | 69 | +7.91 | +11 |
| short_gated|engine(extreme-fill)|none | research | +339 | 0.32 | -566 | 410 | +0.83 | +66 |
| short_gated|engine(extreme-fill)|none | dev | +708 | 2.34 | -475 | 72 | +9.83 | +12 |
| short_gated|engine(extreme-fill)|stop2.5 | research | -733 | -0.93 | -797 | 410 | -1.79 | +66 |
| short_gated|engine(extreme-fill)|stop2.5 | dev | +145 | 0.59 | -442 | 72 | +2.01 | +12 |
| combined|engine(extreme-fill)|none | research | +1,162 | 0.83 | -902 | 1240 | +0.94 | +198 |
| combined|engine(extreme-fill)|none | dev | +632 | 1.39 | -452 | 221 | +2.86 | +35 |
| combined|engine(extreme-fill)|stop2.5 | research | -1,437 | -1.41 | -1,488 | 1240 | -1.16 | +198 |
| combined|engine(extreme-fill)|stop2.5 | dev | -52 | -0.15 | -608 | 221 | -0.23 | +35 |
| buy_hold_long(overnight) | research | +1,823 | 1.09 | -1,165 | 641 | +2.84 | +103 |
| buy_hold_long(overnight) | dev | -1,144 | -2.03 | -1,501 | 131 | -8.73 | +21 |
| always_long@trend_up(intraday) | research | +1,098 | 1.05 | -350 | 3784 | +0.29 | +605 |
| always_long@trend_up(intraday) | dev | -75 | -0.20 | -643 | 656 | -0.11 | +105 |

## 2. Deltas (research period, USD @ 1 oz)

| comparison | long leg | short leg | combined |
|---|---:|---:|---:|
| engine none -> engine stop2.5 (exit-rule cost) | +1,776 | +1,072 | +2,600 |
| sum-of-legs -> single account (both stop2.5) | - | - | -95 |
| sum-of-legs -> single account (no exits) | - | - | -343 |

## 3. Realized trades of the combined stop2.5 system (full history)

### by side x exit reason

| side | exit_reason | trades | net_pnl | avg | costs |
|---:|---:|---:|---:|---:|---:|
| short | signal | 194 | 2866.08 | 14.77 | 31.04 |
| short | stop_loss | 271 | -3548.34 | -13.09 | 43.36 |
| long | session | 2 | -4.33 | -2.17 | 0.32 |
| long | signal | 360 | 5005.49 | 13.90 | 57.60 |
| long | stop_loss | 634 | -5808.21 | -9.16 | 101.44 |

### by entry session (UTC)

| session | trades | pnl | avg |
|---:|---:|---:|---:|
| asia | 805.00 | -1111.79 | -1.38 |
| london | 278.00 | 93.12 | 0.33 |
| ny | 378.00 | -470.64 | -1.25 |
| late | - | - | - |

### by regime at entry

| regime | trades | pnl | avg |
|---:|---:|---:|---:|
| trend_down | 100 | -321.53 | -3.22 |
| trend_down+adx | 431 | -516.47 | -1.20 |
| trend_up | 128 | -93.67 | -0.73 |
| trend_up+adx | 802 | -557.64 | -0.70 |

- stop-loss exits filling at the adverse bar extreme instead of the trigger-bar close cost an exact **$1,587.21** extra on 905 stop trades (pure fill-model gap vs close, same trades).
- 'signal' exits: 13 were reversals (PnL +1.22), 541 were hold expiries (PnL +7,870.35).

## Conclusions

1. **Exit rule, not direction, is the largest controllable loss.** Moving the long leg from no-exit to a 2.5xATR fixed stop costs $+1,776 of research PnL on the engine (fill-at-extreme + re-entry lock); the short leg changes by $+1,072.
2. **Sum-of-legs vs one account:** with stop2.5 the legs sum to $-1,343 while the unified account makes $-1,437 (interaction $-95); without exits the legs sum to $+1,505 vs unified $+1,162.
3. **Fill model:** 905 stop exits filled at the bar extreme cost $1,587.21 more than the same exits at the trigger-bar close ($1.75/trade) - the fast path's mark-to-close convention materially overstated stop-system performance.
4. **Beta check:** buy-and-hold makes $+1,823 research / $-1,144 dev under identical costs; the gate-conditioned always-long makes $+1,098 research. Any candidate must beat these passive references to claim factor alpha.
5. Dev columns are diagnosis only; nothing here selects parameters.
