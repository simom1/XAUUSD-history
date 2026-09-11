"""Pre-locked dev segment evaluation for the rank-aggregation scalping config.

The config is frozen (selected on the research period, never re-selected on
dev).  The dev segment (last 183 days, excluded from all selection) is the
"consumed development" period used only for out-of-sample evaluation.

Steps:
  1. Freeze: select the best aggregation config on the research period.
  2. Dev evaluation: evaluate the frozen config on the dev segment.
  3. Diagnostics:
     - Research vs dev performance comparison.
     - Dev monthly breakdown.
     - Factor family IC stability on dev (are the factors still reversal?).
     - Regime/session distribution shift (research vs dev).
     - Dev trade list (first/last 10 trades).

Preregistered verdict: the config is ACCEPTED for live deployment if
dev Sharpe > 0 AND dev maxDD > -15% AND dev trades >= 50.
"""
from __future__ import annotations

import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
import pandas as pd

from analysis.combo_screening import build_gates, holdout_split
from analysis.factor_screening import build_factors, ic_stats
from analysis.scalping_research import (
    AggregationConfig, build_grid, run_aggregation_engine,
    select_aggregation_on_train, select_reversal_factors,
)
from analysis.system_research import bar_metrics

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "xauusd_5m_indicators.csv.gz"
REPORT = ROOT / "report" / "scalping_prelocked_dev.md"

ANN_5M = float(np.sqrt(288 * 252))
FAST_WINDOW = 48
HORIZON = 12
MAX_N_FACTORS = 15
TOP_K_ENGINE = 20

# Grid (must match run_scalping_rank_aggregation.py)
METHODS = ("vote", "rank_avg", "z_composite")
N_FACTORS = (5, 7, 10)
WINDOWS = (288, 576)
THRESHOLDS = (1.5, 2.0)
VOTE_MINS = (2, 3, 4)
HOLDS = (6, 12, 24)
REGIMES = ("none", "trend", "trend_adx", "trend_not_choppy")
SESSIONS = ("all", "london", "new_york", "overlap")
EXITS = ("none", "stop1_5", "trail2")

# Acceptance gates
DEV_MIN_SHARPE = 0.0
DEV_MIN_MAXDD = -15.0       # percent of initial capital
DEV_MIN_TRADES = 50


def md_table(frame: pd.DataFrame, floatfmt: str = "{:.3f}") -> str:
    if frame is None or frame.empty:
        return "(none)"
    cols = list(frame.columns)
    lines = ["| " + " | ".join(str(c) for c in cols) + " |",
             "|" + "|".join("---:" for _ in cols) + "|"]
    for _, row in frame.iterrows():
        cells = []
        for col in cols:
            v = row[col]
            if isinstance(v, float):
                cells.append(floatfmt.format(v) if pd.notna(v) else "-")
            else:
                cells.append(str(v))
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


def trade_stats(t: pd.DataFrame) -> dict:
    if t is None or t.empty:
        return {"trades": 0, "wr": 0.0, "pf": 0.0, "avg_hold": 0.0,
                "best": 0.0, "worst": 0.0}
    wins = float(t.loc[t.net_pnl > 0, "net_pnl"].sum())
    losses = float(-t.loc[t.net_pnl < 0, "net_pnl"].sum())
    return {"trades": int(len(t)),
            "wr": round(float((t.net_pnl > 0).mean() * 100), 1),
            "pf": round(wins / losses, 3) if losses > 0 else float("inf"),
            "avg_hold": round(float(t.bars_held.mean()), 1),
            "best": round(float(t.net_pnl.max()), 2),
            "worst": round(float(t.net_pnl.min()), 2)}


def select_best_config(research: pd.DataFrame, n: int) -> dict:
    """Select the best aggregation config on the research period."""
    grid = build_grid(METHODS, N_FACTORS, WINDOWS, THRESHOLDS, VOTE_MINS,
                      HOLDS, REGIMES, SESSIONS, EXITS)
    return select_aggregation_on_train(research, grid, max_n_factors=MAX_N_FACTORS,
                                       horizon=HORIZON, fast_window=FAST_WINDOW,
                                       bar_seconds=300, ann=ANN_5M,
                                       min_trades=20, top_k_engine=TOP_K_ENGINE)


# ======================================================================
# Step 1: Freeze config on research
# ======================================================================
def step1_freeze(lines: list, research: pd.DataFrame, n: int) -> dict:
    lines += ["## Step 1 -- freeze config on research period\n"]

    sel = select_best_config(research, n)
    if sel is None:
        lines += ["**Selection failed.**\n"]
        return {"ok": False}

    cfg = sel["config"]
    family = sel["all_reversal_factors"]
    factor_names = sel["factor_names"]

    factors = build_factors(research, fast_window=FAST_WINDOW)
    gates = build_gates(research)
    result, _, m, _ = run_aggregation_engine(research, factors, factor_names, cfg,
                                              gates, bar_seconds=300, ann=ANN_5M)
    ts = trade_stats(result.trades)

    lines += [f"- config: `{cfg.key}`",
              f"- method: `{cfg.method}`, N={cfg.n_factors}, window={cfg.window}, "
              f"threshold={cfg.threshold:g}, vote_min={cfg.vote_min}, hold={cfg.hold}",
              f"- regime: `{cfg.regime}`, session: `{cfg.session}`, exit: `{cfg.exit_name}`",
              f"- factor family (top-{MAX_N_FACTORS}): `{', '.join(family)}`",
              f"- active factors (top-{cfg.n_factors}): `{', '.join(factor_names)}`",
              f"- research Sharpe: {m['sharpe']:+.3f}",
              f"- research PnL: ${m['pnl']:+,.2f}",
              f"- research maxDD: ${m['maxdd']:,.2f}",
              f"- research trades: {ts['trades']}, WR {ts['wr']}%, PF {ts['pf']}",
              f"- research avg hold: {ts['avg_hold']} bars\n"]

    return {"ok": True, "cfg": cfg, "family": family,
            "factor_names": factor_names, "research_metrics": m,
            "research_trades": ts, "research_result": result}


# ======================================================================
# Step 2: Dev evaluation (frozen config)
# ======================================================================
def step2_dev_eval(lines: list, dev: pd.DataFrame,
                   cfg: AggregationConfig, factor_names: list[str]) -> dict:
    lines += ["## Step 2 -- dev evaluation (frozen config)\n",
              f"- dev period: {dev.datetime_utc.iloc[0]} -> {dev.datetime_utc.iloc[-1]} "
              f"({len(dev)} bars)",
              "- config is frozen from Step 1; no re-selection on dev.\n"]

    factors = build_factors(dev, fast_window=FAST_WINDOW)
    gates = build_gates(dev)
    result, _, m, _ = run_aggregation_engine(dev, factors, factor_names, cfg,
                                              gates, bar_seconds=300, ann=ANN_5M)
    ts = trade_stats(result.trades)

    lines += [f"- dev Sharpe: {m['sharpe']:+.3f}",
              f"- dev PnL: ${m['pnl']:+,.2f}",
              f"- dev maxDD: ${m['maxdd']:,.2f}",
              f"- dev trades: {ts['trades']}, WR {ts['wr']}%, PF {ts['pf']}",
              f"- dev avg hold: {ts['avg_hold']} bars",
              f"- dev best trade: ${ts['best']:+,.2f}",
              f"- dev worst trade: ${ts['worst']:+,.2f}\n"]

    return {"metrics": m, "trades": ts, "result": result,
            "dev_factors": factors, "dev_gates": gates}


# ======================================================================
# Step 3: Diagnostics
# ======================================================================
def step3_diagnostics(lines: list, research: pd.DataFrame, dev: pd.DataFrame,
                      cfg: AggregationConfig, factor_names: list[str],
                      family: list[str], step1: dict, step2: dict) -> None:
    lines += ["## Step 3 -- diagnostics\n"]

    # 3a: Research vs dev comparison
    lines += ["### 3a -- research vs dev comparison\n"]
    rm = step1["research_metrics"]
    rt = step1["research_trades"]
    dm = step2["metrics"]
    dt = step2["trades"]
    comp_df = pd.DataFrame([
        {"period": "research", "bars": len(research),
         "sharpe": round(rm["sharpe"], 3), "pnl": round(rm["pnl"], 2),
         "maxdd": round(rm["maxdd"], 2), "trades": rt["trades"],
         "wr": rt["wr"], "pf": rt["pf"], "avg_hold": rt["avg_hold"]},
        {"period": "dev", "bars": len(dev),
         "sharpe": round(dm["sharpe"], 3), "pnl": round(dm["pnl"], 2),
         "maxdd": round(dm["maxdd"], 2), "trades": dt["trades"],
         "wr": dt["wr"], "pf": dt["pf"], "avg_hold": dt["avg_hold"]},
    ])
    lines += [md_table(comp_df), "\n"]

    sharpe_decay = 0.0
    if rm["sharpe"] != 0:
        sharpe_decay = float((dm["sharpe"] - rm["sharpe"]) / abs(rm["sharpe"]) * 100)
    lines += [f"- Sharpe decay: {sharpe_decay:+.1f}% (dev vs research)",
              f"- PnL per bar: research ${rm['pnl']/len(research):+.4f}, "
              f"dev ${dm['pnl']/len(dev):+.4f}",
              f"- Trade frequency: research {rt['trades']/len(research)*1000:.2f}/kbar, "
              f"dev {dt['trades']/len(dev)*1000:.2f}/kbar\n"]

    # 3b: Dev monthly breakdown
    lines += ["### 3b -- dev monthly breakdown\n"]
    dev_result = step2["result"]
    if not dev_result.trades.empty:
        trades = dev_result.trades.copy()
        # entry time from bar index
        dt_arr = pd.to_datetime(dev["datetime_utc"])
        trades["entry_date"] = trades["entry_i"].apply(lambda i: dt_arr.iloc[i])
        trades["month"] = trades["entry_date"].dt.to_period("M").astype(str)
        monthly = trades.groupby("month").agg(
            n=("net_pnl", "count"),
            pnl=("net_pnl", "sum"),
            wins=("net_pnl", lambda x: (x > 0).sum()),
        ).reset_index()
        monthly["wr"] = (monthly["wins"] / monthly["n"] * 100).round(1)
        monthly["pnl"] = monthly["pnl"].round(2)
        lines += [md_table(monthly[["month", "n", "pnl", "wr"]]), "\n"]
    else:
        lines += ["No trades in dev.\n"]

    # 3c: Factor family IC stability on dev
    lines += ["### 3c -- factor family IC on dev (reversal stability)\n"]
    dev_factors = step2["dev_factors"]
    dev_close = dev["close"].to_numpy(float)
    dev_ts = pd.to_datetime(dev["datetime_utc"])
    dev_ic = ic_stats(dev_factors, dev_close, dev_ts, len(dev), horizons=(HORIZON,))
    dev_ic12 = dev_ic[dev_ic.h == HORIZON].copy()
    dev_ic12 = dev_ic12.set_index("factor")

    ic_rows = []
    for fn in factor_names:
        if fn in dev_ic12.index:
            r = dev_ic12.loc[fn]
            ic_rows.append({
                "factor": fn,
                "research_ic": "(selected)",
                "dev_ic": round(float(r["ic_mean"]), 4),
                "dev_icir": round(float(r["icir"]), 3),
                "still_reversal": "yes" if r["ic_mean"] < 0 else "NO",
            })
    ic_df = pd.DataFrame(ic_rows)
    n_still_reversal = int((ic_df["still_reversal"] == "yes").sum()) if not ic_df.empty else 0
    lines += [md_table(ic_df[["factor", "dev_ic", "dev_icir", "still_reversal"]]),
              f"\n- factors still reversal on dev: {n_still_reversal} / {len(factor_names)}",
              f"- {'STABLE' if n_still_reversal >= len(factor_names) * 0.7 else 'UNSTABLE'}: "
              f"{'>= 70%' if n_still_reversal >= len(factor_names) * 0.7 else '< 70%'} "
              f"of factors retain reversal IC on dev\n"]

    # 3d: Dev trade list (first/last 10)
    lines += ["### 3d -- dev trade list (first 10 + last 10)\n"]
    if not dev_result.trades.empty:
        t = dev_result.trades.copy()
        dt_arr = pd.to_datetime(dev["datetime_utc"])
        t["entry_time"] = t["entry_i"].apply(lambda i: str(dt_arr.iloc[i]))
        t["exit_time"] = t["exit_i"].apply(lambda i: str(dt_arr.iloc[i]))
        t["side"] = t["side"].map({1: "L", -1: "S"}).fillna("?")
        show_cols = ["entry_time", "side", "bars_held", "net_pnl"]
        first10 = t.head(10)[show_cols].copy()
        last10 = t.tail(10)[show_cols].copy()
        first10["net_pnl"] = first10["net_pnl"].round(2)
        last10["net_pnl"] = last10["net_pnl"].round(2)
        lines += ["**First 10 trades:**\n",
                  md_table(first10),
                  "\n**Last 10 trades:**\n",
                  md_table(last10), "\n"]
    else:
        lines += ["No trades.\n"]

    # 3e: Regime/session distribution shift
    lines += ["### 3e -- regime/session distribution (research vs dev)\n"]
    from analysis.combo_screening import build_gates as _bg
    from analysis.system_research import regime_mask, session_mask
    r_gates = _bg(research)
    d_gates = _bg(dev)
    r_ts = research["timestamp"].to_numpy(np.int64)
    d_ts = dev["timestamp"].to_numpy(np.int64)

    regime_rows = []
    for regime in REGIMES:
        r_long = regime_mask(research, "long", regime, r_gates)
        d_long = regime_mask(dev, "long", regime, d_gates)
        regime_rows.append({
            "regime": regime,
            "research_pct": round(float(r_long.mean() * 100), 1),
            "dev_pct": round(float(d_long.mean() * 100), 1),
        })
    lines += ["Regime active percentage (long side):\n",
              md_table(pd.DataFrame(regime_rows)), "\n"]

    session_rows = []
    for sess in SESSIONS:
        r_s = session_mask(r_ts, sess, 300)
        d_s = session_mask(d_ts, sess, 300)
        session_rows.append({
            "session": sess,
            "research_pct": round(float(r_s.mean() * 100), 1),
            "dev_pct": round(float(d_s.mean() * 100), 1),
        })
    lines += ["Session active percentage:\n",
              md_table(pd.DataFrame(session_rows)), "\n"]


# ======================================================================
# Main
# ======================================================================
def main():
    lines = ["# Pre-locked dev evaluation -- rank-aggregation scalping config (5m)\n"]

    full = pd.read_csv(DATA)
    h, dev_start = holdout_split(full.timestamp.to_numpy("int64"), 183)
    research = full.iloc[:h].reset_index(drop=True)
    dev = full.iloc[h:].reset_index(drop=True)
    n = len(research)

    lines += [f"- research: {research.datetime_utc.iloc[0]} -> {research.datetime_utc.iloc[-1]} ({n} bars)",
              f"- dev: {dev.datetime_utc.iloc[0]} -> {dev.datetime_utc.iloc[-1]} ({len(dev)} bars)",
              f"- acceptance gates: Sharpe > {DEV_MIN_SHARPE}, maxDD > {DEV_MIN_MAXDD}%, "
              f"trades >= {DEV_MIN_TRADES}\n"]

    print("=== Step 1: freeze config on research ===")
    step1 = step1_freeze(lines, research, n)
    if not step1["ok"]:
        REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
        print("FAILED: no config selected")
        return

    print("=== Step 2: dev evaluation ===")
    step2 = step2_dev_eval(lines, dev, step1["cfg"], step1["factor_names"])

    print("=== Step 3: diagnostics ===")
    step3_diagnostics(lines, research, dev, step1["cfg"], step1["factor_names"],
                      step1["family"], step1, step2)

    # Verdict
    lines += ["## Verdict\n"]
    dm = step2["metrics"]
    dt = step2["trades"]
    # maxDD as percent of initial capital ($10k)
    maxdd_pct = float(dm["maxdd"] / 10000.0 * 100.0)

    gates_pass = {
        "sharpe": dm["sharpe"] > DEV_MIN_SHARPE,
        "maxdd": maxdd_pct > DEV_MIN_MAXDD,
        "trades": dt["trades"] >= DEV_MIN_TRADES,
    }
    lines += [f"- dev Sharpe {dm['sharpe']:+.3f} > {DEV_MIN_SHARPE}: "
              f"{'PASS' if gates_pass['sharpe'] else 'FAIL'}",
              f"- dev maxDD {maxdd_pct:.1f}% > {DEV_MIN_MAXDD}%: "
              f"{'PASS' if gates_pass['maxdd'] else 'FAIL'}",
              f"- dev trades {dt['trades']} >= {DEV_MIN_TRADES}: "
              f"{'PASS' if gates_pass['trades'] else 'FAIL'}\n"]

    n_pass = sum(gates_pass.values())
    if n_pass == 3:
        lines += ["**ACCEPTED**: the frozen config passes all three acceptance gates "
                  "on the dev segment. The config is cleared for live deployment "
                  "with continuous monitoring.\n"]
    elif n_pass >= 2:
        lines += [f"**MARGINAL**: {n_pass}/3 gates pass. The config shows partial "
                  f"out-of-sample viability but does not fully meet all criteria. "
                  f"Review the failing gate(s) before deployment.\n"]
    else:
        lines += [f"**REJECTED**: {n_pass}/3 gates pass. The config does not meet "
                  f"the acceptance criteria for live deployment.\n"]

    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"\nsaved {REPORT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
