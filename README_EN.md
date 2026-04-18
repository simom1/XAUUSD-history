# XAUUSD Historical Market Data

> 🌐 Language: [中文](./README.md) | **English**

---

## Overview

This repository contains historical OHLCV price data for **17 financial instruments** at the **H1 (1-hour)** timeframe, exported from MetaTrader 5. Data spans from as early as 2007 up to April 2026, with over **1.1 million rows** in total.

---

## File Structure

Each file follows the naming convention: `{SYMBOL}_H1.csv`

### Columns

| Column | Type | Description |
|---|---|---|
| `time` | datetime | Bar open time (UTC) |
| `open` | float | Opening price |
| `high` | float | Highest price of the bar |
| `low` | float | Lowest price of the bar |
| `close` | float | Closing price |
| `tick_volume` | int | Number of ticks (volume proxy) |

### Sample Row

```
time,open,high,low,close,tick_volume
2007-06-22 03:00:00,651.3,656.3,650.6,653.9,881
```

---

## Instruments

### Precious Metals

| File | Symbol | Rows | From | To |
|---|---|---|---|---|
| `XAUUSD_H1.csv` | Gold / USD | 50,718 | 2007-06-22 | 2026-04-17 |
| `XAGUSD_H1.csv` | Silver / USD | 26,025 | — | 2026-04-17 |

### Forex — Majors

| File | Symbol | Rows | To |
|---|---|---|---|
| `EURUSD_H1.csv` | EUR / USD | 100,000 | 2026-04-17 |
| `GBPUSD_H1.csv` | GBP / USD | 100,000 | 2026-04-17 |
| `AUDUSD_H1.csv` | AUD / USD | 100,000 | 2026-04-17 |
| `NZDUSD_H1.csv` | NZD / USD | 21,181 | 2026-04-17 |
| `USDCAD_H1.csv` | USD / CAD | 88,774 | 2026-04-17 |
| `USDCHF_H1.csv` | USD / CHF | 100,000 | 2026-04-17 |
| `USDJPY_H1.csv` | USD / JPY | 100,000 | 2026-04-17 |

### Forex — Crosses

| File | Symbol | Rows | To |
|---|---|---|---|
| `EURJPY_H1.csv` | EUR / JPY | 8,725 | 2026-04-17 |
| `EURGBP_H1.csv` | EUR / GBP | 100,000 | 2026-04-17 |
| `EURAUD_H1.csv` | EUR / AUD | 14,965 | 2026-04-17 |
| `GBPJPY_H1.csv` | GBP / JPY | 100,000 | 2026-04-17 |
| `GBPAUD_H1.csv` | GBP / AUD | 100,000 | 2026-04-17 |
| `AUDJPY_H1.csv` | AUD / JPY | 100,000 | 2026-04-17 |

### Commodities (Oil)

| File | Symbol | Rows | To |
|---|---|---|---|
| `UKOIL_H1.csv` | Brent Crude Oil | 18,734 | 2026-04-17 |
| `USOIL_H1.csv` | WTI Crude Oil | 8,281 | 2026-04-17 |

---

## Quick Start (Python)

```python
import pandas as pd

df = pd.read_csv("XAUUSD_H1.csv", parse_dates=["time"], index_col="time")

print(df.head())
print(f"Total bars: {len(df)}")
print(f"Date range: {df.index.min()} → {df.index.max()}")
```

---

## Notes

- Data exported from **MetaTrader 5** via the Python `MetaTrader5` library
- Timeframe: **H1** — each row represents 1 hour
- `tick_volume` counts the number of price ticks within the bar, not real traded volume. Commonly used as a volume proxy in forex markets
- Some instruments have fewer rows due to limited broker history availability
- All timestamps are in **UTC**

---

## Related Project

This dataset is part of the **SINERGY ML BOT** project — a machine learning-based multi-symbol trading system that uses H1 data for signal generation and backtesting.
