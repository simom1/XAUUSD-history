# XAUUSD 5m indicator dataset - data quality report

## A. Schema

- rows: **211,242**, columns: 70 (6 price/time + 64 indicators)
- time range: **2023-09-13 04:55:00 -> 2026-09-09 03:45:00** (1091 calendar days)
- indicator columns missing: none

## B. Timestamp grid

- strictly increasing: True; duplicate timestamps: 0; not 5m-aligned: 0
- consecutive 5m steps: 210,456 / 211,241 (99.63%)
- non-5m gaps total: 785 -> intraday breaks: 625, daily closes: 7, weekend: 153

Intraday breaks (same-day gaps > 5m):
gap_h  0.166667  0.250000  0.333333  0.500000  1.000000  1.083333  1.166667  1.333333  3.583333  3.666667
count         6         2         2         1         1       135       460         1         5        12

Daily close pattern (prev_close_time -> next_open_time):
prev   cur  
18:40  23:05    2
20:55  22:00    1
21:55  23:05    3
23:35  23:05    1
- min/median/max daily-closure gap: 25.17 / 28.42 / 73.17 h

Weekend gaps: 153 (min 48.1h, max 73.2h, median 49.2h)

Long weekends / holiday closures:
               prev                 cur     gap_h
2023-12-22 21:55:00 2023-12-25 23:05:00 73.166667
2023-12-29 21:55:00 2024-01-01 23:05:00 73.166667

## C. OHLC consistency

- high < low: 0; high < max(open,close): 0; low > min(open,close): 0; non-positive prices: 0
- price range: low min **1810.44**, high max **5597.35**; first close 1909.64, last close 4378.10

## D. Zero-range candles

- high == low: 22 bars, of which open == close (fully flat): 22
- zero-range dates: ['2023-11-23', '2023-11-24', '2023-12-01', '2023-12-22', '2023-12-29', '2024-01-05', '2024-01-15', '2024-01-26', '2024-02-09', '2024-02-23', '2024-03-01', '2024-03-15', '2025-04-10', '2025-04-17', '2025-04-24', '2025-11-28']
- note: these make range-denominated indicators undefined (clv, candle anatomy, zscore if sd==0) -> structural NaNs, not data loss

## E. NaN audit per indicator column

- columns with mid-series NaN (beyond warm-up): **4**
- distinct bars affected: 22
- timestamps: ['2023-11-23 19:30', '2023-11-24 18:45', '2023-12-01 21:55', '2023-12-22 21:55', '2023-12-29 21:55', '2024-01-05 21:55', '2024-01-15 19:35', '2024-01-15 20:35', '2024-01-15 21:55', '2024-01-26 21:55', '2024-02-09 21:55', '2024-02-23 21:55', '2024-03-01 21:55', '2024-03-15 21:55', '2025-04-10 23:00', '2025-04-17 23:05', '2025-04-17 23:35', '2025-04-24 23:05', '2025-11-28 08:10', '2025-11-28 08:40', '2025-11-28 08:45', '2025-11-28 09:25']

| column | total NaN | warm-up bars | mid-series NaN |
|---|---:|---:|---:|
| candle_body_pct | 22 | 0 | 22 |
| upper_shadow_pct | 22 | 0 | 22 |
| lower_shadow_pct | 22 | 0 | 22 |
| clv | 22 | 0 | 22 |

- clean columns (only warm-up NaN): 60 / 64; max warm-up length: 199 bars (ema_200/adx-family ~expected)
- total NaN cells: 1,208 of 13,519,488 indicator cells (0.009%)
- volume column: NOT present (Gate.io TradFi klines provide no volume); volume-type indicators are out of scope by design

## F. Bounded-range checks

- violations of theoretical bounds: none

## G. Extreme 5m moves

| time | 5m return % | close |
|---|---:|---:|
| 2026-03-23 11:05:00 | +2.916 | 4407.42 |
| 2026-01-29 15:25:00 | -2.042 | 5189.18 |
| 2026-02-02 01:05:00 | -2.001 | 4660.67 |
| 2026-06-14 22:00:00 | +1.956 | 4301.38 |
| 2026-02-12 16:10:00 | -1.910 | 4953.83 |
| 2026-01-30 18:40:00 | +1.745 | 4779.24 |
| 2026-09-04 12:30:00 | -1.732 | 4394.96 |
| 2026-04-12 22:00:00 | -1.677 | 4669.62 |
| 2026-07-14 12:30:00 | +1.637 | 4096.04 |
| 2026-01-29 15:40:00 | -1.580 | 5121.61 |
- |ret| > 1%: 52 bars; > 0.5%: 424 bars

## H. Yearly coverage

| year | bars | from | to | min low | max high |
|---|---:|---|---|---:|---:|
| 2023 | 21,031 | 2023-09-13 | 2023-12-29 | 1810.44 | 2134.76 |
| 2024 | 70,915 | 2024-01-01 | 2024-12-31 | 1984.27 | 2790.11 |
| 2025 | 70,605 | 2025-01-01 | 2025-12-31 | 2614.58 | 4549.93 |
| 2026 | 48,691 | 2026-01-01 | 2026-09-09 | 3942.37 | 5597.35 |
- avg bars/day: 193.6 (5m grid would be 288 if 24h continuous)
