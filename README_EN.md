# XAUUSD Historical Market Data

> 🌐 Language: [中文](./README.md) | **English**

---

## Overview

This repository contains historical OHLCV price data for **20 major financial instruments** across multiple timeframes (M1 to W1), exported from MetaTrader 5. Data spans from as early as 2007, gets updated daily, and currently contains over **4 million rows** in total.

---

## File Structure

Files are organized by instrument, where each instrument has its own folder containing 8 different timeframes:
- Directory naming: `{SYMBOL}/`
- File naming convention: `{SYMBOL}/{SYMBOL}_{TIMEFRAME}.csv`

### Supported Timeframes

| Code | Timeframe | Description |
|---|---|---|
| `M1` | 1 Minute | 1-minute bar |
| `M5` | 5 Minutes | 5-minute bar |
| `M15` | 15 Minutes | 15-minute bar |
| `M30` | 30 Minutes | 30-minute bar |
| `H1` | 1 Hour | 1-hour bar |
| `H4` | 4 Hours | 4-hour bar |
| `D1` | Daily | Daily bar |
| `W1` | Weekly | Weekly bar |

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

All MT5 historical market data includes 8 timeframes (from M1 to W1) stored inside their respective instrument folders.

### Precious Metals
- **XAUUSD** (Gold / USD)
- **XAGUSD** (Silver / USD)
- **XPTUSD** (Platinum / USD)

### Forex — Majors
- **EURUSD** (EUR / USD)
- **GBPUSD** (GBP / USD)
- **USDJPY** (USD / JPY)
- **USDCHF** (USD / CHF)
- **AUDUSD** (AUD / USD)
- **NZDUSD** (NZD / USD)
- **USDCAD** (USD / CAD)

### Stock Indices
- **NAS100** (Nasdaq 100)
- **SPX500** (S&P 500)
- **US30** (Dow Jones 30)
- **UK100** (FTSE 100)

### Commodities (Energy)
- **UKOIL** (Brent Crude Oil)
- **USOIL** (WTI Crude Oil)

### Cryptocurrency
- **BTCUSD** (Bitcoin / USD)
- **ETHUSD** (Ethereum / USD)
- **SOLUSD** (Solana / USD)
- **XRPUSD** (Ripple / USD)

---

## TradingView Deep Historical Datasets (Multi-Timeframe)

The repository also includes deep historical datasets from TradingView under the `TradingView_Deep_Datasets` folder. Unlike the single-timeframe (H1) MT5 data in the root directory, these datasets provide comprehensive multi-timeframe coverage from **1-minute (M1) up to Monthly**, available in both CSV and JSON formats.

### Supported Instruments & Timeframes

- **Available Timeframes**: 1-minute (`1`), 5-minute (`5`), 15-minute (`15`), 30-minute (`30`), 1-hour (`60`), 4-hour (`240`), Daily (`D`), Weekly (`W`), Monthly (`M`).
- **File Naming Convention**: `TradingView_Deep_Datasets/{SYMBOL}/{SYMBOL}_{TIMEFRAME}.csv` (and `.json`)

#### 1. Stock Indices
| Directory | Index Name | Source | Timeframes |
|---|---|---|---|
| `TVC_SPX` | S&P 500 Index | TVC | 1, 5, 15, 30, 60, 240, D, W, M |
| `TVC_NDX` | Nasdaq 100 Index | TVC | 1, 5, 15, 30, 60, 240, D, W, M |
| `TVC_DJI` | Dow Jones Industrial Average | TVC | 1, 5, 15, 30, 60, 240, D, W, M |
| `TVC_RUT` | Russell 2000 Index | TVC | 1, 5, 15, 30, 60, 240, D, W, M |

#### 2. Cryptocurrency
| Directory | Trading Pair | Source | Timeframes |
|---|---|---|---|
| `BINANCE_BTCUSDT` | Bitcoin / USDT (BTC/USDT) | Binance | 1, 5, 15, 30, 60, 240, D, W, M |
| `BINANCE_ETHUSDT` | Ethereum / USDT (ETH/USDT) | Binance | 1, 5, 15, 30, 60, 240, D, W, M |

#### 3. Precious Metals
| Directory | Symbol | Source | Timeframes |
|---|---|---|---|
| `OANDA_XAUUSD` | Gold / USD | Oanda | 1, 5, 15, 30, 60, 240, D, W, M |

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
