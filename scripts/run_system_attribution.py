"""Attribute the legacy long/short system using the current 1 oz account."""
from __future__ import annotations

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd

from analysis.combo_screening import holdout_split
from analysis.system_research import LONG_ATTR as LONG
from analysis.system_research import SHORT_ATTR as SHORT
from analysis.system_research import bar_metrics, run_engine

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "xauusd_5m_indicators.csv.gz"
OUT = ROOT / "report" / "system_attribution.md"


def summary(name, result, metrics):
    rows = []
    if result.trades.empty:
        return [f"### {name}\n", "No trades.\n"]
    for reason, g in result.trades.groupby("exit_reason"):
        rows.append(f"| {reason} | {len(g)} | ${g.net_pnl.sum():+.2f} | ${g.net_pnl.mean():+.2f} | ${g.costs.sum():.2f} |")
    return [f"### {name}\n", f"- PnL: ${metrics['pnl']:+.2f}; 5m Sharpe: {metrics['sharpe']:.2f}; max DD: ${metrics['maxdd']:.2f}\n",
            "| exit reason | trades | PnL | avg trade | costs |", "|---|---:|---:|---:|---:|", *rows, ""]


def main():
    df = pd.read_csv(DATA)
    h, start = holdout_split(df.timestamp.to_numpy("int64"), 183)
    research = df.iloc[:h].reset_index(drop=True)
    lines = ["# Single-account attribution (0.01 lot = 1 oz)\n",
             f"- research: {research.datetime_utc.iloc[0]} -> {research.datetime_utc.iloc[-1]}",
             f"- development segment excluded: {start:%Y-%m-%d} -> {df.datetime_utc.iloc[-1]}",
             "- cost: $0.16 round trip per 1 oz; capital: $10,000.\n"]
    cases = [("long only, no exit", LONG, None, "none"),
             ("short only, no exit", None, SHORT, "none"),
             ("combined, no exit", LONG, SHORT, "none"),
             ("long only, 2.5 ATR stop", LONG, None, "stop2_5"),
             ("short only, 2.5 ATR stop", None, SHORT, "stop2_5"),
             ("combined, 2.5 ATR stop", LONG, SHORT, "stop2_5")]
    totals = []
    for name, long, short, exit_name in cases:
        result, target, metrics, conflicts = run_engine(research, long, short, exit_name)
        if abs(target).max() > 1:
            raise RuntimeError("attribution exceeded 1 oz")
        totals.append({"case": name, **metrics, "trades": len(result.trades), "conflicts": conflicts})
        lines.extend(summary(name, result, metrics))
    table = pd.DataFrame(totals)
    lines += ["## Comparison\n", table.to_markdown(index=False), "",
              "## Interpretation\n",
              "Compare the combined cases with the sum of their legs: any gap is caused by single-account reversals and mutual position replacement. Compare each no-exit/stop pair to isolate the conservative ATR exit effect.\n"]
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"saved {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
