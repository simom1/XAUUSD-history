"""Explain single-account walk-forward instability without reading development data."""
from __future__ import annotations

import json
import sys
from collections import Counter
from dataclasses import asdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
import pandas as pd

from analysis.combo_screening import build_gates, fold_list, holdout_split
from analysis.factor_screening import Session, build_factors, path_from_targets, pnl_from_path
from analysis.system_research import Component, EXITS, bar_metrics, components, fast_component_score, run_engine

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "xauusd_5m_indicators.csv.gz"
REPORT = ROOT / "report" / "single_account_stability_attribution.md"
CSV = ROOT / "report" / "single_account_stability_picks.csv"
SHAPES = ("long_only", "short_only", "long_short")


def table(df: pd.DataFrame) -> str:
    if df.empty:
        return "(none)"
    return df.to_markdown(index=False)


def top(df, factors, gates, side: str) -> list[Component]:
    scored = [fast_component_score(df, c, factors, gates) for c in components(side)]
    valid = [x for x in scored if x["trades_proxy"] >= 20 and x["avg"] > 0]
    return [x["component"] for x in sorted(valid, key=lambda x: x["sharpe"], reverse=True)[:3]]


def specs(longs: list[Component], shorts: list[Component], shape: str):
    if shape == "long_only":
        return ((l, None) for l in longs)
    if shape == "short_only":
        return ((None, s) for s in shorts)
    return ((l, s) for l in longs for s in shorts)


def key(shape: str, long: Component | None, short: Component | None, exit_name: str) -> str:
    return json.dumps({"shape": shape, "long": asdict(long) if long else None,
                       "short": asdict(short) if short else None, "exit": exit_name}, sort_keys=True)


def component_key(component: Component | None) -> str | None:
    return component.key if component else None


def exit_contributions(trades: pd.DataFrame) -> list[dict]:
    if trades.empty:
        return []
    next_entry = trades["entry_i"].shift(-1)
    next_side = trades["side"].shift(-1)
    reversal = ((trades["exit_reason"] == "signal") & (trades["exit_i"] == next_entry) &
                (trades["side"] != next_side))
    labels = np.where(reversal, "signal_reversal", trades["exit_reason"])
    frame = trades.assign(contribution=labels)
    return [{"contribution": name, "trades": len(g), "pnl": g.net_pnl.sum(),
             "avg": g.net_pnl.mean(), "costs": g.costs.sum()}
            for name, g in frame.groupby("contribution")]


def verify_no_exit_calibration(df: pd.DataFrame, target: np.ndarray, result) -> None:
    """Fail closed when the no-exit fast accounting diverges from the engine."""
    session = Session(df.timestamp.to_numpy(np.int64))
    pos = path_from_targets(target, session.blocked, session.flat)
    fast_pnl = pnl_from_path(pos, df.open.to_numpy(float), df.close.to_numpy(float), session.flat).sum()
    engine_pnl = result.equity[-1] - result.config.initial_capital
    previous = np.r_[0.0, pos[:-1]]
    fast_trades = int(np.count_nonzero((pos != 0.0) & (pos != previous)))
    if not np.isclose(fast_pnl, engine_pnl, atol=1e-6) or fast_trades != len(result.trades):
        raise RuntimeError("fast no-exit accounting does not match the event engine")
    if not np.isclose(result.trades.costs.sum(), len(result.trades) * 0.16, atol=1e-9):
        raise RuntimeError("no-exit trade costs do not match the $0.16 round-trip model")


def main() -> None:
    full = pd.read_csv(DATA)
    research_end, dev_start = holdout_split(full.timestamp.to_numpy(np.int64), 183)
    research = full.iloc[:research_end].reset_index(drop=True)
    factors, gates = build_factors(research), build_gates(research)
    folds = fold_list(research.timestamp.to_numpy(np.int64), len(research), 4, 183)
    picks, contribution_rows = [], []

    for fold in folds:
        lo, hi = fold["test_lo"], fold["test_hi"]
        train, f_train = research.iloc[:lo].reset_index(drop=True), factors.iloc[:lo].reset_index(drop=True)
        g_train = {name: values[:lo] for name, values in gates.items()}
        long_top, short_top = top(train, f_train, g_train, "long"), top(train, f_train, g_train, "short")
        for shape in SHAPES:
            candidates = []
            for long, short in specs(long_top, short_top, shape):
                for exit_name, _ in EXITS:
                    result, target, metrics, conflicts = run_engine(train, long, short, exit_name, f_train, g_train)
                    if exit_name == "none":
                        verify_no_exit_calibration(train, target, result)
                    avg = result.trades.net_pnl.mean() if not result.trades.empty else -np.inf
                    if len(result.trades) >= 20 and avg > 0:
                        candidates.append((metrics["sharpe"], long, short, exit_name, conflicts))
            if not candidates:
                continue
            _, long, short, exit_name, train_conflicts = max(candidates, key=lambda x: x[0])
            context, f_context = research.iloc[:hi].reset_index(drop=True), factors.iloc[:hi].reset_index(drop=True)
            g_context = {name: values[:hi] for name, values in gates.items()}
            result, target, _, test_conflicts = run_engine(context, long, short, exit_name, f_context, g_context)
            test_m = bar_metrics(result, lo, hi)
            test_trades = result.trades[(result.trades.entry_i >= lo) & (result.trades.entry_i < hi)].copy()
            if abs(target).max() > 1.0:
                raise RuntimeError("single-account target exceeded 1 oz")
            trade_pnl = test_trades.net_pnl.sum()
            equity_pnl = test_m["pnl"]
            # A trade may be open across the test boundary.  Its mark-to-market PnL is
            # deliberately kept in equity; completed trades must still reconcile globally.
            picks.append({"fold": fold["name"], "shape": shape, "window": f"{fold['test_start']}->{fold['test_end']}",
                          "signature": key(shape, long, short, exit_name), "long": component_key(long),
                          "short": component_key(short), "exit": exit_name, "test_pnl": round(equity_pnl, 2),
                          "test_sharpe": round(test_m["sharpe"], 3), "test_maxdd": round(test_m["maxdd"], 2),
                          "test_trades": len(test_trades),
                          "test_avg": round(test_trades.net_pnl.mean(), 2) if len(test_trades) else 0.0,
                          "completed_trade_pnl": round(trade_pnl, 2),
                          "conflicts": train_conflicts + test_conflicts})
            for row in exit_contributions(test_trades):
                contribution_rows.append({"fold": fold["name"], "shape": shape, **row})

    out = pd.DataFrame(picks)
    out.to_csv(CSV, index=False)
    lines = ["# Single-account stability attribution\n",
             f"- research only: {research.datetime_utc.iloc[0]} -> {research.datetime_utc.iloc[-1]}",
             f"- excluded and unread: consumed development set from {dev_start:%Y-%m-%d} onward.",
             "- shapes: long-only, short-only, and long-short; all use a 1 oz maximum, next-open execution, and $0.16/oz round-trip cost.",
             "- each fold selects on its training prefix only; all full-system exit comparisons use the event engine.\n",
             "## Fold-selected systems\n", table(out.drop(columns=["signature"]) if not out.empty else out), ""]
    if out.empty:
        lines += ["## Outcome\n", "No fold produced an eligible training system. No candidate.\n"]
    else:
        consensus = out.groupby(["shape", "signature"]).agg(
            selections=("fold", "count"), positive_folds=("test_pnl", lambda x: int((x > 0).sum())),
            trades=("test_trades", "sum"), completed_pnl=("completed_trade_pnl", "sum"),
            mean_sharpe=("test_sharpe", "mean"), mean_pnl=("test_pnl", "mean"),
        ).reset_index()
        consensus["avg_trade"] = consensus.completed_pnl / consensus.trades.replace(0, np.nan)
        eligible = consensus[(consensus.selections >= 3) & (consensus.positive_folds >= 3) &
                             (consensus.trades >= 100) & (consensus.avg_trade > 0)]
        component_occurrences = pd.concat([
            out.loc[out.long.notna(), ["fold", "long"]].rename(columns={"long": "component"}),
            out.loc[out.short.notna(), ["fold", "short"]].rename(columns={"short": "component"}),
        ]).drop_duplicates()
        components_seen = Counter(component_occurrences.component)
        component_table = pd.DataFrame([{"component": name, "training_selections": count}
                                        for name, count in components_seen.most_common()])
        drift = out.groupby(["shape", "exit"]).agg(selections=("fold", "count"),
                                                       positive_folds=("test_pnl", lambda x: int((x > 0).sum())),
                                                       mean_pnl=("test_pnl", "mean")).reset_index()
        contrib = pd.DataFrame(contribution_rows)
        contrib_table = (contrib.groupby(["shape", "contribution"]).agg(trades=("trades", "sum"), pnl=("pnl", "sum"),
                         costs=("costs", "sum")).reset_index() if not contrib.empty else contrib)
        lines += ["## Complete-specification consensus\n", table(consensus.drop(columns=["signature"])), "",
                  "## Component-level repetition (evidence only)\n", table(component_table), "",
                  "## Parameter drift\n", table(drift), "",
                  "## Test-trade contribution\n", table(contrib_table), ""]
        if eligible.empty:
            stable = component_table[component_table.training_selections >= 3]
            lines += ["## Outcome\n", "No static candidate: no complete specification met the 3/4 independent-selection, 3/4 positive-fold, and 100-trade gates.",
                      "Component repetition is descriptive evidence only and does not authorize a development diagnostic or capacity table.\n",
                      "## Stable component hypotheses (not candidates)\n", table(stable)]
        else:
            lines += ["## Outcome\n", "A complete specification met the research gates. It remains a research result; this script intentionally does not run the consumed development set.\n"]
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"saved {REPORT.relative_to(ROOT)} and {CSV.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
