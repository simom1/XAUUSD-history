# 📈 多资产全周期金融历史行情数据集 (Multi-Asset Financial Market History)

> 🌐 **项目仓库**: [simom1/XAUUSD-history](https://github.com/simom1/XAUUSD-history)  
> ⏰ **更新机制**: 每日自动增量更新 (MT5 自动化采集 + Git 自动同步推送)

---

## 📖 项目简介

本项目是一个高频、多周期、多资产的金融历史行情（OHLCV）数据中心与自动化量化基础设施。

数据直接对接 **MetaTrader 5 (MT5)** 机构级流动性行情源，并整合了 **TradingView Deep Datasets** 深度历史切片。涵盖 **贵金属、原油能源、全球主要股指、外汇主要/主流交叉盘、主流加密货币** 等 33+ 个核心金融资产，数据周期覆盖 **1分钟 (M1) 到 周线 (W1)**，部分数据最早可追溯至 2007 年，目前全库累计包含数千万行高精度历史数据。

---

## 🗂 仓库整体项目结构

整个仓库按**资产大类（Asset Group）→ 品种代码（Symbol）→ 周期数据文件（Timeframe CSV）**划分：

```text
XAUUSD-history/
├── Gold-Cash/                       # 现货黄金
│   └── XAUUSD/                      # XAUUSD (M1, M5, M15, M30, H1, H4, D1, W1)
├── Silver-Cash/                     # 现货白银
│   └── XAGUSD/                      # XAGUSD (M1, M5, M15, M30, H1, H4, D1, W1)
├── Oil-Cash/                        # 现货原油能源
│   ├── USOIL/                       # 美原油 WTI (券商映射 XTIUSD)
│   └── UKOIL/                       # 布伦特原油 Brent (券商映射 XBRUSD)
├── Index-Cash/                      # 全球主流股指现货
│   ├── NAS100/                      # 纳斯达克 100 指数
│   ├── SPX500/                      # 标普 500 指数
│   ├── US30/                        # 道琼斯工业指数
│   └── UK100/                       # 英国富时 100 指数
├── Forex-Majors/                    # 外汇核心直盘对
│   ├── EURUSD/                      # 欧元 / 美元
│   ├── GBPUSD/                      # 英镑 / 美元
│   ├── USDJPY/                      # 美元 / 日元
│   ├── AUDUSD/                      # 澳元 / 美元
│   └── NZDUSD/                      # 纽元 / 美元
├── Forex-Main/                      # 外汇主流交叉盘与主盘
│   ├── USDCHF/                      # 美元 / 瑞郎
│   ├── USDCAD/                      # 美元 / 加元
│   ├── AUDCAD/, AUDCHF/, AUDJPY/, AUDNZD/
│   ├── CADCHF/, CADJPY/, CHFJPY/
│   └── EURAUD/, EURCAD/, EURCHF/
├── Crypto/                          # 主流加密货币
│   ├── BTCUSD/                      # 比特币 / 美元
│   ├── ETHUSD/                      # 以太坊 / 美元
│   ├── SOLUSD/                      # 索拉纳 / 美元
│   └── XRPUSD/                      # 瑞波币 / 美元
├── Commodities/                     # 大宗商品 / 贵金属延伸
│   ├── XPTUSD/                      # 现货铂金
│   └── XPDUSD/                      # 现货钯金
├── Energy-Future/                   # 能源期货合约
│   └── CL-OIL/                      # 原油期货合约 CFD
├── TradingView_Deep_Datasets/       # TradingView 深度历史多周期切片数据集
│   ├── TVC_SPX/                     # 标普500 (1m~1M)
│   ├── TVC_NDX/                     # 纳指100 (1m~1M)
│   ├── TVC_DJI/                     # 道指 (1m~1M)
│   ├── TVC_RUT/                     # 罗素2000 (1m~1M)
│   ├── BINANCE_BTCUSDT/             # 币安 BTC/USDT
│   ├── BINANCE_ETHUSDT/             # 币安 ETH/USDT
│   └── OANDA_XAUUSD/                # OANDA 黄金
└── metatrader_tools/ (核心运维脚本)
    ├── fetch_mt5_data.py            # MT5 增量数据抓取核心脚本
    ├── scheduler.py                 # 定时调度后台服务 (每日更新 + 飞书卡片)
    ├── push_data.bat                # 自动化拉取、暂存与 Git 提交推送脚本
    └── send_feishu_mt5_report.py    # 飞书量化交易晨报推送工具
```

---

## 📊 数据规格与字段说明

### 1. 时间周期划分 (Timeframes)

每个品种目录下均包含 8 个标准时间周期的 CSV 文件，文件命名规范为 `{品种}_{周期}.csv`：

| 周期代码 | 时间级别 | 对应 MT5 常量 | 说明 |
|:---|:---|:---|:---|
| `M1` | 1 分钟 | `mt5.TIMEFRAME_M1` | 1-minute Bar |
| `M5` | 5 分钟 | `mt5.TIMEFRAME_M5` | 5-minute Bar |
| `M15` | 15 分钟 | `mt5.TIMEFRAME_M15` | 15-minute Bar |
| `M30` | 30 分钟 | `mt5.TIMEFRAME_M30` | 30-minute Bar |
| `H1` | 1 小时 | `mt5.TIMEFRAME_H1` | 1-hour Bar |
| `H4` | 4 小时 | `mt5.TIMEFRAME_H4` | 4-hour Bar |
| `D1` | 日线 | `mt5.TIMEFRAME_D1` | Daily Bar |
| `W1` | 周线 | `mt5.TIMEFRAME_W1` | Weekly Bar |

### 2. CSV 数据列格式

| 列名 | 数据类型 | 描述 |
|:---|:---|:---|
| `time` | `datetime` (UTC) | K 线开盘时间（如 `2026-08-18 08:00:00`） |
| `open` | `float` | 开盘价 |
| `high` | `float` | 最高价 |
| `low` | `float` | 最低价 |
| `close` | `float` | 收盘价 |
| `tick_volume` | `int` | Tick 跳动次数（成交量代理指标） |

#### 数据样例
```csv
time,open,high,low,close,tick_volume
2026-08-18 00:00:00,2498.35,2504.12,2495.60,2502.80,18420
2026-08-18 01:00:00,2502.80,2508.90,2501.10,2507.45,14230
```

---

## ⚡ 数据更新与自动化运维机制

### 1. 增量更新与防重原理
为了高效同步且避免全量覆盖损坏历史数据，数据采集脚本采用**三层无损增量机制**：
1. **末尾时间嗅探**：通过快速文件定位（`f.seek`）读取本地对应 CSV 最底部的最新一条时间戳 `last_time`。
2. **MT5 范围精准拉取**：调用 `mt5.copy_rates_range(symbol, tf, last_time, now)` 仅拉取新产生的 K 线，并在内存中通过 `df[df.index > last_time]` 严格去除重叠。
3. **追加写入 (Append Mode)**：以 `mode="a", header=False` 模式将新增记录追加到文件尾部。

### 2. 品种别名（Alias）自动映射
不同外汇与差价合约券商对品种命名存在差异，采集器内置智能别名探测机制：
* **美原油 (USOIL)**：自动探测并适配 `["USOIL", "WTIUSD", "USOUSD", "XTIUSD", "CL"]`（当前券商匹配 `XTIUSD`，归档入 `Oil-Cash/USOIL/`）。
* **布伦特原油 (UKOIL)**：自动探测并适配 `["UKOIL", "BRENTUSD", "UKOUSD", "XBRUSD"]`（当前券商匹配 `XBRUSD`，归档入 `Oil-Cash/UKOIL/`）。
* **加密货币**：自动探测各券商标缀（如 `BTCUSD` / `BTCUSD.crp`）。

### 3. 定时调度任务 (Scheduler)
运行在后台的 `scheduler.py` 守护进程负责以下自动任务：
* **每日 08:00**：自动执行 `push_data.bat`，完成全品种 264 个任务的行情采集、Git 暂存、自动生成当期 Commit 并 Push 同步至 GitHub。
* **周一至周六 06:30**：自动生成 MT5 账户资金、持仓风控与行情汇总卡片，推送至飞书机器人。

---

## 🚀 快速开始 (Python / Pandas)

```python
import pandas as pd

# 读取黄金 (XAUUSD) 1小时 (H1) 历史数据
file_path = "Gold-Cash/XAUUSD/XAUUSD_H1.csv"
df = pd.read_csv(file_path, parse_dates=["time"], index_col="time")

print(df.tail(10))
print(f"总记录数: {len(df):,} 行")
print(f"时间跨度: {df.index.min()} 至 {df.index.max()}")

# 计算 20 周期均线
df["SMA_20"] = df["close"].rolling(window=20).mean()
```

---

## 📌 注意事项与说明

1. **时区标准**：所有导出的时间戳均统一为 **UTC 协调世界时**。
2. **成交量说明**：外汇与 CFD 市场的 `tick_volume` 为价格变动跳动量，是评估市场活跃度的核心指标。
3. **期货合约说明**：`Energy-Future/CL-OIL` 属于特定月份期货合约 CFD，当券商未在市场报价中挂载该合约时将自动跳过，现货原油请以 `Oil-Cash/USOIL` 及 `Oil-Cash/UKOIL` 为准。

---

## 📄 开源与授权

本数据集专为量化研究、机器学习策略回测与历史分析使用。
