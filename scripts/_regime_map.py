# -*- coding: utf-8 -*-
"""Phase 0: Regime map of the full sample.

Monthly aggregation: return, range, ADX, choppiness -> label each month
trend_up / trend_down / choppy.  Identifies down/choppy sub-periods that
can serve as development validation for short-side and regime-gate work.
"""
from __future__ import annotations

import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import numpy as np
import pandas as pd

DATA = ROOT / "data" / "xauusd_5m_indicators.csv.gz"
REPORTS = ROOT / "report"


def main() -> None:
    print(f"loading {DATA.name} ...")
    df = pd.read_csv(DATA)
    ts = pd.to_datetime(df["timestamp"], unit="s")
    df["dt"] = ts

    # monthly aggregation
    df["month"] = ts.dt.to_period("M")
    g = df.groupby("month")
    monthly = pd.DataFrame({
        "open": g["open"].first(),
        "high": g["high"].max(),
        "low": g["low"].min(),
        "close": g["close"].last(),
        "bars": g.size(),
        "adx_mean": g["adx_14"].mean(),
        "chop_mean": g["choppiness_14"].mean(),
    })
    monthly["ret_pct"] = (monthly["close"] / monthly["open"] - 1.0) * 100.0
    monthly["range_pct"] = (monthly["high"] / monthly["low"] - 1.0) * 100.0

    # label regime
    def label(r):
        if r["ret_pct"] > 3.0:
            return "trend_up"
        if r["ret_pct"] < -3.0:
            return "trend_down"
        if r["chop_mean"] > 50.0:
            return "choppy"
        return "flat"
    monthly["regime"] = monthly.apply(label, axis=1)

    # summary
    counts = monthly["regime"].value_counts()
    down_months = monthly[monthly["regime"] == "trend_down"]
    choppy_months = monthly[monthly["regime"] == "choppy"]

    print(f"\nfull sample: {ts.iloc[0]:%Y-%m-%d} -> {ts.iloc[-1]:%Y-%m-%d} ({len(df):,} bars)")
    print(f"months: {len(monthly)}   regime counts: {dict(counts)}")
    print(f"\ntrend_down months ({len(down_months)}):")
    for idx, r in down_months.iterrows():
        print(f"  {idx}  ret {r['ret_pct']:+.1f}%  range {r['range_pct']:.1f}%  "
              f"ADX {r['adx_mean']:.1f}  chop {r['chop_mean']:.1f}")
    print(f"\nchoppy months ({len(choppy_months)}):")
    for idx, r in choppy_months.iterrows():
        print(f"  {idx}  ret {r['ret_pct']:+.1f}%  range {r['range_pct']:.1f}%  "
              f"ADX {r['adx_mean']:.1f}  chop {r['chop_mean']:.1f}")

    # write report
    L = ["# Regime Map - XAUUSD 5m Monthly\n"]
    L.append(f"- data: `{DATA.name}` ({len(df):,} bars, "
             f"{ts.iloc[0]:%Y-%m-%d} -> {ts.iloc[-1]:%Y-%m-%d})")
    L.append(f"- months: {len(monthly)}   regime counts: {dict(counts)}\n")
    L.append("## All months\n")
    L.append("| month | ret% | range% | ADX | chop | regime |")
    L.append("|---|---:|---:|---:|---:|:---|")
    for idx, r in monthly.iterrows():
        L.append(f"| {idx} | {r['ret_pct']:+.1f} | {r['range_pct']:.1f} | "
                 f"{r['adx_mean']:.1f} | {r['chop_mean']:.1f} | {r['regime']} |")
    L.append(f"\n## trend_down months ({len(down_months)})\n")
    if down_months.empty:
        L.append("(none - sample is predominantly bullish)\n")
    else:
        L.append("| month | ret% | range% | ADX | chop |")
        L.append("|---|---:|---:|---:|---:|")
        for idx, r in down_months.iterrows():
            L.append(f"| {idx} | {r['ret_pct']:+.1f} | {r['range_pct']:.1f} | "
                     f"{r['adx_mean']:.1f} | {r['chop_mean']:.1f} |")
    L.append(f"\n## choppy months ({len(choppy_months)})\n")
    if choppy_months.empty:
        L.append("(none)\n")
    else:
        L.append("| month | ret% | range% | ADX | chop |")
        L.append("|---|---:|---:|---:|---:|")
        for idx, r in choppy_months.iterrows():
            L.append(f"| {idx} | {r['ret_pct']:+.1f} | {r['range_pct']:.1f} | "
                     f"{r['adx_mean']:.1f} | {r['chop_mean']:.1f} |")
    L.append("\n## Implication\n")
    if len(down_months) >= 2:
        L.append(f"- {len(down_months)} down months found in the research period - "
                 "usable as development validation for short-side / regime-gate work.")
    else:
        L.append("- Few down months in the research period - the 2026-03->09 sealed "
                 "holdout (now consumed) is the main down-regime development set.")
    L.append("- The walk-forward folds (2024-03 -> 2026-03) are predominantly bullish; "
             "short-side edge cannot be fully validated on them alone.")

    out = REPORTS / "regime_map.md"
    out.write_text("\n".join(L) + "\n", encoding="utf-8")
    print(f"\nsaved: {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
