"""Nested walk-forward search for a 1 oz single-account development candidate."""
from __future__ import annotations

import json
import sys
from dataclasses import asdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
import pandas as pd

from analysis.combo_screening import build_gates, fold_list, holdout_split
from analysis.factor_screening import build_factors
from analysis.system_research import (EXITS, Component, bar_metrics, components,
                                      fast_component_score, run_engine)

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "xauusd_5m_indicators.csv.gz"
REPORT = ROOT / "report" / "single_account_walkforward.md"
CSV = ROOT / "report" / "single_account_fold_picks.csv"


def md_table(frame: pd.DataFrame) -> str:
    if frame.empty:
        return "(none)"
    cols = list(frame.columns)
    lines = ["| " + " | ".join(cols) + " |", "|" + "|".join("---:" for _ in cols) + "|"]
    for _, row in frame.iterrows():
        lines.append("| " + " | ".join(str(row[c]) for c in cols) + " |")
    return "\n".join(lines)


def top_components(df, factors, gates, side: str, n: int = 3):
    scores = [fast_component_score(df, c, factors, gates) for c in components(side)]
    good = [x for x in scores if x["trades_proxy"] >= 20 and x["avg"] > 0]
    return sorted(good, key=lambda x: x["sharpe"], reverse=True)[:n]


def signature(long: Component, short: Component, exit_name: str) -> str:
    return json.dumps({"long": asdict(long), "short": asdict(short), "exit": exit_name}, sort_keys=True)


def main():
    full = pd.read_csv(DATA)
    h, dev_start = holdout_split(full.timestamp.to_numpy("int64"), 183)
    research = full.iloc[:h].reset_index(drop=True)
    folds = fold_list(research.timestamp.to_numpy("int64"), len(research), 4, 183)
    factors = build_factors(research)
    gates = build_gates(research)
    picks = []

    for fold in folds:
        lo, hi = fold["test_lo"], fold["test_hi"]
        train, f_train = research.iloc[:lo].reset_index(drop=True), factors.iloc[:lo].reset_index(drop=True)
        g_train = {k: v[:lo] for k, v in gates.items()}
        longs, shorts = top_components(train, f_train, g_train, "long"), top_components(train, f_train, g_train, "short")
        candidates = []
        for l in longs:
            for s in shorts:
                for exit_name, _ in EXITS:
                    result, _, metrics, conflicts = run_engine(train, l["component"], s["component"], exit_name,
                                                               f_train, g_train)
                    avg = result.trades.net_pnl.mean() if not result.trades.empty else -np.inf
                    if len(result.trades) >= 20 and avg > 0:
                        candidates.append((metrics["sharpe"], metrics, l["component"], s["component"], exit_name, conflicts))
        if not candidates:
            continue
        _, train_m, long, short, exit_name, conflicts = max(candidates, key=lambda x: x[0])
        context, f_context = research.iloc[:hi].reset_index(drop=True), factors.iloc[:hi].reset_index(drop=True)
        g_context = {k: v[:hi] for k, v in gates.items()}
        result, target, _, test_conflicts = run_engine(context, long, short, exit_name, f_context, g_context)
        test_m = bar_metrics(result, lo, hi)
        test_trades = result.trades[(result.trades.entry_i >= lo) & (result.trades.entry_i < hi)]
        picks.append({"fold": fold["name"], "window": f"{fold['test_start']}->{fold['test_end']}",
                      "signature": signature(long, short, exit_name), "long": long.key, "short": short.key,
                      "exit": exit_name, "train_sharpe": round(train_m["sharpe"], 3),
                      "test_pnl": round(test_m["pnl"], 2), "test_sharpe": round(test_m["sharpe"], 3),
                      "test_maxdd": round(test_m["maxdd"], 2), "test_trades": len(test_trades),
                      "conflicts": conflicts + test_conflicts})

    out = pd.DataFrame(picks)
    out.to_csv(CSV, index=False)
    lines = ["# Single-account nested walk-forward (0.01 lot = 1 oz)\n",
             f"- research: {research.datetime_utc.iloc[0]} -> {research.datetime_utc.iloc[-1]}",
             f"- development excluded from selection: {dev_start:%Y-%m-%d} -> {full.datetime_utc.iloc[-1]}",
             "- each fold selects long/short components and exit rules from its training prefix only.",
             "- exits are always evaluated by the event engine; component preselection is fast-path only.\n",
             "## Fold selections\n", md_table(out.drop(columns=["signature"]) if not out.empty else out), ""]
    winner = None
    if not out.empty:
        counts = out.groupby("signature").agg(picks=("fold", "count"), positives=("test_pnl", lambda s: int((s > 0).sum())),
                                                mean_sharpe=("test_sharpe", "mean"), trades=("test_trades", "sum")).reset_index()
        eligible = counts[(counts.picks >= 3) & (counts.positives >= 3) & (counts.trades >= 100)]
        lines += ["## Consensus\n", md_table(counts.drop(columns=["signature"])), ""]
        if not eligible.empty:
            winner = eligible.sort_values(["mean_sharpe", "picks"], ascending=False).iloc[0]
            spec = json.loads(winner.signature)
            long, short = Component(**spec["long"]), Component(**spec["short"])
            exit_name = spec["exit"]
            lines += ["## Locked development candidate\n", f"- long: `{long.key}`", f"- short: `{short.key}`",
                      f"- exit: `{exit_name}`", f"- selected in {winner.picks} folds; test-positive folds: {winner.positives}.\n"]
            # Development is deliberately evaluated only after the candidate is locked.
            dev = full.iloc[h:].reset_index(drop=True)
            dev_f, dev_g = build_factors(dev), build_gates(dev)
            dev_result, _, dev_m, _ = run_engine(dev, long, short, exit_name, dev_f, dev_g)
            lines += ["## Consumed development diagnostic\n", f"- PnL: ${dev_m['pnl']:+.2f}",
                      f"- 5m Sharpe: {dev_m['sharpe']:.2f}", f"- max drawdown: ${dev_m['maxdd']:.2f}",
                      "- This result did not influence the candidate selection.\n",
                      "## Capacity sensitivity\n", "| lot | oz | PnL | 5m Sharpe | max drawdown |", "|---|---:|---:|---:|---:|"]
            for lot, oz in ((0.01, 1.0), (0.05, 5.0), (0.10, 10.0)):
                r, target, m, _ = run_engine(research, long, short, exit_name, factors, gates, oz)
                if abs(target).max() > oz:
                    raise RuntimeError("capacity target exceeded limit")
                lines.append(f"| {lot:.2f} | {oz:.0f} | ${m['pnl']:+.2f} | {m['sharpe']:.2f} | ${m['maxdd']:.2f} |")
        else:
            lines += ["## Outcome\n", "No static development candidate was independently selected in at least three folds with at least three positive test folds and 100 total test trades.\n"]
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"saved {REPORT.relative_to(ROOT)} and {CSV.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
