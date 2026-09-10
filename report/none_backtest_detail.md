# Detailed backtest report -- no-exit candidate (0.01 lot = 1 oz)

- long component: `long:plus_di_14:W6048:T2:H84:none:new_york`
- short component: `short:aroon_up_25:W6048:T1.5:H84:none:london`
- exit: `none` (hold to hold-based expiry, then daily session flat; no stop/target/trail)
- research: 2023-09-13 04:55:00 -> 2026-03-09 23:55:00 (175475 bars)
- consumed development segment (diagnostic only): 2026-03-10 00:00:00 -> 2026-09-09 03:45:00
- accounting: 10,000 capital, fills at next open mid, all-in round-trip cost $0.16/oz, 5m Sharpe annualized by sqrt(288x252), conflicts 0
- trade log: `report\none_backtest_trades.csv` (443 closed trades)

## Headline (research)

| metric | value |
|---:|---:|
|  |  |
| net PnL (1 oz) | $2,099.69 |
| 5m Sharpe (annualized) | 2.44 |
| max drawdown | $-178.07 |
| return on $10k | 21.0% |
| CAGR (calendar years) | 12.1% |
| closed trades | 443 |
| win rate | 53.3% |
| profit factor | 2.07 |
| avg win / avg loss | $17.24 / $-9.52 |
| expectancy per trade | $4.74 |
| gross PnL / total costs | $2,170.57 / $70.88 |
| worst / best trade | $-64.02 / $196.89 |
| avg bars held (median) | 58 (69) |
| time in market | 14.7% |

## Per side

| side | trades | pnl | win_rate | avg_trade | worst | avg_bars |
|---:|---:|---:|---:|---:|---:|---:|
| long | 341 | $957.64 | 54.0% | $2.81 | $-45.78 | 56 |
| short | 102 | $1,142.05 | 51.0% | $11.20 | $-64.02 | 66 |

## Exit reasons

| exit_reason | trades | pnl | share_of_trades | avg |
|---:|---:|---:|---:|---:|
| signal | 438 | $2,080.26 | 98.9% | $4.75 |
| session | 5 | $19.43 | 1.1% | $3.89 |

## Trade PnL distribution (1 oz)

| quantile | net_pnl |
|---:|---:|
| p1 | $-36.26 |
| p5 | $-24.81 |
| p25 | $-5.21 |
| p50 | $0.51 |
| p75 | $9.49 |
| p95 | $40.34 |
| p99 | $105.94 |

## Worst / best trades

| entry | exit | side | entry_px | exit_px | exit_reason | net_pnl |
|---:|---:|---:|---:|---:|---:|---:|
| 2026-01-29 16:30:00+00:00 | 2026-01-29 20:45:00+00:00 | short | 5289.97 | 5353.83 | signal | $-64.02 |
| 2025-10-20 07:45:00+00:00 | 2025-10-20 13:20:00+00:00 | short | 4234.19 | 4293.16 | signal | $-59.13 |
| 2024-06-21 13:05:00+00:00 | 2024-06-21 20:00:00+00:00 | long | 2367.82 | 2322.20 | signal | $-45.78 |
| 2024-08-02 13:35:00+00:00 | 2024-08-02 20:30:00+00:00 | long | 2473.57 | 2431.96 | signal | $-41.77 |
| 2024-11-13 13:35:00+00:00 | 2024-11-13 20:30:00+00:00 | long | 2612.05 | 2575.85 | signal | $-36.36 |
| 2026-01-29 08:25:00+00:00 | 2026-01-29 15:20:00+00:00 | short | 5530.28 | 5333.23 | signal | $196.89 |
| 2026-02-04 10:05:00+00:00 | 2026-02-04 17:00:00+00:00 | short | 5051.48 | 4904.07 | signal | $147.25 |
| 2026-02-12 16:00:00+00:00 | 2026-02-12 20:45:00+00:00 | short | 5060.42 | 4921.52 | signal | $138.74 |
| 2026-01-30 07:25:00+00:00 | 2026-01-30 14:20:00+00:00 | short | 5179.01 | 5054.51 | signal | $124.34 |
| 2025-10-21 07:00:00+00:00 | 2025-10-21 13:55:00+00:00 | short | 4323.17 | 4207.77 | signal | $115.24 |

## Entry hour (UTC) PnL

| utc_hour | trades | pnl | avg |
|---:|---:|---:|---:|
| 00:00 | 94 | $168.94 | $1.80 |
| 07:00 | 19 | $281.21 | $14.80 |
| 08:00 | 16 | $252.73 | $15.80 |
| 09:00 | 14 | $38.54 | $2.75 |
| 10:00 | 7 | $152.19 | $21.74 |
| 11:00 | 4 | $26.12 | $6.53 |
| 12:00 | 5 | $43.07 | $8.61 |
| 13:00 | 117 | $392.75 | $3.36 |
| 14:00 | 48 | $353.62 | $7.37 |
| 15:00 | 35 | $152.16 | $4.35 |
| 16:00 | 22 | $125.92 | $5.72 |
| 17:00 | 11 | $-28.69 | $-2.61 |
| 18:00 | 13 | $96.93 | $7.46 |
| 19:00 | 12 | $-10.97 | $-0.91 |
| 20:00 | 26 | $55.17 | $2.12 |

## Monthly PnL (realized at exit)

| month | pnl | trades | win_rate |
|---:|---:|---:|---:|
| 2023-09 | $-29.74 | 1 | 0% |
| 2023-10 | $53.69 | 18 | 67% |
| 2023-11 | $43.91 | 12 | 67% |
| 2023-12 | $40.09 | 14 | 50% |
| 2024-01 | $-77.85 | 12 | 17% |
| 2024-02 | $28.94 | 16 | 69% |
| 2024-03 | $56.60 | 10 | 60% |
| 2024-04 | $42.20 | 13 | 77% |
| 2024-05 | $20.19 | 13 | 62% |
| 2024-06 | $-10.13 | 12 | 58% |
| 2024-07 | $28.94 | 15 | 47% |
| 2024-08 | $-48.89 | 16 | 19% |
| 2024-09 | $-27.11 | 14 | 57% |
| 2024-10 | $72.16 | 15 | 53% |
| 2024-11 | $38.26 | 17 | 53% |
| 2024-12 | $-11.48 | 9 | 44% |
| 2025-01 | $-14.14 | 14 | 43% |
| 2025-02 | $59.87 | 15 | 53% |
| 2025-03 | $17.69 | 7 | 57% |
| 2025-04 | $88.38 | 24 | 46% |
| 2025-05 | $181.21 | 13 | 69% |
| 2025-06 | $-14.69 | 13 | 38% |
| 2025-07 | $58.21 | 12 | 67% |
| 2025-08 | $63.23 | 18 | 56% |
| 2025-09 | $44.19 | 20 | 45% |
| 2025-10 | $285.97 | 38 | 45% |
| 2025-11 | $42.05 | 11 | 55% |
| 2025-12 | $36.44 | 15 | 53% |
| 2026-01 | $473.55 | 15 | 67% |
| 2026-02 | $507.09 | 19 | 68% |
| 2026-03 | $50.86 | 2 | 100% |

## Yearly summary

| year | pnl | trades | win_rate | worst_trade |
|---:|---:|---:|---:|---:|
| 2023 | $107.95 | 45 | 60% | $-29.74 |
| 2024 | $111.83 | 162 | 51% | $-45.78 |
| 2025 | $848.41 | 200 | 50% | $-59.13 |
| 2026 | $1,031.50 | 36 | 69% | $-64.02 |

## Top-5 drawdown episodes

| peak | trough | depth | length_days |
|---:|---:|---:|---:|
| 2025-09-25 19:55:00+00:00 | 2025-10-09 14:20:00+00:00 | $-178.07 | 16.7 |
| 2026-01-30 09:45:00+00:00 | 2026-01-30 11:55:00+00:00 | $-158.47 | 1.2 |
| 2024-06-12 14:15:00+00:00 | 2024-10-07 12:50:00+00:00 | $-124.30 | 99.8 |
| 2026-01-29 16:40:00+00:00 | 2026-01-29 17:40:00+00:00 | $-118.11 | 0.6 |
| 2025-10-31 00:50:00+00:00 | 2025-11-10 14:30:00+00:00 | $-113.06 | 30.9 |

## Consumed development segment (diagnostic only -- never selects anything)

| metric | value |
|---:|---:|
|  |  |
| net PnL (1 oz) | $-94.49 |
| 5m Sharpe (annualized) | -0.52 |
| max drawdown | $-443.17 |
| return on $10k | -0.9% |
| CAGR (calendar years) | -2.8% |
| closed trades | 69 |
| win rate | 39.1% |
| profit factor | 0.88 |
| avg win / avg loss | $26.82 / $-19.49 |
| expectancy per trade | $-1.37 |
| gross PnL / total costs | $-83.45 / $11.04 |
| worst / best trade | $-98.32 / $72.48 |
| avg bars held (median) | 51 (45) |
| time in market | 9.8% |

- stop-exit events: 0 (the `none` exit has no stop; this row is 0 by construction)

## Reading notes

- Per-side and hourly tables use realized trade PnL (net of the all-in cost).
- Monthly attribution uses the exit time; a trade spanning a month boundary lands entirely in its exit month.
- The development segment is already consumed: its numbers may not be used to pick or justify anything. The next legitimate evaluation is a single pass on >= 6 months of new data.
