# XAUUSD History Data

黄金兑美元（XAU/USD）Tick级历史数据集

## 📊 数据概览

| 项目 | 内容 |
|------|------|
| 交易品种 | XAU/USD (Gold vs US Dollar) |
| 数据类型 | Tick级数据 (Bid/Ask) |
| 时间范围 | 2024年1月 - 2026年8月 |
| 总文件数 | 39 个 Parquet 文件 |
| 总数据量 | 1.9 亿条 Tick |
| 总大小 | 1.4 GB |
| 数据格式 | Parquet (列式存储) |

## 📁 目录结构

```
XAUUSD-history/
├── 2024/                    # 12 个文件 (253.6 MB)
│   ├── xauusd_2024_01.parquet
│   ├── xauusd_2024_02.parquet
│   ├── xauusd_2024_03.parquet
│   ├── xauusd_2024_04.parquet
│   ├── xauusd_2024_05.parquet
│   ├── xauusd_2024_06.parquet
│   ├── xauusd_2024_07.parquet
│   ├── xauusd_2024_08.parquet
│   ├── xauusd_2024_09.parquet
│   ├── xauusd_2024_10.parquet
│   ├── xauusd_2024_11.parquet
│   └── xauusd_2024_12.parquet
├── 2025/                    # 14 个文件 (561.6 MB)
│   ├── xauusd_2025_01.parquet
│   ├── xauusd_2025_02.parquet
│   ├── xauusd_2025_03.parquet
│   ├── xauusd_2025_04.parquet
│   ├── xauusd_2025_05.parquet
│   ├── xauusd_2025_06.parquet
│   ├── xauusd_2025_07.parquet
│   ├── xauusd_2025_08.parquet
│   ├── xauusd_2025_09.parquet
│   ├── xauusd_2025_10.parquet
│   ├── xauusd_2025_11.parquet
│   ├── xauusd_2025_12.parquet
│   ├── xauusd_2025_07a.parquet  # 补充数据
│   └── xauusd_2025_07b.parquet  # 补充数据
└── 2026/                    # 13 个文件 (602.5 MB)
    ├── xauusd_2026_01.parquet
    ├── xauusd_2026_02.parquet
    ├── xauusd_2026_03.parquet
    ├── xauusd_2026_04.parquet
    ├── xauusd_2026_05.parquet
    ├── xauusd_2026_06.parquet
    ├── xauusd_2026_07.parquet
    ├── xauusd_2026_08.parquet
    ├── xauusd_2026_05a.parquet  # 补充数据
    ├── xauusd_2026_05b.parquet  # 补充数据
    ├── xauusd_2026_06a.parquet  # 补充数据
    ├── xauusd_2026_06b.parquet  # 补充数据
    └── xauusd_2026_06c.parquet  # 补充数据
```

## 📈 数据字段

| 字段名 | 类型 | 说明 |
|--------|------|------|
| `ts` | datetime64[ms] | 时间戳 (UTC) |
| `bid` | float64 | 买价 |
| `ask` | float64 | 卖价 |
| `bid_vol` | float64 | 买量 |
| `ask_vol` | float64 | 卖量 |

## 🔧 使用示例

### Python (Pandas)

```python
import pandas as pd

# 读取单个文件
df = pd.read_parquet('2024/xauusd_2024_01.parquet')

# 读取所有文件
import glob
files = glob.glob('**/*.parquet', recursive=True)
df = pd.concat([pd.read_parquet(f) for f in files])

# 查看数据
print(df.head())
print(f"总行数: {len(df)}")
```

### Python (Polars - 更快)

```python
import polars as pl

# 读取单个文件
df = pl.read_parquet('2024/xauusd_2024_01.parquet')

# 批量读取
df = pl.read_parquet('**/*.parquet')
```

### R

```r
library(arrow)

# 读取单个文件
df <- read_parquet('2024/xauusd_2024_01.parquet')

# 读取所有文件
files <- list.files(pattern = '\\.parquet$', recursive = TRUE)
df <- do.call(rbind, lapply(files, read_parquet))
```

## 📊 数据质量

- ✅ 无空值 (No missing values)
- ✅ 时间升序 (Chronological order)
- ✅ 无重复 tick (No duplicate ticks)
- ⚠️ 部分文件 >50MB 但 <100MB (符合 GitHub 文件限制)

## 📅 数据统计

| 年份 | 文件数 | 总大小 | 说明 |
|------|--------|--------|------|
| 2024 | 12 | 253.6 MB | 完整数据 |
| 2025 | 14 | 561.6 MB | 7月用 .bi5 补充 |
| 2026 | 13 | 602.5 MB | 5-8月已补充 |
| **总计** | **39** | **1.4 GB** | 1.9 亿条 tick |

## 📜 许可

MIT License

## 🔗 相关资源

- 数据源: Dukascopy Historical Data
- 处理工具: Python, Pandas, Polars
- 存储格式: Apache Parquet
