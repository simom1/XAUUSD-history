"""Diagnose why the 15m nested walk-forward folds failed or passed.

Rebuilds each fold-selected system from report/single_account_fold_picks_15m.csv
(research-slice results only; the development segment is never read), replays it
over its selection context with the event engine, and decomposes the test block:

- monthly completed-trade PnL (entry-month attribution),
- exit-reason contributions (reversals labeled like the stability report),
- concentration: share of test PnL in the three best/worst trades.

Diagnostic only: nothing here selects, re-ranks, or authorizes a candidate.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
import pandas as pd

from analysis.combo_screening import build_gates, fold_list, holdout_split
from analysis.factor_screening import build_factors
from analysis.system_research import (LONG_FAMILY, SHORT_FAMILY, Component, bar_metrics,
                                      run_engine)

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "xauusd_15m_indicators.csv.gz"
PICKS = ROOT / "report" / "single_account_fold_picks_15m.csv"
REPORT = ROOT / "report" / "fold_diagnosis_15m.md"

BAR_SECONDS = 900
ANN = float(np.sqrt(96 * 252))
DIRECTIONS = {**LONG_FAMILY, **SHORT_FAMILY}


def parse_component(text: str) -> Component:
    side, factor, w, t, h, regime, session = text.split(":")
    return Component(side, factor, DIRECTIONS[factor], int(w[1:]), float(t[1:]),
                     int(h[1:]), regime, session)


def exit_contributions(trades: pd.DataFrame) -> pd.DataFrame:
    if trades.empty:
        return pd.DataFrame(columns=["exit", "trades", "pnl", "avg"])
    next_entry = trades["entry_i"].shift(-1)
    next_side = trades["side"].shift(-1)
    reversal = ((trades["exit_reason"] == "signal") & (trades["exit_i"] == next_entry) &
                (trades["side"] != next_side))
    labels = np.where(reversal, "signal_reversal", trades["exit_reason"])
    frame = trades.assign(exit=labels)
    return (frame.groupby("exit").agg(trades=("net_pnl", "size"), pnl=("net_pnl", "sum"),
                                      avg=("net_pnl", "mean")).reset_index())


def md_table(df: pd.DataFrame) -> str:
    return df.to_markdown(index=False, floatfmt=".2f") if not df.empty else "(none)"


def main() -> None:
    full = pd.read_csv(DATA)
    research_end, dev_start = holdout_split(full.timestamp.to_numpy(np.int64), 183)
    research = full.iloc[:research_end].reset_index(drop=True)
    folds = fold_list(research.timestamp.to_numpy(np.int64), len(research), 4, 183)
    picks = pd.read_csv(PICKS)

    lines = ["# 15m walk-forward fold diagnosis (research slice only)\n",
             f"- research: {research.datetime_utc.iloc[0]} -> {research.datetime_utc.iloc[-1]}; "
             f"development from {dev_start:%Y-%m-%d} never read.",
             "- rebuilds each fold-selected system from `single_account_fold_picks_15m.csv` and "
             "decomposes its test block: monthly completed-trade PnL, exit contributions, concentration.",
             "- diagnostic only: nothing here selects or re-ranks anything.\n"]

    for _, pick in picks.iterrows():
        fold = next(f for f in folds if f["name"] == pick["fold"])
        lo, hi = fold["test_lo"], fold["test_hi"]
        long = parse_component(pick["long"]) if isinstance(pick["long"], str) else None
        short = parse_component(pick["short"]) if isinstance(pick["short"], str) else None
        context, f_ctx = research.iloc[:hi].reset_index(drop=True), build_factors(
            research.iloc[:hi].reset_index(drop=True), fast_window=32)
        g_ctx = build_gates(research.iloc[:hi].reset_index(drop=True))
        result, _, _, conflicts = run_engine(context, long, short, pick["exit"], f_ctx, g_ctx,
                                             bar_seconds=BAR_SECONDS, ann=ANN)
        trades = result.trades[(result.trades.entry_i >= lo) & (result.trades.entry_i < hi)].copy()
        eq_m = bar_metrics(result, lo, hi, ann=ANN)
        month = pd.to_datetime(trades.entry_time, unit="s").dt.strftime("%Y-%m")
        monthly = (trades.assign(month=month).groupby("month")
                   .agg(trades=("net_pnl", "size"), pnl=("net_pnl", "sum")).reset_index())
        worst3 = float(trades.nsmallest(3, "net_pnl").net_pnl.sum()) if len(trades) else 0.0
        best3 = float(trades.nlargest(3, "net_pnl").net_pnl.sum()) if len(trades) else 0.0
        pnl = float(trades.net_pnl.sum()) if len(trades) else 0.0
        wr = (trades.net_pnl > 0).mean() * 100 if len(trades) else 0.0

        lines += [f"## {pick['fold']}  {pick['window']}  (exit `{pick['exit']}`)",
                  f"- long `{pick['long']}` / short `{pick['short']}`; train-prefix Sharpe {pick['train_sharpe']:.2f} (15m annualized).",
                  f"- test block: equity PnL ${eq_m['pnl']:+.2f}, 15m Sharpe {eq_m['sharpe']:.2f}, maxDD ${eq_m['maxdd']:.2f}, "
                  f"{len(trades)} completed trades, win rate {wr:.1f}%, completed-trade PnL ${pnl:+.2f}.",
                  f"- concentration: 3 worst trades ${worst3:+.2f} ({worst3 / pnl * 100 if pnl else 0:.0f}% of completed PnL), "
                  f"3 best ${best3:+.2f} ({best3 / pnl * 100 if pnl else 0:.0f}%).", "",
                  "### Monthly completed-trade PnL", md_table(monthly), "",
                  "### Exit contributions", md_table(exit_contributions(trades)), ""]

    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"saved {REPORT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
