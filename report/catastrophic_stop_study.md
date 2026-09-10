# Catastrophic-stop study (0.01 lot = 1 oz)

- research: 2023-09-13 04:55:00 -> 2026-03-09 23:55:00 (175475 bars)
- consumed development segment (diagnostic only): 2026-03-10 00:00:00 -> 2026-09-09 03:45:00
- pairs: top-3 long x top-3 short components by the walk-forward fast-path score (research prefix only).
- exits compared: none, stop2_5, stop5, stop6, stop8, stop12, stop16; retention = pnl(exit) / pnl(none) per pair.
- selection rule fixed in advance: max research 5m Sharpe with >= 100 trades; the development segment never selects anything.

## Research results

| pair | exit | pnl | sharpe | maxdd | trades | worst_trade | p05_trade | stop_exits | stopped_pnl | retention_vs_none |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| long:di_ratio:W2016:T1.5:H84:none:all + short:aroon_up_25:W6048:T1.5:H84:none:london | none | 2640.21 | 2.323 | -257.31 | 1121 | -120.84 | -24.47 | 0 | 0.0 | 1.0 |
| long:di_ratio:W2016:T1.5:H84:none:all + short:aroon_up_25:W6048:T1.5:H84:none:london | stop2_5 | 238.26 | 0.255 | -507.45 | 1121 | -64.02 | -17.36 | 681 | -5292.75 | 0.09 |
| long:di_ratio:W2016:T1.5:H84:none:all + short:aroon_up_25:W6048:T1.5:H84:none:london | stop5 | 898.36 | 0.849 | -365.95 | 1121 | -87.84 | -23.54 | 399 | -5269.57 | 0.34 |
| long:di_ratio:W2016:T1.5:H84:none:all + short:aroon_up_25:W6048:T1.5:H84:none:london | stop6 | 1324.89 | 1.224 | -302.37 | 1121 | -87.84 | -24.4 | 309 | -4426.79 | 0.502 |
| long:di_ratio:W2016:T1.5:H84:none:all + short:aroon_up_25:W6048:T1.5:H84:none:london | stop8 | 1817.19 | 1.643 | -292.88 | 1121 | -112.13 | -24.68 | 192 | -3440.12 | 0.688 |
| long:di_ratio:W2016:T1.5:H84:none:all + short:aroon_up_25:W6048:T1.5:H84:none:london | stop12 | 2210.25 | 1.97 | -321.78 | 1121 | -185.31 | -25.32 | 80 | -1989.36 | 0.837 |
| long:di_ratio:W2016:T1.5:H84:none:all + short:aroon_up_25:W6048:T1.5:H84:none:london | stop16 | 2356.34 | 2.09 | -348.69 | 1121 | -212.22 | -25.5 | 41 | -1366.44 | 0.892 |
| long:di_ratio:W2016:T1.5:H84:none:all + short:aroon_up_25:W6048:T1.5:H84:trend:london | none | 2481.15 | 2.237 | -296.21 | 1087 | -120.84 | -24.26 | 0 | 0.0 | 1.0 |
| long:di_ratio:W2016:T1.5:H84:none:all + short:aroon_up_25:W6048:T1.5:H84:trend:london | stop2_5 | -109.41 | -0.123 | -513.64 | 1087 | -64.02 | -17.48 | 664 | -5171.28 | -0.044 |
| long:di_ratio:W2016:T1.5:H84:none:all + short:aroon_up_25:W6048:T1.5:H84:trend:london | stop5 | 719.17 | 0.707 | -319.52 | 1087 | -87.84 | -23.41 | 393 | -5133.89 | 0.29 |
| long:di_ratio:W2016:T1.5:H84:none:all + short:aroon_up_25:W6048:T1.5:H84:trend:london | stop6 | 1156.94 | 1.108 | -250.25 | 1087 | -87.84 | -23.79 | 306 | -4391.3 | 0.466 |
| long:di_ratio:W2016:T1.5:H84:none:all + short:aroon_up_25:W6048:T1.5:H84:trend:london | stop8 | 1668.09 | 1.56 | -287.5 | 1087 | -112.13 | -24.45 | 193 | -3491.42 | 0.672 |
| long:di_ratio:W2016:T1.5:H84:none:all + short:aroon_up_25:W6048:T1.5:H84:trend:london | stop12 | 2081.79 | 1.904 | -360.68 | 1087 | -185.31 | -24.83 | 79 | -1969.82 | 0.839 |
| long:di_ratio:W2016:T1.5:H84:none:all + short:aroon_up_25:W6048:T1.5:H84:trend:london | stop16 | 2197.28 | 1.998 | -387.59 | 1087 | -212.22 | -25.09 | 41 | -1366.44 | 0.886 |
| long:di_ratio:W2016:T1.5:H84:none:all + short:aroon_up_25:W2016:T1.5:H12:none:overlap | none | 2274.77 | 2.276 | -247.74 | 1161 | -120.84 | -21.95 | 0 | 0.0 | 1.0 |
| long:di_ratio:W2016:T1.5:H84:none:all + short:aroon_up_25:W2016:T1.5:H12:none:overlap | stop2_5 | -122.58 | -0.156 | -639.11 | 1161 | -68.32 | -16.26 | 666 | -5124.62 | -0.054 |
| long:di_ratio:W2016:T1.5:H84:none:all + short:aroon_up_25:W2016:T1.5:H12:none:overlap | stop5 | 660.65 | 0.724 | -372.5 | 1161 | -87.84 | -22.04 | 379 | -4873.77 | 0.29 |
| long:di_ratio:W2016:T1.5:H84:none:all + short:aroon_up_25:W2016:T1.5:H12:none:overlap | stop6 | 1106.2 | 1.177 | -315.45 | 1161 | -87.84 | -21.91 | 289 | -4056.97 | 0.486 |
| long:di_ratio:W2016:T1.5:H84:none:all + short:aroon_up_25:W2016:T1.5:H12:none:overlap | stop8 | 1469.32 | 1.525 | -248.24 | 1161 | -112.13 | -22.79 | 192 | -3496.86 | 0.646 |
| long:di_ratio:W2016:T1.5:H84:none:all + short:aroon_up_25:W2016:T1.5:H12:none:overlap | stop12 | 1908.0 | 1.942 | -312.21 | 1161 | -185.31 | -22.33 | 80 | -2018.79 | 0.839 |
| long:di_ratio:W2016:T1.5:H84:none:all + short:aroon_up_25:W2016:T1.5:H12:none:overlap | stop16 | 2015.62 | 2.037 | -339.12 | 1161 | -212.22 | -22.24 | 40 | -1322.23 | 0.886 |
| long:plus_di_14:W6048:T2:H84:none:new_york + short:aroon_up_25:W6048:T1.5:H84:none:london | none | 2099.69 | 2.436 | -178.07 | 443 | -64.02 | -24.81 | 0 | 0.0 | 1.0 |
| long:plus_di_14:W6048:T2:H84:none:new_york + short:aroon_up_25:W6048:T1.5:H84:none:london | stop2_5 | 912.81 | 1.207 | -219.46 | 443 | -64.02 | -17.2 | 223 | -2086.44 | 0.435 |
| long:plus_di_14:W6048:T2:H84:none:new_york + short:aroon_up_25:W6048:T1.5:H84:none:london | stop5 | 1406.1 | 1.701 | -243.66 | 443 | -64.02 | -24.57 | 122 | -1843.43 | 0.67 |
| long:plus_di_14:W6048:T2:H84:none:new_york + short:aroon_up_25:W6048:T1.5:H84:none:london | stop6 | 1373.97 | 1.646 | -259.44 | 443 | -64.02 | -26.07 | 100 | -1723.27 | 0.654 |
| long:plus_di_14:W6048:T2:H84:none:new_york + short:aroon_up_25:W6048:T1.5:H84:none:london | stop8 | 1707.35 | 2.021 | -194.65 | 443 | -64.02 | -27.58 | 51 | -1115.15 | 0.813 |
| long:plus_di_14:W6048:T2:H84:none:new_york + short:aroon_up_25:W6048:T1.5:H84:none:london | stop12 | 1949.0 | 2.287 | -178.07 | 443 | -64.02 | -25.11 | 15 | -426.27 | 0.928 |
| long:plus_di_14:W6048:T2:H84:none:new_york + short:aroon_up_25:W6048:T1.5:H84:none:london | stop16 | 2009.44 | 2.338 | -178.07 | 443 | -64.02 | -25.11 | 7 | -234.15 | 0.957 |
| long:plus_di_14:W6048:T2:H84:none:new_york + short:aroon_up_25:W6048:T1.5:H84:trend:london | none | 1900.11 | 2.366 | -158.47 | 417 | -64.02 | -21.88 | 0 | 0.0 | 1.0 |
| long:plus_di_14:W6048:T2:H84:none:new_york + short:aroon_up_25:W6048:T1.5:H84:trend:london | stop2_5 | 584.46 | 0.831 | -213.64 | 417 | -64.02 | -17.26 | 205 | -1945.67 | 0.308 |
| long:plus_di_14:W6048:T2:H84:none:new_york + short:aroon_up_25:W6048:T1.5:H84:trend:london | stop5 | 1241.65 | 1.602 | -189.16 | 417 | -64.02 | -22.65 | 109 | -1586.57 | 0.653 |
| long:plus_di_14:W6048:T2:H84:none:new_york + short:aroon_up_25:W6048:T1.5:H84:trend:london | stop6 | 1255.72 | 1.606 | -193.38 | 417 | -64.02 | -25.04 | 89 | -1482.22 | 0.661 |
| long:plus_di_14:W6048:T2:H84:none:new_york + short:aroon_up_25:W6048:T1.5:H84:trend:london | stop8 | 1561.25 | 1.971 | -193.77 | 417 | -64.02 | -27.04 | 49 | -1048.07 | 0.822 |
| long:plus_di_14:W6048:T2:H84:none:new_york + short:aroon_up_25:W6048:T1.5:H84:trend:london | stop12 | 1805.6 | 2.259 | -158.47 | 417 | -64.02 | -22.43 | 15 | -396.33 | 0.95 |
| long:plus_di_14:W6048:T2:H84:none:new_york + short:aroon_up_25:W6048:T1.5:H84:trend:london | stop16 | 1809.86 | 2.261 | -158.47 | 417 | -64.02 | -24.72 | 7 | -234.15 | 0.953 |
| long:plus_di_14:W6048:T2:H84:none:new_york + short:aroon_up_25:W2016:T1.5:H12:none:overlap | none | 1536.58 | 2.352 | -179.74 | 486 | -68.32 | -18.23 | 0 | 0.0 | 1.0 |
| long:plus_di_14:W6048:T2:H84:none:new_york + short:aroon_up_25:W2016:T1.5:H12:none:overlap | stop2_5 | 468.64 | 0.833 | -339.48 | 486 | -68.32 | -15.83 | 211 | -1936.01 | 0.305 |
| long:plus_di_14:W6048:T2:H84:none:new_york + short:aroon_up_25:W2016:T1.5:H12:none:overlap | stop5 | 1011.32 | 1.614 | -212.09 | 486 | -68.32 | -20.07 | 100 | -1406.91 | 0.658 |
| long:plus_di_14:W6048:T2:H84:none:new_york + short:aroon_up_25:W2016:T1.5:H12:none:overlap | stop6 | 1025.71 | 1.616 | -204.11 | 486 | -68.32 | -22.18 | 81 | -1292.21 | 0.668 |
| long:plus_di_14:W6048:T2:H84:none:new_york + short:aroon_up_25:W2016:T1.5:H12:none:overlap | stop8 | 1274.39 | 1.982 | -212.47 | 486 | -68.32 | -22.52 | 41 | -833.52 | 0.829 |
| long:plus_di_14:W6048:T2:H84:none:new_york + short:aroon_up_25:W2016:T1.5:H12:none:overlap | stop12 | 1492.12 | 2.297 | -154.97 | 486 | -68.32 | -18.94 | 13 | -320.83 | 0.971 |
| long:plus_di_14:W6048:T2:H84:none:new_york + short:aroon_up_25:W2016:T1.5:H12:none:overlap | stop16 | 1468.03 | 2.256 | -192.8 | 486 | -68.32 | -20.08 | 7 | -235.72 | 0.955 |
| long:plus_di_14:W6048:T2:H84:trend:new_york + short:aroon_up_25:W6048:T1.5:H84:none:london | none | 2072.27 | 2.414 | -178.07 | 422 | -64.02 | -25.12 | 0 | 0.0 | 1.0 |
| long:plus_di_14:W6048:T2:H84:trend:new_york + short:aroon_up_25:W6048:T1.5:H84:none:london | stop2_5 | 896.52 | 1.191 | -219.94 | 422 | -64.02 | -17.33 | 214 | -2027.33 | 0.433 |
| long:plus_di_14:W6048:T2:H84:trend:new_york + short:aroon_up_25:W6048:T1.5:H84:none:london | stop5 | 1382.77 | 1.68 | -243.66 | 422 | -64.02 | -25.1 | 117 | -1793.83 | 0.667 |
| long:plus_di_14:W6048:T2:H84:trend:new_york + short:aroon_up_25:W6048:T1.5:H84:none:london | stop6 | 1359.94 | 1.635 | -259.44 | 422 | -64.02 | -26.26 | 95 | -1664.37 | 0.656 |
| long:plus_di_14:W6048:T2:H84:trend:new_york + short:aroon_up_25:W6048:T1.5:H84:none:london | stop8 | 1677.24 | 1.994 | -211.47 | 422 | -64.02 | -27.67 | 49 | -1099.03 | 0.809 |
| long:plus_di_14:W6048:T2:H84:trend:new_york + short:aroon_up_25:W6048:T1.5:H84:none:london | stop12 | 1954.25 | 2.302 | -178.07 | 422 | -64.02 | -25.12 | 14 | -378.52 | 0.943 |
| long:plus_di_14:W6048:T2:H84:trend:new_york + short:aroon_up_25:W6048:T1.5:H84:none:london | stop16 | 1982.02 | 2.315 | -178.07 | 422 | -64.02 | -25.3 | 7 | -234.15 | 0.956 |
| long:plus_di_14:W6048:T2:H84:trend:new_york + short:aroon_up_25:W6048:T1.5:H84:trend:london | none | 1872.69 | 2.343 | -158.47 | 396 | -64.02 | -23.65 | 0 | 0.0 | 1.0 |
| long:plus_di_14:W6048:T2:H84:trend:new_york + short:aroon_up_25:W6048:T1.5:H84:trend:london | stop2_5 | 568.17 | 0.812 | -219.94 | 396 | -64.02 | -17.34 | 196 | -1886.56 | 0.303 |
| long:plus_di_14:W6048:T2:H84:trend:new_york + short:aroon_up_25:W6048:T1.5:H84:trend:london | stop5 | 1218.32 | 1.58 | -206.86 | 396 | -64.02 | -24.53 | 104 | -1536.97 | 0.651 |
| long:plus_di_14:W6048:T2:H84:trend:new_york + short:aroon_up_25:W6048:T1.5:H84:trend:london | stop6 | 1241.69 | 1.595 | -211.08 | 396 | -64.02 | -25.63 | 84 | -1423.32 | 0.663 |
| long:plus_di_14:W6048:T2:H84:trend:new_york + short:aroon_up_25:W6048:T1.5:H84:trend:london | stop8 | 1531.14 | 1.942 | -211.47 | 396 | -64.02 | -27.66 | 47 | -1031.95 | 0.818 |
| long:plus_di_14:W6048:T2:H84:trend:new_york + short:aroon_up_25:W6048:T1.5:H84:trend:london | stop12 | 1810.85 | 2.276 | -158.47 | 396 | -64.02 | -22.48 | 14 | -348.58 | 0.967 |
| long:plus_di_14:W6048:T2:H84:trend:new_york + short:aroon_up_25:W6048:T1.5:H84:trend:london | stop16 | 1782.44 | 2.237 | -158.47 | 396 | -64.02 | -25.04 | 7 | -234.15 | 0.952 |
| long:plus_di_14:W6048:T2:H84:trend:new_york + short:aroon_up_25:W2016:T1.5:H12:none:overlap | none | 1499.69 | 2.315 | -171.74 | 463 | -68.32 | -18.86 | 0 | 0.0 | 1.0 |
| long:plus_di_14:W6048:T2:H84:trend:new_york + short:aroon_up_25:W2016:T1.5:H12:none:overlap | stop2_5 | 443.88 | 0.796 | -363.08 | 463 | -68.32 | -16.14 | 202 | -1882.19 | 0.296 |
| long:plus_di_14:W6048:T2:H84:trend:new_york + short:aroon_up_25:W2016:T1.5:H12:none:overlap | stop5 | 992.83 | 1.597 | -252.47 | 463 | -68.32 | -20.41 | 94 | -1342.78 | 0.662 |
| long:plus_di_14:W6048:T2:H84:trend:new_york + short:aroon_up_25:W2016:T1.5:H12:none:overlap | stop6 | 1019.82 | 1.62 | -227.46 | 463 | -68.32 | -22.24 | 75 | -1215.48 | 0.68 |
| long:plus_di_14:W6048:T2:H84:trend:new_york + short:aroon_up_25:W2016:T1.5:H12:none:overlap | stop8 | 1234.81 | 1.938 | -242.32 | 463 | -68.32 | -23.2 | 39 | -817.4 | 0.823 |
| long:plus_di_14:W6048:T2:H84:trend:new_york + short:aroon_up_25:W2016:T1.5:H12:none:overlap | stop12 | 1487.9 | 2.31 | -168.55 | 463 | -68.32 | -18.95 | 12 | -273.08 | 0.992 |
| long:plus_di_14:W6048:T2:H84:trend:new_york + short:aroon_up_25:W2016:T1.5:H12:none:overlap | stop16 | 1431.14 | 2.219 | -184.8 | 463 | -68.32 | -20.49 | 7 | -235.72 | 0.954 |

## Research selection

- long: `long:plus_di_14:W6048:T2:H84:none:new_york`
- short: `short:aroon_up_25:W6048:T1.5:H84:none:london`
- exit: `none`
- research: PnL $+2,099.69, 5m Sharpe 2.44, maxDD $-178.07, 443 trades, worst trade $-64.02
- retention vs none on this pair: 1.000 (0 stop exits, stopped PnL $+0.00)

## Consumed development diagnostic (not used for selection)

- `none`: PnL $-94.49, 5m Sharpe -0.52, maxDD $-443.17, 69 trades, worst trade $-98.32, stop exits 0

## Interpretation

- The selector chose no stop: on every pair in the ladder the no-exit variant holds the highest research Sharpe, so every fixed ATR stop width measured so far costs edge.
- Without a stop the worst research trade is $-64.02 (p05 $-24.81, 443 trades); hold-based expiry plus the daily session flat already bound the tail, so the effective risk cap is the position size.
- Stop ladder on this pair -- stop5 triggers 27.5%, retains 0.670; stop8 triggers 11.5%, retains 0.813; stop12 triggers 3.4%, retains 0.928; stop16 triggers 1.6%, retains 0.957. Narrow rungs are regular exits, not insurance; only the widest rungs approach true disaster protection.
- The no-exit variant already bounds holding time via the hold-based expiry; a catastrophic stop only caps gap risk and runaway adverse excursions.
