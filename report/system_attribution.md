# Single-account attribution (0.01 lot = 1 oz)

- research: 2023-09-13 04:55:00 -> 2026-03-09 23:55:00
- development segment excluded: 2026-03-10 -> 2026-09-09 03:45:00
- cost: $0.16 round trip per 1 oz; capital: $10,000.

### long only, no exit

- PnL: $+1166.15; 5m Sharpe: 1.14; max DD: $-467.15

| exit reason | trades | PnL | avg trade | costs |
|---|---:|---:|---:|---:|
| session | 6 | $+21.50 | $+3.58 | $0.96 |
| signal | 837 | $+1144.65 | $+1.37 | $133.92 |

### short only, no exit

- PnL: $+339.07; 5m Sharpe: 0.32; max DD: $-566.05

| exit reason | trades | PnL | avg trade | costs |
|---|---:|---:|---:|---:|
| session | 1 | $-23.14 | $-23.14 | $0.16 |
| signal | 409 | $+362.21 | $+0.89 | $65.44 |

### combined, no exit

- PnL: $+1162.17; 5m Sharpe: 0.83; max DD: $-902.47

| exit reason | trades | PnL | avg trade | costs |
|---|---:|---:|---:|---:|
| session | 7 | $-1.64 | $-0.23 | $1.12 |
| signal | 1233 | $+1163.81 | $+0.94 | $197.28 |

### long only, 2.5 ATR stop

- PnL: $-609.48; 5m Sharpe: -0.92; max DD: $-697.69

| exit reason | trades | PnL | avg trade | costs |
|---|---:|---:|---:|---:|
| session | 2 | $-4.33 | $-2.17 | $0.32 |
| signal | 309 | $+3526.73 | $+11.41 | $49.44 |
| stop_loss | 532 | $-4131.88 | $-7.77 | $85.12 |

### short only, 2.5 ATR stop

- PnL: $-733.28; 5m Sharpe: -0.93; max DD: $-796.79

| exit reason | trades | PnL | avg trade | costs |
|---|---:|---:|---:|---:|
| signal | 170 | $+1899.37 | $+11.17 | $27.20 |
| stop_loss | 240 | $-2632.65 | $-10.97 | $38.40 |

### combined, 2.5 ATR stop

- PnL: $-1437.47; 5m Sharpe: -1.41; max DD: $-1488.02

| exit reason | trades | PnL | avg trade | costs |
|---|---:|---:|---:|---:|
| session | 2 | $-4.33 | $-2.17 | $0.32 |
| signal | 471 | $+5344.49 | $+11.35 | $75.36 |
| stop_loss | 767 | $-6777.63 | $-8.84 | $122.72 |

## Comparison

| case                     |      pnl |    sharpe |    maxdd |   trades |   conflicts |
|:-------------------------|---------:|----------:|---------:|---------:|------------:|
| long only, no exit       |  1166.15 |  1.13811  |  -467.15 |      843 |           0 |
| short only, no exit      |   339.07 |  0.319439 |  -566.05 |      410 |           0 |
| combined, no exit        |  1162.17 |  0.83306  |  -902.47 |     1240 |           0 |
| long only, 2.5 ATR stop  |  -609.48 | -0.920573 |  -697.69 |      843 |           0 |
| short only, 2.5 ATR stop |  -733.28 | -0.929888 |  -796.79 |      410 |           0 |
| combined, 2.5 ATR stop   | -1437.47 | -1.40639  | -1488.02 |     1240 |           0 |

## Interpretation

Compare the combined cases with the sum of their legs: any gap is caused by single-account reversals and mutual position replacement. Compare each no-exit/stop pair to isolate the conservative ATR exit effect.

