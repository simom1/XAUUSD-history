# XAUUSD History Data

黄金兑美元（XAU/USD）历史数据集：Tick 级报价 + 多周期 OHLC。

## 📊 数据概览

| 数据集 | 内容 | 时间范围 | 文件数 | 大小 |
|--------|------|----------|--------|------|
| Tick 级 | Bid/Ask 逐笔报价 | 2024-01 至 2026-08 | 39 | 1.4 GB |
| OHLC | M5 / M15 / M30 / H1 / H4 / D1 | D1 自 2007-06-22；H1/H4 自 2018-03-19；M5/M15/M30 自 2018-09-14；快照 2026-11-17 | 6 | 21 MB |
| **合计** | | | **45** | **约 1.42 GB** |

## 📁 目录结构

```
XAUUSD-history/
├── 2024/                    # 12 个 Tick 文件 (253.6 MB)
│   └── xauusd_2024_*.parquet
├── 2025/                    # 14 个 Tick 文件 (561.6 MB)
│   └── xauusd_2025_*.parquet
├── 2026/                    # 13 个 Tick 文件 (602.5 MB)
│   └── xauusd_2026_*.parquet
└── XAUUSD_OHLC_M5-D1_2026-11-17/
    ├── M5_2018-09-14_2026-11-17/XAUUSD_M5.parquet
    ├── M15_2018-09-14_2026-11-17/XAUUSD_M15.parquet
    ├── M30_2018-09-14_2026-11-17/XAUUSD_M30.parquet
    ├── H1_2018-03-19_2026-11-17/XAUUSD_H1.parquet
    ├── H4_2018-03-19_2026-11-17/XAUUSD_H4.parquet
    ├── D1_2007-06-22_2026-11-17/XAUUSD_D1.parquet
    ├── manifest.json
    └── README.md
```

OHLC 目录内每个子目录名都包含周期与起止日期，详见该目录下的 README。

## 📈 数据字段

### Tick 数据

| 字段名 | 类型 | 说明 |
|--------|------|------|
| `ts` | datetime64[ms] | 时间戳 (UTC) |
| `bid` | float64 | 买价 |
| `ask` | float64 | 卖价 |
| `bid_vol` | float64 | 买量 |
| `ask_vol` | float64 | 卖量 |

### OHLC 数据

| 字段名 | 类型 | 说明 |
|--------|------|------|
| `time_utc` | datetime64[us, UTC] | bar 开盘时间，真 UTC |
| `time_server` | datetime64[us] | MT5 券商墙上时钟（bar 开盘） |
| `open` / `high` / `low` / `close` | float64 | 报价 |
| `tick_volume` | int64 | MT5 tick 计数 |
| `spread` | int32 | 点差（points） |
| `real_volume` | int64 | 该品种为 0 |

## 🔧 使用示例

### Tick 数据 (Pandas)

```python
import pandas as pd

df = pd.read_parquet('2024/xauusd_2024_01.parquet')
print(df.head())
```

### Tick 数据 (Polars)

```python
import polars as pl

df = pl.read_parquet('2024/xauusd_2024_01.parquet')
```

### OHLC 数据 (Pandas)

```python
import pandas as pd

df = pd.read_parquet("XAUUSD_OHLC_M5-D1_2026-11-17/M5_2018-09-14_2026-11-17/XAUUSD_M5.parquet")
df = df.set_index("time_utc").sort_index()
print(df.close.resample("1D").last().tail())
```

### R

```r
library(arrow)

df <- read_parquet('2024/xauusd_2024_01.parquet')
```

## 📊 数据质量

Tick 数据：

- ✅ 无空值 (No missing values)
- ✅ 时间升序 (Chronological order)
- ✅ 无重复 tick (No duplicate ticks)
- ⚠️ 部分文件 >50MB 但 <100MB (符合 GitHub 文件限制)

OHLC 数据：

- ✅ 重复时间戳 0，OHLC 违规 0，非正价格 0
- ✅ 工作日中位 bar 数：M5 276、M15 92、M30 46、H1 23、H4 6
- ✅ M5 聚合日收盘与 D1 收盘对比 2,110 个交易日，平均绝对差 0.0001
- ⚠️ 券商更早的存档只有每日一根快照，稀疏段落已剔除

## 📅 数据统计

Tick 数据：

| 年份 | 文件数 | 总大小 | 说明 |
|------|--------|--------|------|
| 2024 | 12 | 253.6 MB | 完整数据 |
| 2025 | 14 | 561.6 MB | 7月用 .bi5 补充 |
| 2026 | 13 | 602.5 MB | 5-8月已补充 |
| **总计** | **39** | **1.4 GB** | 1.9 亿条 tick |

OHLC 数据（快照 2026-11-17）：

| 周期 | 行数 | 起止（UTC） | 大小 |
|------|------|-------------|------|
| M5 | 579,531 | 2018-09-13 至 2026-11-17 | 12 MB |
| M15 | 193,184 | 2018-09-13 至 2026-11-17 | 4.6 MB |
| M30 | 96,609 | 2018-09-13 至 2026-11-17 | 2.6 MB |
| H1 | 51,260 | 2018-03-18 至 2026-11-17 | 1.5 MB |
| H4 | 13,406 | 2018-03-18 至 2026-11-17 | 426 KB |
| D1 | 5,127 | 2007-06-21 至 2026-11-16 | 167 KB |

## 📜 许可

MIT License

## 🔗 相关资源

- Tick 数据源: Dukascopy Historical Data
- OHLC 数据源: Infinox MT5（服务器 InfinoxLimited-MT5Live）
- 处理工具: Python, Pandas, Polars
- 存储格式: Apache Parquet
