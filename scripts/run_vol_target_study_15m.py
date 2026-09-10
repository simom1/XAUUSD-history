"""Volatility-targeted sizing vs fixed 1 oz on the 15m transfer specification.

15m mirror of scripts/run_vol_target_study.py.  The base signal is the
cross-timeframe transfer spec -- the locked 5-minute system rescaled to 15m
bars (long plus_di_14 W2016 T2.0 H28 new_york; short aroon_up_25 W2016 T1.5
H28 london; no protective exit; scripts/run_15m_transfer_test.py) -- so the
sizing layer is tested on the only 15m system with a frozen, externally
specified signal; nothing is mined here.  The pre-specified sizing rule is

    oz_t = clip(ref_oz * trailing_median(atr_14, 672)_t / atr_14_t, floor, cap)

(672 15m bars = the 5m study's 2016-bar / 7-day median; min_periods 96 = 1
day), decided at the same bar close as the signal and frozen for the whole
position episode, keeping the trade stream identical to fixed sizing.  The
floor/cap grid is reported for robustness only; nothing is picked from it.
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
from analysis.system_research import Component, bar_metrics, system_target, vol_scaled_target
from backtest import BacktestConfig, BacktestEngine

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "xauusd_15m_indicators.csv.gz"
REPORT = ROOT / "report" / "vol_target_sizing_15m.md"

BAR_SECONDS, ANN = 900, float(np.sqrt(96 * 252))
REF_OZ, MED_WINDOW, MIN_PERIODS = 1.0, 672, 96

# Locked 5m spec rescaled to 15m, exactly as run_15m_transfer_test.py.
LONG = Component("long", "plus_di_14", "high", 2016, 2.0, 28, "none", "new_york")
SHORT = Component("short", "aroon_up_25", "high", 2016, 1.5, 28, "none", "london")


def run_fixed(df, factors, gates, oz=1.0):
    target, conflicts = system_target(df, LONG, SHORT, factors, gates, oz,
                                      bar_seconds=BAR_SECONDS)
    result = BacktestEngine(BacktestConfig(max_position_oz=oz,
                                           bar_seconds=BAR_SECONDS)).run(df, target)
    return result, conflicts


def run_vol(df, factors, gates, floor, cap):
    target, conflicts = vol_scaled_target(df, LONG, SHORT, REF_OZ, MED_WINDOW,
                                          MIN_PERIODS, floor, cap, factors, gates,
                                          bar_seconds=BAR_SECONDS)
    result = BacktestEngine(BacktestConfig(max_position_oz=cap,
                                           bar_seconds=BAR_SECONDS)).run(df, target)
    return result, conflicts


def row(name, result, lo, hi):
    m = bar_metrics(result, lo, hi, ann=ANN)
    tr = result.trades[(result.trades.entry_i >= lo) & (result.trades.entry_i < hi)]
    return {"case": name, "pnl": round(m["pnl"], 2), "sharpe": round(m["sharpe"], 3),
            "maxdd": round(m["maxdd"], 2), "trades": len(tr),
            "avg_oz": round(float(tr["oz"].mean()), 3) if len(tr) else 0.0,
            "costs": round(float(tr["costs"].sum()), 2)}


def main():
    df = pd.read_csv(DATA)
    h, dev_start = holdout_split(df.timestamp.to_numpy(np.int64), 183)
    research = df.iloc[:h].reset_index(drop=True)
    folds = fold_list(research.timestamp.to_numpy(np.int64), len(research), 4, 183)
    factors, gates = build_factors(research, fast_window=32), build_gates(research)

    fixed, _ = run_fixed(research, factors, gates)
    sanity = fixed.equity[-1] - fixed.config.initial_capital
    assert abs(sanity - 1158.81) < 0.05, f"fixed-1oz baseline drifted: {sanity}"

    vol, _ = run_vol(research, factors, gates, 0.25, 2.0)

    lines = ["# Volatility-targeted sizing vs fixed 1 oz (15m bars)\n",
             "- data: XAUUSD 15m only; research period excludes the consumed development set.",
             f"- research: {research.datetime_utc.iloc[0]} -> {research.datetime_utc.iloc[-1]}",
             f"- development segment (untouched): {dev_start:%Y-%m-%d} -> {df.datetime_utc.iloc[-1]}",
             "- signals (unchanged, 15m transfer spec from scripts/run_15m_transfer_test.py): "
             f"long `{LONG.key}`, short `{SHORT.key}`, no protective exit; 15m Sharpe annualized with 96 bars/day.",
             "- sizing rule (pre-specified): oz_t = clip(1.0 * median(atr_14, 672)_t / atr_14_t, 0.25, 2.0); "
               "672 15m bars = the 5m study's 7-day median window; size and signal decided at the same bar "
               "close, trailing data only; the size is frozen for the whole position episode (entry/reversal "
               "bar decides), keeping the trade stream identical to fixed sizing.",
             "- sanity: fixed-1oz research PnL reproduces the corrected transfer-test research row ($+1,158.81).\n",
             "## Walk-forward fold comparison\n",
             "| fold | case | PnL | 15m Sharpe | maxDD | trades | avg oz | costs |",
             "|---|---|---:|---:|---:|---:|---:|---:|"]
    for fold in folds:
        lo, hi = fold["test_lo"], fold["test_hi"]
        for name, res in (("fixed", fixed), ("vol", vol)):
            r = row(f"{fold['name']} {name}", res, lo, hi)
            lines.append(f"| {fold['name']} | {name} | ${r['pnl']:+.2f} | {r['sharpe']:.2f} | "
                         f"${r['maxdd']:,.2f} | {r['trades']} | {r['avg_oz']} | ${r['costs']:.2f} |")
    lines.append("")

    tot_f, tot_v = row("research fixed", fixed, 0, len(research)), row("research vol", vol, 0, len(research))
    lines += ["## Whole research period\n",
              pd.DataFrame([tot_f, tot_v]).to_markdown(index=False), "",
              "`avg_oz` is the mean trade size realized inside the segment; "
              "`maxdd` is in USD on the 1-account equity path.", "",
              "## Sensitivity (whole research period, reported not selected)\n",
              "| floor | cap | PnL | 15m Sharpe | maxDD | trades | avg oz | costs |",
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
              "Unlike the 5-minute study (Sharpe 0.83 -> 1.14), at 15 minutes the rule "
              "does NOT lift Sharpe (1.202 -> 1.127): with 3x fewer and longer episodes "
              "the ATR tilt has too few re-pricing points to pay for the exposure it "
              "gives up. It remains a pure risk reducer: maxDD -45% (-$421 -> -$233) for "
              "~11% less PnL at 0.89 oz average exposure, stable across the floor/cap "
              "grid (no sign flip, maxDD identical at -$232.93 in every cell). This is a "
              "sizing-layer diagnostic on the 15m transfer spec, not a new candidate; no "
              "parameter is selected from the sensitivity grid.\n"]
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"saved {REPORT.relative_to(ROOT)}")
    print(pd.DataFrame([tot_f, tot_v]).to_string(index=False))


if __name__ == "__main__":
    main()
