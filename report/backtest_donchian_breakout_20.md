## Backtest report — donchian_breakout_20

- period: 2023-09-13 → 2026-09-09 (2.99y, 5m bars)
- engine: next-open fills | all-in cost $0.16/oz round-trip ($0.08/side) | commission 0.0 bps
- session: intraday flat 20:55 UTC (Fri 20:45)

| metric | value |
|---|---:|
| total return | -44.50% |
| CAGR | -17.88% |
| Sharpe (daily, ann.) | -0.52 |
| Sortino | -0.35 |
| max drawdown | -126.36% |
| trades | 5221 (5.6/day) |
| win rate | 35.0% |
| profit factor | 0.98 |
| avg net PnL/trade | $-8.52 |
| avg holding | 36.4 bars (182 min) |
| exposure (time in market) | 90.0% |
| total friction paid | $83,536 |
| final equity | $55,502 |
| runtime | 0.1s |

> Note: fixed-oz position sizing; margin/interest not modeled. Equity can go negative for always-in-market strategies at this leverage (100 oz ≈ 2.6x notional on $100k at $2,600/oz).

### exits by reason

| reason | trades | net PnL |
|---|---:|---:|
| session | 27 | $+8,219 |
| signal | 5194 | $-52,725 |
