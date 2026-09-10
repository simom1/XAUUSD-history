"""Detailed backtest report for the catastrophic-stop study winner with exit=none.

Reproduces the study selection (top-3 long x top-3 short by the walk-forward
fast-path score, max research Sharpe with >= 100 trades) and dumps a full
performance breakdown of the no-exit configuration: per-side stats, exit
reasons, trade distribution, monthly/yearly PnL, drawdown episodes and the
consumed development-segment diagnostic.
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
from analysis.system_research import OZ, run_engine
from scripts.run_single_account_research import top_components

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "xauusd_5m_indicators.csv.gz"
REPORT = ROOT / "report" / "none_backtest_detail.md"
TRADES_CSV = ROOT / "report" / "none_backtest_trades.csv"

MIN_TRADES = 100
INITIAL = 10_000.0


def money(x: float) -> str:
    return f"${x:,.2f}"


def table(rows: list[dict]) -> str:
    cols = list(rows[0].keys())
    lines = ["| " + " | ".join(cols) + " |", "|" + "|".join("---:" for _ in cols) + "|"]
    for r in rows:
        lines.append("| " + " | ".join(str(r[c]) for c in cols) + " |")
    return "\n".join(lines)


def headline(result, label: str) -> list[dict]:
    t = result.trades
    wins = t[t.net_pnl > 0]
    losses = t[t.net_pnl <= 0]
    gross_win = float(wins.net_pnl.sum())
    gross_loss = float(losses.net_pnl.sum())
    from analysis.system_research import bar_metrics
    m = bar_metrics(result)
    years = len(result.equity) * 300 / (365.25 * 86400)
    total_ret = float(result.equity[-1] - INITIAL) / INITIAL
    cagr = (1.0 + total_ret) ** (1 / years) - 1 if years > 0 else 0.0
    return [
        {"metric": label, "value": ""},
        {"metric": "net PnL (1 oz)", "value": money(m["pnl"])},
        {"metric": "5m Sharpe (annualized)", "value": f"{m['sharpe']:.2f}"},
        {"metric": "max drawdown", "value": money(m["maxdd"])},
        {"metric": "return on $10k", "value": f"{total_ret:.1%}"},
        {"metric": "CAGR (calendar years)", "value": f"{cagr:.1%}"},
        {"metric": "closed trades", "value": str(len(t))},
        {"metric": "win rate", "value": f"{len(wins) / max(len(t), 1):.1%}"},
        {"metric": "profit factor", "value": f"{gross_win / abs(gross_loss):.2f}" if gross_loss else "inf"},
        {"metric": "avg win / avg loss", "value": f"{money(wins.net_pnl.mean() if len(wins) else 0)} / {money(losses.net_pnl.mean() if len(losses) else 0)}"},
        {"metric": "expectancy per trade", "value": money(float(t.net_pnl.mean()))},
        {"metric": "gross PnL / total costs", "value": f"{money(float(t.gross_pnl.sum()))} / {money(float(t.costs.sum()))}"},
        {"metric": "worst / best trade", "value": f"{money(float(t.net_pnl.min()))} / {money(float(t.net_pnl.max()))}"},
        {"metric": "avg bars held (median)", "value": f"{t.bars_held.mean():.0f} ({int(t.bars_held.median())})"},
        {"metric": "time in market", "value": f"{t.bars_held.sum() * 300 / (len(result.equity) * 300):.1%}"},
    ]


def side_breakdown(t: pd.DataFrame) -> list[dict]:
    rows = []
    for side, name in ((1, "long"), (-1, "short")):
        s = t[t.side == side]
        w = s[s.net_pnl > 0]
        rows.append({"side": name, "trades": len(s), "pnl": money(float(s.net_pnl.sum())),
                     "win_rate": f"{len(w) / max(len(s), 1):.1%}",
                     "avg_trade": money(float(s.net_pnl.mean())) if len(s) else "-",
                     "worst": money(float(s.net_pnl.min())) if len(s) else "-",
                     "avg_bars": f"{s.bars_held.mean():.0f}" if len(s) else "-"})
    return rows


def exit_reasons(t: pd.DataFrame) -> list[dict]:
    rows = []
    for reason, g in t.groupby("exit_reason"):
        rows.append({"exit_reason": reason, "trades": len(g),
                     "pnl": money(float(g.net_pnl.sum())),
                     "share_of_trades": f"{len(g) / len(t):.1%}",
                     "avg": money(float(g.net_pnl.mean()))})
    return sorted(rows, key=lambda r: r["trades"], reverse=True)


def distribution(t: pd.DataFrame) -> list[dict]:
    qs = (0.01, 0.05, 0.25, 0.50, 0.75, 0.95, 0.99)
    return [{"quantile": f"p{int(q * 100)}", "net_pnl": money(float(np.quantile(t.net_pnl, q)))}
            for q in qs]


def hourly(t: pd.DataFrame) -> list[dict]:
    hours = pd.to_datetime(t.entry_time, unit="s", utc=True).dt.hour
    rows = []
    for h, g in t.groupby(hours):
        rows.append({"utc_hour": f"{h:02d}:00", "trades": len(g),
                     "pnl": money(float(g.net_pnl.sum())),
                     "avg": money(float(g.net_pnl.mean()))})
    return rows


def monthly(t: pd.DataFrame) -> list[dict]:
    m = pd.to_datetime(t.exit_time, unit="s", utc=True).dt.to_period("M").astype(str)
    rows = []
    for key, g in t.groupby(m):
        w = g[g.net_pnl > 0]
        rows.append({"month": key, "pnl": money(float(g.net_pnl.sum())), "trades": len(g),
                     "win_rate": f"{len(w) / max(len(g), 1):.0%}"})
    return rows


def yearly(t: pd.DataFrame) -> list[dict]:
    y = pd.to_datetime(t.exit_time, unit="s", utc=True).dt.year
    rows = []
    for key, g in t.groupby(y):
        w = g[g.net_pnl > 0]
        rows.append({"year": str(key), "pnl": money(float(g.net_pnl.sum())), "trades": len(g),
                     "win_rate": f"{len(w) / max(len(g), 1):.0%}",
                     "worst_trade": money(float(g.net_pnl.min()))})
    return rows


def drawdowns(result) -> list[dict]:
    eq = result.equity
    ts = pd.to_datetime(result.timestamps, unit="s", utc=True)
    dd = eq - np.maximum.accumulate(eq)
    episodes, in_ep, start = [], False, 0
    for i, d in enumerate(dd):
        if d < 0 and not in_ep:
            in_ep, start = True, i
        elif d >= 0 and in_ep:
            in_ep = False
            seg = dd[start:i]
            t = int(np.argmin(seg)) + start
            episodes.append({"peak": ts[start], "trough": ts[t], "depth": float(seg.min()), "bars": i - start})
    if in_ep:
        seg = dd[start:]
        t = int(np.argmin(seg)) + start
        episodes.append({"peak": ts[start], "trough": ts[t], "depth": float(seg.min()), "bars": len(dd) - start})
    episodes.sort(key=lambda e: e["depth"])
    return [{"peak": str(e["peak"]), "trough": str(e["trough"]),
             "depth": money(e["depth"]), "length_days": f"{e['bars'] * 300 / 86400:.1f}"}
            for e in episodes[:5]]


def worst_best(t: pd.DataFrame, n: int = 5) -> list[dict]:
    cols = {"entry": "entry_time", "exit": "exit_time", "side": "side", "entry_px": "entry_px",
            "exit_px": "exit_px", "exit_reason": "exit_reason", "net_pnl": "net_pnl"}
    def fmt(g: pd.DataFrame) -> list[dict]:
        rows = []
        for _, r in g.iterrows():
            rows.append({"entry": str(pd.to_datetime(r.entry_time, unit="s", utc=True)),
                         "exit": str(pd.to_datetime(r.exit_time, unit="s", utc=True)),
                         "side": "long" if r.side == 1 else "short",
                         "entry_px": f"{r.entry_px:.2f}", "exit_px": f"{r.exit_px:.2f}",
                         "exit_reason": r.exit_reason, "net_pnl": money(r.net_pnl)})
        return rows
    return fmt(t.nsmallest(n, "net_pnl")) + fmt(t.nlargest(n, "net_pnl"))


def main():
    full = pd.read_csv(DATA)
    h, _ = holdout_split(full.timestamp.to_numpy("int64"), 183)
    research = full.iloc[:h].reset_index(drop=True)
    dev = full.iloc[h:].reset_index(drop=True)

    factors, gates = build_factors(research), build_gates(research)
    longs = top_components(research, factors, gates, "long")
    shorts = top_components(research, factors, gates, "short")

    best, best_sharpe = None, -np.inf
    for lp in longs:
        for sp in shorts:
            _, _, m, _ = run_engine(research, lp["component"], sp["component"], "none", factors, gates)
            if m["sharpe"] > best_sharpe:
                best, best_sharpe = (lp, sp), m["sharpe"]
    lp, sp = best
    result, target, m, conflicts = run_engine(research, lp["component"], sp["component"], "none", factors, gates)
    t = result.trades
    print(f"selected: {lp['component'].key} + {sp['component'].key}  sharpe={m['sharpe']:.2f} pnl={m['pnl']:.2f}")

    # export the trade log
    exp = t[["entry_time", "exit_time", "side", "oz", "entry_px", "exit_px", "entry_reason",
             "exit_reason", "gross_pnl", "costs", "net_pnl", "bars_held"]].copy()
    for c in ("entry_time", "exit_time"):
        exp[c] = pd.to_datetime(exp[c], unit="s", utc=True)
    exp["side"] = exp["side"].map({1: "long", -1: "short"})
    exp.to_csv(TRADES_CSV, index=False)

    dev_f, dev_g = build_factors(dev), build_gates(dev)
    dev_res, _, dev_m, _ = run_engine(dev, lp["component"], sp["component"], "none", dev_f, dev_g)

    lines = [
        "# Detailed backtest report -- no-exit candidate (0.01 lot = 1 oz)\n",
        f"- long component: `{lp['component'].key}`",
        f"- short component: `{sp['component'].key}`",
        f"- exit: `none` (hold to hold-based expiry, then daily session flat; no stop/target/trail)",
        f"- research: {research.datetime_utc.iloc[0]} -> {research.datetime_utc.iloc[-1]} ({len(research)} bars)",
        f"- consumed development segment (diagnostic only): {dev.datetime_utc.iloc[0]} -> {dev.datetime_utc.iloc[-1]}",
        f"- accounting: {INITIAL:,.0f} capital, fills at next open mid, all-in round-trip cost $0.16/oz, "
        f"5m Sharpe annualized by sqrt(288x252), conflicts {conflicts}",
        f"- trade log: `{TRADES_CSV.relative_to(ROOT)}` ({len(t)} closed trades)\n",
        "## Headline (research)\n", table(headline(result, "")), "",
        "## Per side\n", table(side_breakdown(t)), "",
        "## Exit reasons\n", table(exit_reasons(t)), "",
        "## Trade PnL distribution (1 oz)\n", table(distribution(t)), "",
        "## Worst / best trades\n", table(worst_best(t)), "",
        "## Entry hour (UTC) PnL\n", table(hourly(t)), "",
        "## Monthly PnL (realized at exit)\n", table(monthly(t)), "",
        "## Yearly summary\n", table(yearly(t)), "",
        "## Top-5 drawdown episodes\n", table(drawdowns(result)), "",
        "## Consumed development segment (diagnostic only -- never selects anything)\n",
    ]
    lines.append(table(headline(dev_res, "")))
    dt = dev_res.trades
    lines += ["", f"- stop-exit events: {int((dt.exit_reason == 'stop_loss').sum())} "
              f"(the `none` exit has no stop; this row is 0 by construction)"]
    lines += ["\n## Reading notes\n",
              "- Per-side and hourly tables use realized trade PnL (net of the all-in cost).",
              "- Monthly attribution uses the exit time; a trade spanning a month boundary lands entirely in its exit month.",
              "- The development segment is already consumed: its numbers may not be used to pick or justify anything. "
              "The next legitimate evaluation is a single pass on >= 6 months of new data.\n"]
    REPORT.write_text("\n".join(lines), encoding="utf-8")
    print(f"saved {REPORT.relative_to(ROOT)} and {TRADES_CSV.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
