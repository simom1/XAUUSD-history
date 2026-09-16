# XAUUSD Tick Data (2024-2026)

## 数据说明

- **数据源**: Exness (XAUUSDm)
- **时间范围**: 2024-01-01 至 2026-09-15
- **总记录数**: 1.9 亿条 tick
- **时区**: UTC

## 数据列

| 列名 | 类型 | 说明 |
|------|------|------|
| timestamp | datetime64[ns] | 时间戳 (UTC) |
| bid | float64 | 买价 |
| ask | float64 | 卖价 |
| bid_vol | float32 | 买量 (可能为空) |
| ask_vol | float32 | 卖量 (可能为空) |
| real_volume | float32 | 真实成交量 (可能为空) |

## 目录结构

```
data/
├── 2024/
│   ├── 01/
│   │   └── xauusd_2024_01.parquet
│   ├── 02/
│   │   └── xauusd_2024_02.parquet
│   └── ...
├── 2025/
│   ├── 01/
│   │   └── xauusd_2025_01.parquet
│   ├── 02/
│   │   └── xauusd_2025_02.parquet
│   ├── 10/
│   │   ├── xauusd_2025_10_early.parquet  (1-10日)
│   │   ├── xauusd_2025_10_mid.parquet    (11-20日)
│   │   └── xauusd_2025_10_late.parquet   (21-31日)
│   └── ...
└── 2026/
    ├── 01/
    │   ├── xauusd_2026_01_early.parquet  (1-10日)
    │   ├── xauusd_2026_01_mid.parquet    (11-20日)
    │   └── xauusd_2026_01_late.parquet   (21-31日)
    ├── 03/
    │   ├── xauusd_2026_03_early.parquet  (1-10日)
    │   ├── xauusd_2026_03_mid.parquet    (11-20日)
    │   └── xauusd_2026_03_late.parquet   (21-31日)
    └── ...
```

**注**: 大文件已按上/中/下旬拆分，单文件 < 100MB，方便上传 GitHub。

## 使用示例

```python
import polars as pl

# 读取 2024 年 1 月数据
df = pl.read_parquet("data/2024/01/xauusd_2024_01.parquet")

# 查看数据
print(df.head())
print(f"行数: {len(df)}")
```

## 数据质量

- [OK] 无空值 (timestamp, bid, ask)
- [OK] 时间升序
- [OK] 无重复 tick
- [WARN] bid_vol/ask_vol/real_volume 有空值 (数据源问题)

## 原始数据

完整年度数据位于 `data/exness_merged/` 目录。

## 许可证

数据仅供学习和研究使用。
