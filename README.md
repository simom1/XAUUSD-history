# XAUUSD 历史行情数据集

> 🌐 语言切换：**中文** | [English](./README_EN.md)

---

## 简介

本仓库收录了 **20 个主要金融品种** 的多周期（M1 到 W1）历史 OHLCV 行情数据，数据来源于 MetaTrader 5，部分数据最早可追溯至 2007 年，每日自动更新，目前合计超过 **400 万行**。

---

## 文件结构

文件以品种进行分类，每个品种对应一个文件夹，包含 8 个不同的时间周期：
- 文件夹命名：`{品种代码}/`
- 文件命名规则：`{品种代码}/{品种代码}_{时间周期}.csv`

### 支持的时间周期

| 代码 | 时间级别 | 说明 |
|---|---|---|
| `M1` | 1 分钟 | 1-minute bar |
| `M5` | 5 分钟 | 5-minute bar |
| `M15` | 15 分钟 | 15-minute bar |
| `M30` | 30 分钟 | 30-minute bar |
| `H1` | 1 小时 | 1-hour bar |
| `H4` | 4 小时 | 4-hour bar |
| `D1` | 日线 | Daily bar |
| `W1` | 周线 | Weekly bar |

### 数据列说明

| 列名 | 类型 | 说明 |
|---|---|---|
| `time` | datetime | K线开盘时间（UTC） |
| `open` | float | 开盘价 |
| `high` | float | 最高价 |
| `low` | float | 最低价 |
| `close` | float | 收盘价 |
| `tick_volume` | int | Tick 成交量（成交量代理指标） |

### 示例数据

```
time,open,high,low,close,tick_volume
2007-06-22 03:00:00,651.3,656.3,650.6,653.9,881
```

---

## 品种列表

所有的 MT5 历史行情数据按品种分类保存在子目录下。每个子目录均包含 8 个周期的 CSV 文件，文件路径为 `{品种代码}/{品种代码}_{时间周期}.csv`。

| 贵金属 (Precious Metals) | 股指 (Stock Indices - 新增) | 加密货币 (Cryptocurrency - 新增) | 能源/商品 (Energy/Commodities) | 外汇主要货币对 (Forex Majors) |
| :--- | :--- | :--- | :--- | :--- |
| • [XAUUSD](file:///Users/Zhuanz/Downloads/XAUUSD-history/XAUUSD) (黄金)<br>• [XAGUSD](file:///Users/Zhuanz/Downloads/XAUUSD-history/XAGUSD) (白银)<br>• [XPTUSD](file:///Users/Zhuanz/Downloads/XAUUSD-history/XPTUSD) (铂金) | • [NAS100](file:///Users/Zhuanz/Downloads/XAUUSD-history/NAS100) (纳指100)<br>• [SPX500](file:///Users/Zhuanz/Downloads/XAUUSD-history/SPX500) (标普500)<br>• [US30](file:///Users/Zhuanz/Downloads/XAUUSD-history/US30) (道琼斯30)<br>• [UK100](file:///Users/Zhuanz/Downloads/XAUUSD-history/UK100) (富时100) | • [BTCUSD](file:///Users/Zhuanz/Downloads/XAUUSD-history/BTCUSD) (比特币)<br>• [ETHUSD](file:///Users/Zhuanz/Downloads/XAUUSD-history/ETHUSD) (以太坊)<br>• [SOLUSD](file:///Users/Zhuanz/Downloads/XAUUSD-history/SOLUSD) (索拉纳)<br>• [XRPUSD](file:///Users/Zhuanz/Downloads/XAUUSD-history/XRPUSD) (瑞波币) | • [UKOIL](file:///Users/Zhuanz/Downloads/XAUUSD-history/UKOIL) (布伦特原油)<br>• [USOIL](file:///Users/Zhuanz/Downloads/XAUUSD-history/USOIL) (WTI原油) | • [EURUSD](file:///Users/Zhuanz/Downloads/XAUUSD-history/EURUSD) (欧元/美元)<br>• [GBPUSD](file:///Users/Zhuanz/Downloads/XAUUSD-history/GBPUSD) (英镑/美元)<br>• [USDJPY](file:///Users/Zhuanz/Downloads/XAUUSD-history/USDJPY) (美元/日元)<br>• [USDCHF](file:///Users/Zhuanz/Downloads/XAUUSD-history/USDCHF) (美元/瑞郎)<br>• [AUDUSD](file:///Users/Zhuanz/Downloads/XAUUSD-history/AUDUSD) (澳元/美元)<br>• [NZDUSD](file:///Users/Zhuanz/Downloads/XAUUSD-history/NZDUSD) (纽元/美元)<br>• [USDCAD](file:///Users/Zhuanz/Downloads/XAUUSD-history/USDCAD) (美元/加元) |

---

## 快速开始（Python）

```python
import pandas as pd

# 读取黄金 H1 数据
df = pd.read_csv("XAUUSD/XAUUSD_H1.csv", parse_dates=["time"], index_col="time")

print(df.head())
print(f"总行数：{len(df)}")
print(f"时间范围：{df.index.min()} → {df.index.max()}")
```

---

## 注意事项

- 数据由 **MetaTrader 5** Python 接口导出
- 包含从 **M1 到 W1** 8 个不同的时间周期，每行代表该周期的开盘行情
- `tick_volume` 为 Tick 计数，非真实成交量，是外汇市场常用的成交量代理指标
- 部分品种行数较少，受限于券商历史数据深度
- 所有时间戳均为 **UTC**

---

## 相关项目

本数据集是 **SINERGY ML BOT** 项目的基础数据，该项目是一个基于机器学习的多品种量化交易系统，使用 H1 多品种数据进行信号生成与回测。

---

## TradingView 深度历史数据集 (多周期)

本仓库在 [TradingView_Deep_Datasets](file:///Users/Zhuanz/Downloads/XAUUSD-history/TradingView_Deep_Datasets) 目录下还收录了来自 TradingView 的深层历史数据集。与根目录下的单周期（H1）数据不同，这些数据集包含了从 **1分钟（M1）到月线（Monthly）** 的完整多周期数据，包括 CSV 和 JSON 格式。

### 支持品种及周期

- **数据周期**：1分钟 (`1`)、5分钟 (`5`)、15分钟 (`15`)、30分钟 (`30`)、1小时 (`60`)、4小时 (`240`)、日线 (`D`)、周线 (`W`)、月线 (`M`)。
- **文件命名规则**：`TradingView_Deep_Datasets/{代码}/{代码}_{周期}.csv` (和 `.json`)

#### 1. 股指 (Stock Indices)
| 目录 | 指数名称 | 来源 | 包含周期 |
|---|---|---|---|
| `TVC_SPX` | 标普 500 指数 (S&P 500) | TVC | 1, 5, 15, 30, 60, 240, D, W, M |
| `TVC_NDX` | 纳斯达克 100 指数 (Nasdaq 100) | TVC | 1, 5, 15, 30, 60, 240, D, W, M |
| `TVC_DJI` | 道琼斯工业指数 (Dow Jones) | TVC | 1, 5, 15, 30, 60, 240, D, W, M |
| `TVC_RUT` | 罗素 2000 指数 (Russell 2000) | TVC | 1, 5, 15, 30, 60, 240, D, W, M |

#### 2. 加密货币 (Cryptocurrency)
| 目录 | 交易对 | 来源 | 包含周期 |
|---|---|---|---|
| `BINANCE_BTCUSDT` | 比特币 / 泰达币 (BTC/USDT) | Binance | 1, 5, 15, 30, 60, 240, D, W, M |
| `BINANCE_ETHUSDT` | 以太坊 / 泰达币 (ETH/USDT) | Binance | 1, 5, 15, 30, 60, 240, D, W, M |

#### 3. 贵金属 (Precious Metals)
| 目录 | 品种 | 来源 | 包含周期 |
|---|---|---|---|
| `OANDA_XAUUSD` | 黄金 / 美元 (Gold / USD) | Oanda | 1, 5, 15, 30, 60, 240, D, W, M |
