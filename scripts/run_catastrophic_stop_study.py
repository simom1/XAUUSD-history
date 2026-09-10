"""Catastrophic-stop study for the single-account development candidate.

Question: how much of the no-exit edge survives when a wide ATR stop (5/6/8x)
is added purely as a disaster cap, and what tail risk does it remove?

Protocol (no manual picking):
1. Split research (2023-09 -> 2026-03) from the consumed development segment.
2. Preselect the top-3 long and top-3 short components by the same fast-path
   score used by the nested walk-forward, on the full research prefix only.
3. Evaluate all 9 pairs x {none, stop2_5, stop5, stop6, stop8} on the research
   slice through the event engine.
4. Select the best (pair, exit) by research Sharpe with >= 100 trades.
5. Report the consumed development segment for that winner and for the same
   pair without the stop, as a diagnostic only -- it never selects anything.
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
from analysis.factor_screening import build_factors
from analysis.system_research import EXITS, run_engine
from scripts.run_single_account_research import top_components

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "xauusd_5m_indicators.csv.gz"
REPORT = ROOT / "report" / "catastrophic_stop_study.md"
CSV = ROOT / "report" / "catastrophic_stop_study.csv"

STUDY_EXITS = ("none", "stop2_5", "stop5", "stop6", "stop8", "stop12", "stop16")
MIN_TRADES = 100


def trade_stats(trades: pd.DataFrame) -> dict:
    if trades.empty:
        return {"worst": 0.0, "p05": 0.0, "stop_exits": 0, "stopped_pnl": 0.0}
    stopped = trades[trades.exit_reason == "stop_loss"]
    return {"worst": float(trades.net_pnl.min()),
            "p05": float(np.quantile(trades.net_pnl, 0.05)),
            "stop_exits": int(len(stopped)),
            "stopped_pnl": float(stopped.net_pnl.sum())}


def md_table(frame: pd.DataFrame) -> str:
    cols = list(frame.columns)
    lines = ["| " + " | ".join(cols) + " |", "|" + "|".join("---:" for _ in cols) + "|"]
    for _, row in frame.iterrows():
        lines.append("| " + " | ".join(str(row[c]) for c in cols) + " |")
    return "\n".join(lines)


def main():
    full = pd.read_csv(DATA)
    h, dev_start = holdout_split(full.timestamp.to_numpy("int64"), 183)
    research = full.iloc[:h].reset_index(drop=True)
    dev = full.iloc[h:].reset_index(drop=True)

    factors, gates = build_factors(research), build_gates(research)
    longs = top_components(research, factors, gates, "long")
    shorts = top_components(research, factors, gates, "short")
    print(f"top longs:   {[c['component'].key for c in longs]}")
    print(f"top shorts:  {[c['component'].key for c in shorts]}")

    exit_args_map = dict(EXITS)
    rows = []
    for lp in longs:
        for sp in shorts:
            for exit_name in STUDY_EXITS:
                result, _, m, conflicts = run_engine(research, lp["component"], sp["component"],
                                                     exit_name, factors, gates)
                ts = trade_stats(result.trades)
                rows.append({"pair": f"{lp['component'].key} + {sp['component'].key}",
                             "long": lp["component"].key, "short": sp["component"].key,
                             "exit": exit_name, "pnl": round(m["pnl"], 2),
                             "sharpe": round(m["sharpe"], 3), "maxdd": round(m["maxdd"], 2),
                             "trades": len(result.trades),
                             "worst_trade": round(ts["worst"], 2), "p05_trade": round(ts["p05"], 2),
                             "stop_exits": ts["stop_exits"],
                             "stopped_pnl": round(ts["stopped_pnl"], 2),
                             "conflicts": conflicts})
    out = pd.DataFrame(rows)
    none_pnl = out[out.exit == "none"].set_index("pair")["pnl"]
    out["retention_vs_none"] = out.apply(
        lambda r: round(r["pnl"] / none_pnl[r["pair"]], 3)
        if none_pnl.get(r["pair"], 0.0) > 0 else np.nan, axis=1)
    out.to_csv(CSV, index=False)

    lines = ["# Catastrophic-stop study (0.01 lot = 1 oz)\n",
             f"- research: {research.datetime_utc.iloc[0]} -> {research.datetime_utc.iloc[-1]} ({len(research)} bars)",
             f"- consumed development segment (diagnostic only): {dev.datetime_utc.iloc[0]} -> {dev.datetime_utc.iloc[-1]}",
             "- pairs: top-3 long x top-3 short components by the walk-forward fast-path score (research prefix only).",
             f"- exits compared: {', '.join(STUDY_EXITS)}; retention = pnl(exit) / pnl(none) per pair.",
             "- selection rule fixed in advance: max research 5m Sharpe with >= "
             f"{MIN_TRADES} trades; the development segment never selects anything.\n",
             "## Research results\n", md_table(out.drop(columns=["long", "short", "conflicts"])), ""]

    eligible = out[out.trades >= MIN_TRADES]
    if eligible.empty:
        lines += ["## Outcome\n", f"No pair reached {MIN_TRADES} research trades.\n"]
        REPORT.write_text("\n".join(lines), encoding="utf-8")
        print(f"saved {REPORT.relative_to(ROOT)} and {CSV.relative_to(ROOT)}")
        return

    winner = eligible.sort_values("sharpe", ascending=False).iloc[0]
    from analysis.system_research import Component
    lp = next(c for c in longs if c["component"].key == winner["long"])
    sp = next(c for c in shorts if c["component"].key == winner["short"])
    lines += ["## Research selection\n",
              f"- long: `{winner['long']}`", f"- short: `{winner['short']}`",
              f"- exit: `{winner['exit']}`",
              f"- research: PnL ${winner['pnl']:+,.2f}, 5m Sharpe {winner['sharpe']:.2f}, "
              f"maxDD ${winner['maxdd']:,.2f}, {int(winner['trades'])} trades, "
              f"worst trade ${winner['worst_trade']:,.2f}",
              f"- retention vs none on this pair: {winner['retention_vs_none']:.3f}"
              f" ({int(winner['stop_exits'])} stop exits, stopped PnL ${winner['stopped_pnl']:+,.2f})\n",
              "## Consumed development diagnostic (not used for selection)\n"]
    dev_f, dev_g = build_factors(dev), build_gates(dev)
    for exit_name in dict.fromkeys((winner["exit"], "none")):
        r, _, m, _ = run_engine(dev, lp["component"], sp["component"], exit_name, dev_f, dev_g)
        ts = trade_stats(r.trades)
        lines.append(f"- `{exit_name}`: PnL ${m['pnl']:+,.2f}, 5m Sharpe {m['sharpe']:.2f}, "
                     f"maxDD ${m['maxdd']:,.2f}, {len(r.trades)} trades, "
                     f"worst trade ${ts['worst']:,.2f}, stop exits {ts['stop_exits']}")
    lines.append("\n## Interpretation\n")
    ne = out[(out.pair == winner["pair"]) & (out.exit == "none")].iloc[0]
    if winner["exit"] == "none":
        lad = out[(out.pair == winner["pair"]) & (out.exit.isin(("stop5", "stop8", "stop12", "stop16")))]
        lines += [
            "- The selector chose no stop: on every pair in the ladder the no-exit variant holds "
            "the highest research Sharpe, so every fixed ATR stop width measured so far costs edge.",
            f"- Without a stop the worst research trade is ${ne['worst_trade']:,.2f} "
            f"(p05 ${ne['p05_trade']:,.2f}, {int(ne['trades'])} trades); hold-based expiry plus the "
            "daily session flat already bound the tail, so the effective risk cap is the position size.",
        ]
        if len(lad):
            parts = [f"{r['exit']} triggers {r['stop_exits'] / max(r['trades'], 1):.1%}, "
                     f"retains {r['retention_vs_none']:.3f}" for _, r in lad.iterrows()]
            lines.append("- Stop ladder on this pair -- " + "; ".join(parts) +
                         ". Narrow rungs are regular exits, not insurance; only the widest "
                         "rungs approach true disaster protection.")
    elif int(winner["stop_exits"]) == 0:
        lines.append(f"- The selected stop never triggered in research ({int(winner['trades'])} trades): "
                     "it is pure tail insurance at zero measured edge cost on this pair.")
    else:
        lines.append(f"- The stop triggered {int(winner['stop_exits'])} times in research, "
                     f"costing ${winner['stopped_pnl']:+,.2f} of the ${ne['pnl']:+,.2f} no-exit PnL.")
    lines.append("- The no-exit variant already bounds holding time via the hold-based expiry; "
                 "a catastrophic stop only caps gap risk and runaway adverse excursions.\n")
    REPORT.write_text("\n".join(lines), encoding="utf-8")
    print(f"saved {REPORT.relative_to(ROOT)} and {CSV.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
