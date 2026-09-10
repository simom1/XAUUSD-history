## Backtest report — ema_cross_9_21

- period: 2023-09-13 → 2026-09-09 (2.99y, 5m bars)
- engine: next-open fills | all-in cost $0.16/oz round-trip ($0.08/side) | commission 0.0 bps
- session: intraday flat 20:55 UTC (Fri 20:45)

| metric | value |
|---|---:|
| total return | +51.59% |
| CAGR | +14.93% |
| Sharpe (5m USD PnL, ann.) | 0.23 |
| Sortino (5m USD PnL) | 0.27 |
| max drawdown | -68.35% |
| trades | 9323 (10.0/day) |
| win rate | 29.1% |
| profit factor | 1.02 |
| avg net PnL/trade | $+5.53 |
| avg holding | 20.4 bars (102 min) |
| exposure (time in market) | 90.0% |
| total friction paid | $149,168 |
| final equity | $151,590 |
| runtime | 0.1s |

> Note: fixed-oz position sizing; margin/interest not modeled. Equity can go negative for always-in-market strategies at this leverage (100 oz ≈ 2.6x notional on $100k at $2,600/oz).

### exits by reason

| reason | trades | net PnL |
|---|---:|---:|
| session | 27 | $+10,910 |
| signal | 9296 | $+40,680 |
