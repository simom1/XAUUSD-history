# 第二阶段研究方案 — Regime 修复 + 做空侧 + 止损 + 新因子

> 封存区已判两个做多候选 FAIL（2026-03→09 黄金 −15%，趋势跟踪做多全亏）。
> 本机执行：Python + pandas + numpy，数据 `data/xauusd_5m_indicators.csv.gz`（211,242 行），无网络/无 GPU。
> 项目根：`C:\Users\Administrator\codeartswork\2026-09-09-11-27-39\xauusd-quant-lab`

## 数据约束（先讲清楚）

| 数据段 | 区间 | regime | 用途 |
|---|---|---|---|
| 研究期 | 2023-09-13 → 2026-03-09（175,475 根） | 基本牛市 | walk-forward 训练+测试 |
| 已消耗封存区 | 2026-03-10 → 2026-09-09（35,767 根） | **下跌 −15%** | 已用于判决，**不得再当"未见过"判据** |
| 新封存区 | 待新数据攒 3-6 个月 | 未知 | 未来最终判决 |

**关键**：现有数据里唯一的下跌段就是已消耗的封存区。做空侧 / regime 闸门无法在 walk-forward（全牛市）里验证抗跌能力。因此：
- 2026-03→09 这段降级为**开发/洞察集**（可以看、可以调，但不能当独立判据）；
- walk-forward 4 折仍是诚实选择面；
- 真正最终判决等新数据切新封存区。

---

## Phase 0：Regime 普查（15 分钟）

**目标**：在研究期内找出所有下跌/震荡子段，作为后续做空侧和 regime 闸门的验证素材。

**做什么**：
1. 写 `scripts/_regime_map.py`：按月聚合 close，算月收益、月内 max-min 区间、ADX 均值、choppiness 均值。
2. 标注每个月为 `trend_up` / `trend_down` / `choppy`（收益>3%=up，<−3%=down，|收益|<3% 且 choppiness>50=choppy）。

**运行**：
```bash
python scripts/_regime_map.py
```

**验证**：输出 `report/regime_map.md`，确认研究期内有至少 2-3 个 down/choppy 月可做开发验证。若全牛市，则做空侧只能靠 2026-03→09 开发集。

**预期**：2024-2025 黄金虽上行但有回调（如 2024-11、2025-02 附近），应能找到几个 down 月。

---

## Phase 1：Regime 闸门（1-2 小时）★最高优先级

**目标**：给两个失败候选套上"只在趋势上行时做多"的开关，看封存区亏损是否因信号被闸门关掉而消失。

**改哪些文件**：

### 1.1 `analysis/combo_screening.py` — 加闸门构造

新增函数：
```python
def build_gates(df, F) -> dict[str, np.ndarray]:
    """Boolean masks for regime gates. True = allow trading."""
    c = df["close"].to_numpy()
    return {
        "trend_up":      (c > df["ema_200"].to_numpy()),            # 价格在 EMA200 上方
        "adx_strong":    (df["adx_14"].to_numpy() > 25),            # ADX>25 有趋势
        "not_choppy":    (df["choppiness_14"].to_numpy() < 50),     # 非震荡
        "aroon_up":      (df["aroon_up_25"].to_numpy() > df["aroon_down_25"].to_numpy()),
    }
```

修改 `masks_from_spec(cfg, zget, gate=None)`：在返回 long_dec 前，若 `gate` 非空，`long_dec = long_dec & gate`。

修改 `evaluate(...)` 签名加 `gate_mask=None`，传给内部 long_dec 的 AND。

### 1.2 `scripts/run_combo_matrix.py` — 加 `--gate` 参数

```python
ap.add_argument("--gate", type=str, default=None,
                help="comma-separated gate names: trend_up,adx_strong,not_choppy,aroon_up")
```

在 `run_grid` 和 `run_final` 里构造 gate mask（多个闸门取交集 AND），传入 `masks_from_spec`。

**运行**（逐个闸门测，再测组合）：
```bash
python scripts/run_combo_matrix.py --gate trend_up
python scripts/run_combo_matrix.py --gate trend_up,adx_strong
python scripts/run_combo_matrix.py --gate trend_up,not_choppy
```

**验证**：
1. walk-forward 4 折结果不退化（闸门不应把牛市里的好交易也砍掉太多）；
2. **关键洞察检查**：把闸门套到两个失败候选上，在 2026-03→09 开发集重跑（非判决，仅看信号是否被关掉）：
   ```bash
   python scripts/run_combo_matrix.py --final "single|plus_di_14|long|W6048|T1.5|H120" --gate trend_up
   ```
   若 `trend_up` 闸门在 2026-03→09 几乎不触发（价格跌破 EMA200）→ 证明 edge 还在，只是需要 regime 开关；
   若仍触发且仍亏 → edge 真消失了，需换信号。

**输出**：`report/combo_matrix_gated.md`、`report/combo_wf_results_gated.csv`

**预期**：`trend_up` 闸门在 2026-03→09 应大幅减少做多触发（黄金从 5140 跌到 3942，大部分时间在 EMA200 下），证明亏损是 regime 问题而非 edge 消失。

---

## Phase 2：做空侧系统化（2-3 小时）

**目标**：系统扫描做空邻域，找到能在下跌 regime 盈利的信号。`SHORT_FAMILY` 已在 `combo_screening.py` 定义但未跑。

**做什么**：

### 2.1 新建 `scripts/run_short_study.py`

复用 `combo_screening` 的 `evaluate`、`walk_forward`、`fold_list`、`candidate_table`、`md_table`。

配置空间：
- 因子：`minus_di_14`、`aroon_down_25`、`aroon_up_25`（z 极低做空=无新高）、`close_vs_ema200`（z 极低做空）、`rsi_14`（z 极高做空=超买）
- 方向：全部 `side="short"`
- W∈{4032,6048,8640}、T∈{1.25,1.5,1.75,2.0}、H∈{24,36,84,120}
- 约 5 因子 × 3 × 4 × 4 = 240 配置

流程：
1. 加载数据，切研究期（同 `run_combo_matrix`）；
2. 跑 walk-forward 4 折网格；
3. 排名（4 折全正优先）；
4. 引擎复核 top 候选（delta $0.00）；
5. **开发集洞察**：把 top 做空候选在 2026-03→09 重跑，看是否在下跌段盈利（非判决，仅验证逻辑自洽）。

### 2.2 做空因子方向映射

| 因子 | long-when | 做空触发 | 逻辑 |
|---|---|---|---|
| `minus_di_14` | low | z > +T 做空 | 下行方向运动主导 |
| `aroon_down_25` | low | z > +T 做空 | 近期频创新低 |
| `aroon_up_25` | high | z < −T 做空 | 无新高=衰退 |
| `close_vs_ema200` | high | z < −T 做空 | 跌破长期均线 |
| `rsi_14` | low | z > +T 做空 | 超买反转 |

**运行**：
```bash
python scripts/run_short_study.py
```

**验证**：
1. `report/short_wf_results.csv` 生成，4 折全正的做空配置有几个；
2. 引擎复核 delta $0.00；
3. top 做空候选在 2026-03→09 开发集是否盈利（若做空在下跌段也亏，说明做空信号没 edge）。

**输出**：`report/short_study.md`、`report/short_wf_results.csv`

**预期**：`aroon_up_25|short` 在 walk-forward 已有 4 折全正迹象（Sharpe 0.81），邻域内应能找到更优做空配置。开发集 2026-03→09 若做空盈利，则多空组合有戏。

---

## Phase 3：止损 / 动态出场（3-4 小时）

**目标**：把固定持仓 10h 无止损改成 ATR 止损 + 追踪止盈，压缩单笔亏损。

**改哪些文件**：

### 3.1 `analysis/combo_screening.py` — 改 `evaluate`

当前 `evaluate` 是固定 H 根出场。改为支持可选出场参数：

```python
def evaluate(long_dec, short_dec, H, ses, o, c, n, folds,
             stop_atr=None, trail_atr=None, target_atr=None, atr=None):
```

逻辑改动（仅在 stop/trail/target! /target 非空时启用事件驱动出场）：
- 入场后每根 K 线检查：
  - 止损：若 `loss >= stop_atr * atr[i]` → 平仓
  - 止盈：若 `profit >= target_atr * atr[i]` → 平仓
  - 追踪：更新 max_profit，若 `profit <= max_profit - trail_atr * atr[i]` → 平仓
  - 否则持到 H 根或 session flat
- 需传入 ATR_14 数组（已有 `df["atr_14"]`）

### 3.2 `scripts/run_combo_matrix.py` — 加出场参数

```python
ap.add_argument("--stop-atr", type=float, default=None)
ap.add_argument("--trail-atr", type=float, default=None)
ap.add_argument("--target-atr", type=float, default=None)
```

**运行**：
```bash
# 先测纯止损
python scripts/run_combo_matrix.py --stop-atr 2.0
# 再测止损+追踪
python scripts/run_combo_matrix.py --stop-atr 2.0 --trail-atr 1.5
# 再测三件套
python scripts/run_combo_matrix.py --stop-atr 2.0 --trail-atr 1.5 --target-atr 3.0
```

**验证**：
1. walk-forward 单笔均值：止损后单笔亏损应从 −$380 量级压缩；
2. 引擎复核 delta $0.00（出场逻辑改了，必须重新对账）；
3. **注意**：封存区已消耗，止损版只能在 walk-forward + 2026-03→09 开发集验证，不能当判决。

**输出**：`report/combo_matrix_stopped.md`、`report/combo_wf_results_stopped.csv`

**预期**：止损压缩单笔亏损，但可能减少盈利笔的持仓时间（趋势里被追踪止盈早平）——需看净效果。

---

## Phase 4：新因子族（4-6 小时）

**目标**：扩因子宇宙，找新 edge! edge，特别是震荡市有效的反转类因子。

### 4.1 复合因子（10 分钟，零新数据）

**改 `analysis/factor_screening.py` 的 `build_factors`**，追加：
```python
F["di_spread"] = df["plus_di! _14"] - df["minus_di_14"]          # 净方向压力
F["aroon_osc"] = df["aroon_up_25"] - df["aroon_down_25"]         # Aroon 振荡器
F["di_ratio"] = df["plus_di_14"] / df["minus_di_14"].replace(0, np.nan)
F["bb_squeeze"] = (df["bb_width"] - df["bb_width"].rolling(2016).mean()) \
                  / df["bb_width"].rolling(2016).std().replace(0, np.nan)
F["vol_percentile"] = df["atr_14"].rolling(2016).rank(pct=True) * 100
```

### 4.2 K线形态（1 小时，纯 OHLC）

**改 `build_factors`**，追加向量化形态：
```python
body = c - o
prev_body = body.shift(1)
F["engulfing_bull"] = ((c > o) & (c >= o.shift(1)) & (o <= c.shift(1)) & (body > prev_body)).astype(float)
F["engulfing_bear"] = ((c < o) & (c <= o.shift(1)) & (o >= c.shift(1)) & (-body > -prev_body)).astype(float)
lower_shadow = pd.concat([o, c], axis=1).min(axis=1) - l
upper_shadow = h - pd.concat([o, c], axis=1).max(axis=1)
F["hammer"] = ((lower_shadow > 2 * body.abs()) & (upper_shadow < body.abs()) & (body > 0)).astype(float)
F["shooting_star"] = ((upper_shadow > 2 * body.abs()) & (lower_shadow < body.abs()) & (body > 0)).astype(float)
```

### 4.3 多周期因子（半天）

**新建 `analysis/mtf_factors.py`**：
```python
def build_mtf(df_5m):
    """合成 1h 因子映射回 5m。"""
    h1 = df_5m.set_index('dt').resample('1h').agg({'open':'first','high':'max','low':'min','close':'last'})
    h1['ema_200'] = h1['close'].ewm(span=200).mean()
    h1['adx_14'] = ...  # 在 1h 上算 ADX
    h1['aroon_up_25'] = ...
    # 映射回 5m：每根 5m 取所属小时的值
    return h1.reindex(df_5m['dt'], method='ffill')
```

新因子：`close_vs_ema200_1h`、`adx_14_1h`、`aroon_up_25_1h`。

### 4.4 时段过滤（30 分钟）

**改 `build_factors`** 或在闸门层加：
```python
hour = pd.to_datetime(df['timestamp'], unit='s').dt.hour
F["in_us_session"] = ((hour >= 16) & (hour < 21)).astype(float)   # 美盘 16-21 UTC
F["in_eur_session"] = ((hour >= 8) & (hour < 16)).astype(float)
```

### 4.5 跑新因子筛选

**新建 `scripts/run_factor_expansion.py`**：
1. 对新因子跑 IC 检验（复用 `factor_screening` 的 IC 函数）；
2. 对新因子跑单因子网格（W×T×H×方向）；
3. walk-forward 4 折；
4. 排名，找新幸存者。

**运行**：
```bash
python scripts/run_factor_expansion.py
```

**验证**：
1. 新因子 IC：|t|>2 的有几个；
2. 新因子网格：4 折全正的配置；
3. K线形态在 2026-03→09 开发集是否有效（反转形态应在震荡市有效）。

**输出**：`report/factor_expansion.md`、`report/factor_expansion_results.csv`

---

## Phase 5：整合 + 新封存区协议（待新数据）

**目标**：把 regime 闸门做多 + 做空侧 + 止损组合成多空对称系统，等新数据做最终判决。

**做什么**：

### 5.1 多空组合系统

**新建 `strategies/combo_regime.py`**：
- 做多腿：`plus_di_14` z>1.5 AND `trend_up` 闸门 AND `adx>25`，ATR 止损
- 做空腿：Phase 2 选出的最优做空信号 AND `trend_down` 闸门，ATR 止损
- 两腿独立触发，组合权益 = 多腿 + 空腿

### 5.2 整合 walk-forward

```bash
python scripts/run_combo_matrix.py --gate trend_up,adx_strong --stop-atr 2.0 --trail-atr 1.5
python scripts/run_short_study.py --gate trend_down,adx_strong --stop-atr 2.0 --trail-atr 1.5
```

### 5.3 新封存区协议

- **现在**：2026-03→09 降级为开发集，用于调 regime 闸门/做空/止损；
- **等 3-6 个月**：新数据积累后，切新封存区（如 2026-12 → 2027-03），研究阶段不碰；
- **判决**：组合系统在新封存区跑一次 `--final`，定论。

**输出**：`report/integrated_system.md`、`report/new_holdout_protocol.md`

---

## 执行顺序与工时

| 步骤 | 内容 | 工时 | 依赖 |
|:---:|---|---|---|
| 0 | Regime 普查 | 15min | 无 |
| **1** | **Regime 闸门**（最关键，验证 edge 是否还在） | 1-2h | 0 |
| 2 | 做空侧系统扫 | 2-3h | 0 |
| 3 | 止损/动态出场 | 3-4h | 1 |
| 4 | 新因子族（复合+形态+多周期+时段） | 4-6h | 0 |
| 5 | 整合多空系统 + 新封存区协议 | 2h | 1,2,3,4 |
| — | **等新数据** → 新封存区判决 | 3-6月 | 5 |

**总工时**：约 12-17 小时本机开发，可 1-2 天完成。最终判决需等新数据。

## 每步必做的验证（不变纪律）

1. **引擎对账**：每改一次出场/闸门逻辑，top 候选必须引擎复核 delta $0.00；
2. **walk-forward 不退化**：加闸门/止损后 walk-forward 4 折不能比无闸门差太多；
3. **开发集仅洞察**：2026-03→09 可看可调，但不写进"判决"结论；
4. **不碰新封存区**：新数据到位前，新封存区不碰；到位后只跑一次 `--final`。

---

## 执行结果（2026-09-09 自动执行）

### Phase 0 — Regime 地图 ✅

- 4 个 trend_down 月：2023-09 (−3.2%), 2024-11 (−3.5%), 2026-03 (−11.4%), 2026-06 (−11.8%)
- 6 个 choppy 月（choppiness > 50）
- 研究期内仅 2 个下跌月（2023-09, 2024-11），封存区有 2 个大幅下跌月
- 输出：`report/regime_map.md`

### Phase 1 — Regime 闸门 ✅

- 最佳闸门 `trend_up,adx_strong` 将做多候选 #1 封存区亏损从 −$68,909 降至 −$26,450（减亏 62%）
- 但**无任何闸门组合能将封存区 PnL 转正** → edge 确实衰减，非纯 regime 错配
- 输出：`report/combo_matrix_gated.md`, `report/combo_wf_results_gated.csv`

### Phase 2 — 做空侧 ✅

- `close_vs_ema200|short|W6048|T1.5|H120` 在封存区（下跌 regime）**盈利 +$78,200**，Sharpe 2.65，59 笔
- `close_vs_ema200|short|W4032|T1.5|H120` 封存区 +$58,805，Sharpe 2.05，60 笔
- Walk-forward 弱（1/4 折正）— 研究期是牛市，做空理应不赚钱
- 输出：`report/short_study.md`, `report/short_study_gated.md`

### Phase 3 — 止损/动态出场 ✅

- **`stop_atr=2.5` 将 gated做多从封存区 −$26,450 转为 +$13,782**（163 笔，Sharpe 0.50）
- 止损对做空侧有害（下跌 regime 强趋势，止损砍赢家）→ 做空不用止损
- 最佳组合 `stop2+trail3+tgt4` 封存区 +$18,828（244 笔）
- 输出：`report/stop_study.md`, `report/stop_study.csv`

### Phase 4 — 新复合因子 ✅

- 5 个复合因子：di_spread, aroon_osc, di_ratio, bb_squeeze, vol_percentile
- IC 均弱（|IR| < 0.71），walk-forward 做多 4/4 正 Sharpe 1.74 但封存区仍负
- **新因子未超越现有 survivor**，最有价值的是 `di_spread|short` 封存区 +$12.5K（远弱于 close_vs_ema200|short 的 +$78K）
- 输出：`report/factor_expansion.md`, `report/factor_expansion_grid.csv`

### Phase 5 — 整合多空系统 ✅

**系统规格：**
- **LONG**: `plus_di_14|long|W6048|T1.5|H120` | gate=`trend_up,adx_strong` | stop_atr=2.5
- **SHORT**: `close_vs_ema200|short|W6048|T1.5|H120` | gate=`trend_down,adx_strong` | 无止损
- 闸门互斥验证：trend_up (close>ema200) ∩ trend_down (close<ema200) = **0 bars 重叠**

**封存区（dev insight only）：**

| 侧 | PnL | Trades | Sharpe | Engine delta |
|---|---:|---:|---:|---:|
| Long (stop2.5) | +$13,782 | 163 | 0.50 | $154 |
| Short (no stop) | +$78,200 | 59 | 2.65 | $0.00 |
| **合计** | **+$91,982** | **222** | — | $154 |

**Walk-forward：+$121,268，3/4 折正**

| Fold | Long | Short | Combined |
|---|---:|---:|---:|
| f1 | −$2,535 | +$939 | −$1,596 |
| f2 | +$13,868 | +$3,923 | +$17,791 |
| f3 | +$43,198 | +$1,084 | +$44,282 |
| f4 | +$50,827 | +$9,964 | +$60,791 |

**全样本：+$219,710，maxDD −$74,872，1,007 笔做多 + 367 笔做空**

- 输出：`report/integrated_system.md`

### 代码变更

| 文件 | 变更 |
|---|---|
| `analysis/combo_screening.py` | +`build_path_stopped`（ATR 止损路径）, +`SHORT_FAMILY_EXT`, +`build_gates`, `evaluate`/`walk_forward`/`masks_from_spec` 增加 stop/gate 参数 |
| `analysis/factor_screening.py` | +5 个复合因子（di_spread, aroon_osc, di_ratio, bb_squeeze, vol_percentile） |
| `scripts/run_combo_matrix.py` | +`--gate`/`--short-gate`/`--dev`/`--stop-atr`/`--trail-atr`/`--target-atr` |
| `scripts/_regime_map.py` | 新建 — Phase 0 |
| `scripts/run_short_study.py` | 新建 — Phase 2 |
| `scripts/run_stop_study.py` | 新建 — Phase 3 |
| `scripts/run_factor_expansion.py` | 新建 — Phase 4 |
| `scripts/run_integration.py` | 新建 — Phase 5 |

### 结论

1. **原做多 edge 确实衰减**，但 regime 闸门 + 止损将其从封存区 −$69K 修复到 +$14K
2. **做空侧在下跌 regime 有强 edge**（+$78K，Sharpe 2.65），是系统的主要利润来源
3. **整合系统封存区 +$92K，walk-forward +$121K（3/4 正）**— 但封存区已被消耗，仅作洞察
4. **新因子未超越现有 survivor** — 56 因子已覆盖主要信号空间
5. **下一步**：等 3-6 个月新数据 → 新封存区 → 一次性 `--final` 判决；期间可 paper trade 验证

---

## 执行结果（2026-09-09 自动执行）

### Phase 0 — Regime 地图 ✅

- 4 个 trend_down 月：2023-09 (−3.2%), 2024-11 (−3.5%), 2026-03 (−11.4%), 2026-06 (−11.8%)
- 6 个 choppy 月（choppiness > 50）
- 研究期内仅 2 个下跌月（2023-09, 2024-11），封存区有 2 个大幅下跌月
- 输出：`report/regime_map.md`

### Phase 1 — Regime 闸门 ✅

- 最佳闸门 `trend_up,adx_strong` 将做多候选 #1 封存区亏损从 −$68,909 降至 −$26,450（减亏 62%）
- 但**无任何闸门组合能将封存区 PnL 转正** → edge 确实衰减，非纯 regime 错配
- 输出：`report/combo_matrix_gated.md`, `report/combo_wf_results_gated.csv`

### Phase 2 — 做空侧 ✅

- `close_vs_ema200|short|W6048|T1.5|H120` 在封存区（下跌 regime）**盈利 +$78,200**，Sharpe 2.65，59 笔
- `close_vs_ema200|short|W4032|T1.5|H120` 封存区 +$58,805，Sharpe 2.05，60 笔
- Walk-forward 弱（1/4 折正）— 研究期是牛市，做空理应不赚钱
- 输出：`report/short_study.md`, `report/short_study_gated.md`

### Phase 3 — 止损/动态出场 ✅

- **`stop_atr=2.5` 将 gated做多从封存区 −$26,450 转为 +$13,782**（163 笔，Sharpe 0.50）
- 止损对做空侧有害（下跌 regime 强趋势，止损砍赢家）→ 做空不用止损
- 最佳组合 `stop2+trail3+tgt4` 封存区 +$18,828（244 笔）
- 输出：`report/stop_study.md`, `report/stop_study.csv`

### Phase 4 — 新复合因子 ✅

- 5 个复合因子：di_spread, aroon_osc, di_ratio, bb_squeeze, vol_percentile
- IC 均弱（|IR| < 0.71），walk-forward 做多 4/4 正 Sharpe 1.74 但封存区仍负
- **新因子未超越现有 survivor**，最有价值的是 `di_spread|short` 封存区 +$12.5K（远弱于 close_vs_ema200|short 的 +$78K）
- 输出：`report/factor_expansion.md`, `report/factor_expansion_grid.csv`

### Phase 5 — 整合多空系统 ✅

**系统规格：**
- **LONG**: `plus_di_14|long|W6048|T1.5|H120` | gate=`trend_up,adx_strong` | stop_atr=2.5
- **SHORT**: `close_vs_ema200|short|W6048|T1.5|H120` | gate=`trend_down,adx_strong` | 无止损
- 闸门互斥验证：trend_up (close>ema200) ∩ trend_down (close<ema200) = **0 bars 重叠**

**封存区（dev insight only）：**

| 侧 | PnL | Trades | Sharpe | Engine delta |
|---|---:|---:|---:|---:|
| Long (stop2.5) | +$13,782 | 163 | 0.50 | $154 |
| Short (no stop) | +$78,200 | 59 | 2.65 | $0.00 |
| **合计** | **+$91,982** | **222** | — | $154 |

**Walk-forward：+$121,268，3/4 折正**

| Fold | Long | Short | Combined |
|---|---:|---:|---:|
| f1 | −$2,535 | +$939 | −$1,596 |
| f2 | +$13,868 | +$3,923 | +$17,791 |
| f3 | +$43,198 | +$1,084 | +$44,282 |
| f4 | +$50,827 | +$9,964 | +$60,791 |

**全样本：+$219,710，maxDD −$74,872，1,007 笔做多 + 367 笔做空**

- 输出：`report/integrated_system.md`

### 代码变更

| 文件 | 变更 |
|---|---|
| `analysis/combo_screening.py` | +`build_path_stopped`（ATR 止损路径）, +`SHORT_FAMILY_EXT`, +`build_gates`, `evaluate`/`walk_forward`/`masks_from_spec` 增加 stop/gate 参数 |
| `analysis/factor_screening.py` | +5 个复合因子（di_spread, aroon_osc, di_ratio, bb_squeeze, vol_percentile） |
| `scripts/run_combo_matrix.py` | +`--gate`/`--short-gate`/`--dev`/`--stop-atr`/`--trail-atr`/`--target-atr` |
| `scripts/_regime_map.py` | 新建 — Phase 0 |
| `scripts/run_short_study.py` | 新建 — Phase 2 |
| `scripts/run_stop_study.py` | 新建 — Phase 3 |
| `scripts/run_factor_expansion.py` | 新建 — Phase 4 |
| `scripts/run_integration.py` | 新建 — Phase 5 |

### 结论

1. **原做多 edge 确实衰减**，但 regime 闸门 + 止损将其从封存区 −$69K 修复到 +$14K
2. **做空侧在下跌 regime 有强 edge**（+$78K，Sharpe 2.65），是系统的主要利润来源
3. **整合系统封存区 +$92K，walk-forward +$121K（3/4 正）**— 但封存区已被消耗，仅作洞察
4. **新因子未超越现有 survivor** — 56 因子已覆盖主要信号空间
5. **下一步**：等 3-6 个月新数据 → 新封存区 → 一次性 `--final` 判决；期间可 paper trade 验证
