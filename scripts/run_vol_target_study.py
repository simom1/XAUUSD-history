"""Volatility-targeted sizing vs fixed 1 oz on the legacy attribution spec.

Pre-specified rule (no parameter search): same signals as the attribution
report (long plus_di_14 / short close_vs_ema200, W6048 T1.5 H120, trend_adx,
no protective exit); the only change is position size

    oz_t = clip(ref_oz * trailing_median(atr_14, 2016)_t / atr_14_t, 0.25, 2.0)

decided at the same bar close as the signal.  High ATR -> smaller size, low
ATR -> larger size, capped at 2 oz.  The size is frozen for the whole
position episode (entry/reversal bar decides it); a continuously re-sized
target would make the engine trade a resize nearly every bar, which is not
the rule being studied.  The floor/cap grid in the sensitivity
table is reported for robustness only; nothing is picked from it.
Development segment (last 183 days) is excluded and untouched.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
import pandas as pd

from analysis.combo_screening import build_gates, fold_list, holdout_split
from analysis.factor_screening import build_factors
from analysis.system_research import (LONG_ATTR as LONG, SHORT_ATTR as SHORT,
                                      Component, bar_metrics, vol_scaled_target)
from backtest import BacktestConfig, BacktestEngine

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "xauusd_5m_indicators.csv.gz"
REPORT = ROOT / "report" / "vol_target_sizing.md"

REF_OZ, MED_WINDOW, MIN_PERIODS = 1.0, 2016, 288


def run_fixed(df, factors, gates, oz=1.0):
    from analysis.system_research import system_target
    target, conflicts = system_target(df, LONG, SHORT, factors, gates, oz)
    result = BacktestEngine(BacktestConfig(max_position_oz=oz)).run(df, target)
    return result, conflicts


def run_vol(df, factors, gates, floor, cap):
    target, conflicts = vol_scaled_target(df, LONG, SHORT, REF_OZ, MED_WINDOW,
                                          MIN_PERIODS, floor, cap, factors, gates)
    result = BacktestEngine(BacktestConfig(max_position_oz=cap)).run(df, target)
    return result, conflicts


def row(name, result, lo, hi):
    m = bar_metrics(result, lo, hi)
    tr = result.trades[(result.trades.entry_i >= lo) & (result.trades.entry_i < hi)]
    return {"case": name, "pnl": round(m["pnl"], 2), "sharpe": round(m["sharpe"], 3),
            "maxdd": round(m["maxdd"], 2), "trades": len(tr),
            "avg_oz": round(float(tr["oz"].mean()), 3) if len(tr) else 0.0,
            "costs": round(float(tr["costs"].sum()), 2)}


def md(frame):
    if frame.empty:
        return "(none)"
    return frame.to_markdown(index=False)


def main():
    df = pd.read_csv(DATA)
    h, dev_start = holdout_split(df.timestamp.to_numpy(np.int64), 183)
    research = df.iloc[:h].reset_index(drop=True)
    folds = fold_list(research.timestamp.to_numpy(np.int64), len(research), 4, 183)
    factors, gates = build_factors(research), build_gates(research)

    fixed, _ = run_fixed(research, factors, gates)
    sanity = fixed.equity[-1] - fixed.config.initial_capital
    assert abs(sanity - 1162.17) < 0.01, f"fixed-1oz baseline drifted: {sanity}"

    vol, _ = run_vol(research, factors, gates, 0.25, 2.0)

    lines = ["# Volatility-targeted sizing vs fixed 1 oz\n",
             "- data: XAUUSD 5m only; research period excludes the consumed development set.",
             f"- research: {research.datetime_utc.iloc[0]} -> {research.datetime_utc.iloc[-1]}",
             f"- development segment (untouched): {dev_start:%Y-%m-%d} -> {df.datetime_utc.iloc[-1]}",
             "- signals (unchanged, from report/system_attribution.md): "
             f"long `{LONG.key}`, short `{SHORT.key}`, no protective exit.",
             "- sizing rule (pre-specified): oz_t = clip(1.0 * median(atr_14, 2016)_t / atr_14_t, 0.25, 2.0); "
               "size and signal decided at the same bar close, trailing data only; "
               "the size is frozen for the whole position episode (entry/reversal bar decides), "
               "keeping the trade stream identical to fixed sizing.",
             "- sanity: fixed-1oz research PnL reproduces the attribution report ($+1,162.17).\n",
             "## Walk-forward fold comparison\n",
             "| fold | case | PnL | 5m Sharpe | maxDD | trades | avg oz | costs |",
             "|---|---|---:|---:|---:|---:|---:|---:|"]
    fold_rows = []
    for fold in folds:
        lo, hi = fold["test_lo"], fold["test_hi"]
        for name, res in (("fixed", fixed), ("vol", vol)):
            r = row(f"{fold['name']} {name}", res, lo, hi)
            fold_rows.append(r)
            lines.append(f"| {fold['name']} | {name} | ${r['pnl']:+.2f} | {r['sharpe']:.2f} | "
                         f"${r['maxdd']:,.2f} | {r['trades']} | {r['avg_oz']} | ${r['costs']:.2f} |")
    lines.append("")

    tot_f = row("research fixed", fixed, 0, len(research))
    tot_v = row("research vol", vol, 0, len(research))
    lines += ["## Whole research period\n",
              md(pd.DataFrame([tot_f, tot_v])), "",
              "`avg_oz` is the mean trade size realized inside the segment; "
              "`maxdd` is in USD on the 1-account equity path.", "",
              "## Sensitivity (whole research period, reported not selected)\n",
              "| floor | cap | PnL | 5m Sharpe | maxDD | trades | avg oz | costs |",
              "|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for floor in (0.25, 0.5):
        for cap in (1.5, 2.0, 3.0):
            r, _ = run_vol(research, factors, gates, floor, cap)
            m = row(f"{floor}/{cap}", r, 0, len(research))
            lines.append(f"| {floor} | {cap} | ${m['pnl']:+.2f} | {m['sharpe']:.2f} | "
                         f"${m['maxdd']:,.2f} | {m['trades']} | {m['avg_oz']} | ${m['costs']:.2f} |")
    lines += ["",
              "## Interpretation\n",
              "Vol targeting trades the same signal stream: trade count is identical "
              "(session-boundary effects aside), so differences come purely from sizing. "
              "Compare Sharpe (cost-aware, leverage-sensitive) and maxDD (absolute risk) "
              "against the avg-oz exposure actually taken.\n"]
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"saved {REPORT.relative_to(ROOT)}")
    print(pd.DataFrame([tot_f, tot_v]).to_string(index=False))


if __name__ == "__main__":
    main()
