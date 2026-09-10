# 15m walk-forward fold diagnosis (research slice only)

- research: 2023-09-13 04:45:00 -> 2026-03-09 23:45:00; development from 2026-03-10 never read.
- rebuilds each fold-selected system from `single_account_fold_picks_15m.csv` and decomposes its test block: monthly completed-trade PnL, exit contributions, concentration.
- diagnostic only: nothing here selects or re-ranks anything.

## f1  2024-03-07->2024-09-06  (exit `none`)
- long `long:bb_squeeze:W672:T1.5:H4:trend_adx:new_york` / short `short:close_vs_ema200:W2016:T1.5:H28:trend_adx:all`; train-prefix Sharpe 7.39 (15m annualized).
- test block: equity PnL $-70.86, 15m Sharpe -0.91, maxDD $-131.31, 84 completed trades, win rate 33.3%, completed-trade PnL $-70.86.
- concentration: 3 worst trades $-77.08 (109% of completed PnL), 3 best $+136.71 (-193%).

### Monthly completed-trade PnL
| month   |   trades |    pnl |
|:--------|---------:|-------:|
| 2024-03 |       14 | -62.61 |
| 2024-04 |       12 |  -7.91 |
| 2024-05 |       13 |  31.05 |
| 2024-06 |       11 |   7.76 |
| 2024-07 |       15 |  66.78 |
| 2024-08 |       14 | -48.92 |
| 2024-09 |        5 | -57.01 |

### Exit contributions
| exit    |   trades |     pnl |   avg |
|:--------|---------:|--------:|------:|
| session |        8 |   52.51 |  6.56 |
| signal  |       76 | -123.37 | -1.62 |

## f2  2024-09-08->2025-03-07  (exit `none`)
- long `long:atr_28_pct:W2016:T1.5:H28:trend:london` / short `short:rsi_14:W672:T2:H4:none:overlap`; train-prefix Sharpe 4.84 (15m annualized).
- test block: equity PnL $-50.70, 15m Sharpe -1.63, maxDD $-84.28, 35 completed trades, win rate 40.0%, completed-trade PnL $-50.70.
- concentration: 3 worst trades $-50.67 (100% of completed PnL), 3 best $+32.81 (-65%).

### Monthly completed-trade PnL
| month   |   trades |    pnl |
|:--------|---------:|-------:|
| 2024-09 |        7 |   4.09 |
| 2024-10 |        3 |   6.82 |
| 2024-11 |        4 | -16.28 |
| 2024-12 |        8 | -39.58 |
| 2025-01 |       10 | -20.11 |
| 2025-02 |        1 |  13.58 |
| 2025-03 |        2 |   0.78 |

### Exit contributions
| exit   |   trades |    pnl |   avg |
|:-------|---------:|-------:|------:|
| signal |       35 | -50.70 | -1.45 |

## f3  2025-03-09->2025-09-07  (exit `none`)
- long `long:natr_14:W672:T1.5:H28:none:all` / short `short:close_vs_ema200:W672:T2:H28:trend_adx:overlap`; train-prefix Sharpe 3.90 (15m annualized).
- test block: equity PnL $+24.62, 15m Sharpe 0.26, maxDD $-179.33, 58 completed trades, win rate 46.6%, completed-trade PnL $+24.62.
- concentration: 3 worst trades $-106.55 (-433% of completed PnL), 3 best $+108.96 (443%).

### Monthly completed-trade PnL
| month   |   trades |    pnl |
|:--------|---------:|-------:|
| 2025-03 |        9 |   7.54 |
| 2025-04 |        7 |  88.22 |
| 2025-05 |       13 | -30.94 |
| 2025-06 |       11 | -35.04 |
| 2025-07 |        9 |   0.87 |
| 2025-08 |        9 |  -6.03 |

### Exit contributions
| exit    |   trades |    pnl |   avg |
|:--------|---------:|-------:|------:|
| session |        6 |  44.50 |  7.42 |
| signal  |       52 | -19.88 | -0.38 |

## f4  2025-09-07->2026-03-09  (exit `none`)
- long `long:natr_14:W672:T1.5:H28:trend_not_choppy:all` / short `short:aroon_down_25:W672:T2:H28:none:all`; train-prefix Sharpe 4.21 (15m annualized).
- test block: equity PnL $+407.37, 15m Sharpe 1.45, maxDD $-252.98, 42 completed trades, win rate 47.6%, completed-trade PnL $+407.37.
- concentration: 3 worst trades $-129.79 (-32% of completed PnL), 3 best $+334.20 (82%).

### Monthly completed-trade PnL
| month   |   trades |    pnl |
|:--------|---------:|-------:|
| 2025-09 |        4 | -21.64 |
| 2025-10 |       12 | 158.57 |
| 2025-11 |        8 |  85.72 |
| 2025-12 |        1 |  -4.67 |
| 2026-01 |       13 | 161.53 |
| 2026-02 |        4 |  27.86 |

### Exit contributions
| exit    |   trades |    pnl |   avg |
|:--------|---------:|-------:|------:|
| session |        2 |  -8.15 | -4.08 |
| signal  |       40 | 415.52 | 10.39 |

