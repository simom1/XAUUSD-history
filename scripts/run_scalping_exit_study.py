"""Scalping-exit study for the qualified XAUUSD entries (5m and 15m).

Question: does any scalping-style exit -- tight ATR stops, trailing stops,
trailing take-profits (arm-then-trail), breakeven stops, or short holds --
improve the risk-adjusted profile of entries that are already qualified?

Protocol (no manual picking, research slice only):
  A. Exit ladder: the pre-qualified top-3 long x top-3 short component pairs
     (walk-forward fast-path score on the research prefix) x the full 18-rule
     exit ladder, through the event engine.
  B. Short holds: the pinned locked-spec pair re-held at H6/H12/H24/H36/H84
     x a fixed exit subset (scalping = short holding time, not just stops).
  C. Cost sensitivity: the top-5 configs by Sharpe re-run at 0.30 and 0.50
     USD/oz round trip (scalping lives or dies on friction).
  D. Consumed development segment diagnostic for the overall winner only.
  E. 15-minute arm: the transferred locked-spec pair through the same ladder
     plus a hold sweep.

Preregistered verdict rule: the scalping thesis is confirmed only if at least
3 of the 9 pairs in phase A improve research Sharpe by >= +0.2 over their own
`none` baseline without lower PnL.  Anything else is "no adapted strategy".
"""
from __future__ import annotations

import sys
from dataclasses import replace
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
import pandas as pd

from analysis.combo_screening import build_gates, holdout_split
from analysis.factor_screening import build_factors
from analysis.system_research import EXITS, Component, run_engine
from scripts.run_single_account_research import top_components

ROOT = Path(__file__).resolve().parents[1]
DATA_5M = ROOT / "data" / "xauusd_5m_indicators.csv.gz"
DATA_15M = ROOT / "data" / "xauusd_15m_indicators.csv.gz"
REPORT = ROOT / "report" / "scalping_exit_study.md"
CSV = ROOT / "report" / "scalping_exit_study.csv"
CSV_15M = ROOT / "report" / "scalping_exit_study_15m.csv"

ALL_EXITS = tuple(name for name, _ in EXITS)
HOLD_EXITS = ("none", "trail1", "trail2", "trailtp10", "be10_trail3", "stop1_5_trail2")
MIN_TRADES = 150
DELTA_SHARPE = 0.2

ANN_5M = float(np.sqrt(288 * 252))
ANN_15M = float(np.sqrt(96 * 252))
# run_engine computes bar Sharpe with the 5m annualization constant; rescale
# for 15m runs instead of duplicating the metric code.
SC15 = float(np.sqrt(96 / 288))

L5 = Component("long", "plus_di_14", "high", 6048, 2.0, 84, "none", "new_york")
S5 = Component("short", "aroon_up_25", "high", 6048, 1.5, 84, "none", "london")
L15 = Component("long", "plus_di_14", "high", 2016, 2.0, 28, "none", "new_york")
S15 = Component("short", "aroon_up_25", "high", 2016, 1.5, 28, "none", "london")


def trade_stats(t: pd.DataFrame) -> dict:
    if t.empty:
        return {"trades": 0, "wr": np.nan, "pf": np.nan, "avg_hold": 0.0, "med_hold": 0,
                "worst": 0.0, "n_trail": 0, "n_stop": 0, "n_be": 0, "n_tp": 0, "n_sess": 0}
    wins = float(t.loc[t.net_pnl > 0, "net_pnl"].sum())
    losses = float(-t.loc[t.net_pnl < 0, "net_pnl"].sum())
    er = t.exit_reason.value_counts()
    return {"trades": int(len(t)),
            "wr": round(float((t.net_pnl > 0).mean() * 100), 1),
            "pf": round(wins / losses, 3) if losses > 0 else np.inf,
            "avg_hold": round(float(t.bars_held.mean()), 1),
            "med_hold": int(t.bars_held.median()),
            "worst": round(float(t.net_pnl.min()), 2),
            "n_trail": int(er.get("trailing_stop", 0)), "n_stop": int(er.get("stop_loss", 0)),
            "n_be": int(er.get("breakeven", 0)), "n_tp": int(er.get("take_profit", 0)),
            "n_sess": int(er.get("session", 0))}


def evaluate(df, factors, gates, long_c, short_c, exit_name, bar_seconds=300,
             hold=None, cost=None) -> dict:
    lc = replace(long_c, hold=hold) if hold else long_c
    sc = replace(short_c, hold=hold) if hold else short_c
    result, _, m, _ = run_engine(df, lc, sc, exit_name, factors, gates,
                                 bar_seconds=bar_seconds, round_trip_cost=cost)
    sharpe = m["sharpe"] * (SC15 if bar_seconds == 900 else 1.0)
    row = {"exit": exit_name, "pnl": round(m["pnl"], 2), "sharpe": round(sharpe, 3),
           "maxdd": round(m["maxdd"], 2)}
    if hold:
        row["hold"] = hold
    row.update(trade_stats(result.trades))
    return row


def md_table(frame: pd.DataFrame) -> str:
    cols = list(frame.columns)
    lines = ["| " + " | ".join(cols) + " |", "|" + "|".join("---:" for _ in cols) + "|"]
    for _, row in frame.iterrows():
        lines.append("| " + " | ".join(str(row[c]) for c in cols) + " |")
    return "\n".join(lines)


def resolve_legs(cfg: str, longs, shorts):
    """'long-key + short-key|exit' or 'locked5|H<bars>|exit' -> (long, short, exit)."""
    parts = cfg.split("|")
    if parts[0] == "locked5":
        hold = int(parts[1][1:])
        return replace(L5, hold=hold), replace(S5, hold=hold), parts[2]
    lp, sp = parts[0].split(" + ")
    lc = next(c["component"] for c in longs if c["component"].key == lp)
    sc = next(c["component"] for c in shorts if c["component"].key == sp)
    return lc, sc, parts[1]


def main():
    lines = ["# Scalping-exit study (0.01 lot = 1 oz)\n"]
    full5 = pd.read_csv(DATA_5M)
    h, dev_start = holdout_split(full5.timestamp.to_numpy("int64"), 183)
    research5 = full5.iloc[:h].reset_index(drop=True)
    dev5 = full5.iloc[h:].reset_index(drop=True)
    f5, g5 = build_factors(research5), build_gates(research5)

    # ---------- Phase A: exit ladder on the pre-qualified pairs ----------
    longs = top_components(research5, f5, g5, "long")
    shorts = top_components(research5, f5, g5, "short")
    print("top longs:  ", [c["component"].key for c in longs])
    print("top shorts: ", [c["component"].key for c in shorts])
    rows = []
    for lp in longs:
        for sp in shorts:
            for exit_name in ALL_EXITS:
                row = evaluate(research5, f5, g5, lp["component"], sp["component"], exit_name)
                row["pair"] = f"{lp['component'].key} + {sp['component'].key}"
                rows.append(row)
                print(f"A {row['pair'][:44]:44s} {exit_name:15s} pnl={row['pnl']:+9.2f} "
                      f"sharpe={row['sharpe']:+.3f} trades={row['trades']}")
    outA = pd.DataFrame(rows)[["pair"] + [c for c in rows[0] if c != "pair"]]
    none_ref = outA[outA.exit == "none"].set_index("pair")
    elig = outA[outA.trades >= MIN_TRADES]
    best = elig.sort_values("sharpe", ascending=False).groupby("pair").head(1).copy()
    best["d_sharpe"] = (best["pair"].map(none_ref["sharpe"]).rsub(best["sharpe"]).round(3))
    best["d_pnl"] = (best["pair"].map(none_ref["pnl"]).rsub(best["pnl"]).round(2))
    confirmed = int(((best["d_sharpe"] >= DELTA_SHARPE) & (best["d_pnl"] >= 0)).sum())
    outA.to_csv(CSV, index=False)

    lines += ["\n## Phase A -- exit ladder on the top-3x3 pairs (research slice)\n",
              f"- exits: {', '.join(ALL_EXITS)}",
              f"- selection gate (preregistered): >= {MIN_TRADES} trades; scalping thesis "
              f"confirmed only if >= 3 of 9 pairs gain >= +{DELTA_SHARPE} Sharpe over their "
              "own `none` baseline without lower PnL.\n",
              "### Best exit per pair vs `none`\n",
              md_table(best[["pair", "exit", "pnl", "sharpe", "maxdd", "trades", "wr", "pf",
                             "avg_hold", "med_hold", "worst", "n_trail", "n_stop", "n_be",
                             "n_tp", "d_sharpe", "d_pnl"]]),
              f"\n**Pairs confirming the thesis: {confirmed} / 9.**\n"]

    # ---------- Phase B: short holds on the pinned locked-spec pair ----------
    rows = []
    for hold in (6, 12, 24, 36, 84):
        for exit_name in HOLD_EXITS:
            row = evaluate(research5, f5, g5, L5, S5, exit_name, hold=hold)
            rows.append(row)
            print(f"B hold={hold:3d} {exit_name:15s} pnl={row['pnl']:+9.2f} "
                  f"sharpe={row['sharpe']:+.3f} trades={row['trades']}")
    outB = pd.DataFrame(rows)
    lines += ["\n## Phase B -- short holds on the locked-spec pair (5m)\n",
              "- pair: `long:plus_di_14:W6048:T2:H*:new_york` + "
              "`short:aroon_up_25:W6048:T1.5:H*:london`\n",
              md_table(outB)]

    # ---------- Phase C: cost sensitivity on the top-5 configs ----------
    pool = pd.concat([best.assign(cfg=best["pair"] + "|" + best["exit"]),
                      outB.assign(cfg="locked5|H" + outB["hold"].astype(str) + "|" + outB["exit"])])
    pool = pool[pool.trades >= MIN_TRADES].sort_values("sharpe", ascending=False).head(5)
    lines += ["\n## Phase C -- cost sensitivity (top-5 configs by Sharpe)\n",
              "| config | cost | pnl | sharpe | trades |", "|---|---:|---:|---:|---:|"]
    pool_rows = []
    for _, r in pool.iterrows():
        lc, sc, ex = resolve_legs(r["cfg"], longs, shorts)
        for cost in (0.16, 0.30, 0.50):
            row = evaluate(research5, f5, g5, lc, sc, ex, cost=cost)
            pool_rows.append(row)
            lines.append(f"| {r['cfg']} | {cost:.2f} | {row['pnl']:+.2f} | "
                         f"{row['sharpe']:+.3f} | {row['trades']} |")
            print(f"C {r['cfg'][:44]:44s} cost={cost:.2f} pnl={row['pnl']:+9.2f} "
                  f"sharpe={row['sharpe']:+.3f}")
    outC = pd.DataFrame(pool_rows)

    # ---------- Phase D: dev diagnostic for the overall winner ----------
    lc, sc, ex_best = resolve_legs(pool.iloc[0]["cfg"], longs, shorts)
    dev_f, dev_g = build_factors(dev5), build_gates(dev5)
    lines += ["\n## Phase D -- consumed development diagnostic (never selects)\n"]
    for exit_name in dict.fromkeys((ex_best, "none")):
        r, _, m, _ = run_engine(dev5, lc, sc, exit_name, dev_f, dev_g)
        ts = trade_stats(r.trades)
        lines.append(f"- `{exit_name}`: PnL ${m['pnl']:+,.2f}, Sharpe {m['sharpe']:+.2f}, "
                     f"maxDD ${m['maxdd']:,.2f}, {ts['trades']} trades")
        print(f"D dev {exit_name:15s} pnl={m['pnl']:+9.2f} sharpe={m['sharpe']:+.3f}")

    # ---------- Phase E: 15-minute arm ----------
    full15 = pd.read_csv(DATA_15M)
    h15, _ = holdout_split(full15.timestamp.to_numpy("int64"), 183)
    research15 = full15.iloc[:h15].reset_index(drop=True)
    f15, g15 = build_factors(research15, fast_window=32), build_gates(research15)
    rows = []
    for exit_name in ALL_EXITS:
        rows.append(evaluate(research15, f15, g15, L15, S15, exit_name, bar_seconds=900))
    for hold in (4, 8, 12):
        for exit_name in HOLD_EXITS:
            rows.append(evaluate(research15, f15, g15, L15, S15, exit_name,
                                 bar_seconds=900, hold=hold))
    outE = pd.DataFrame(rows)
    outE.to_csv(CSV_15M, index=False)
    lines += ["\n## Phase E -- 15-minute transferred locked-spec pair\n",
              "- pair: `long:plus_di_14:W2016:T2:H*:new_york` + "
              "`short:aroon_up_25:W2016:T1.5:H*:london`; Sharpe annualized by sqrt(96*252)\n",
              md_table(outE)]

    lines += ["\n## Interpretation\n"]
    if confirmed >= 3:
        lines.append(f"- The scalping thesis is CONFIRMED on the entry set: {confirmed}/9 pairs "
                     "improve Sharpe by >= +0.2 with the best ladder exit.")
    else:
        lines.append(f"- The scalping thesis is REJECTED on the entry set: only {confirmed}/9 "
                     "pairs improve Sharpe by >= +0.2 over their own no-exit baseline.")
    top1 = best.iloc[0]
    lines.append(f"- Best single config: `{top1['pair']}` + `{top1['exit']}` "
                 f"(Sharpe {top1['sharpe']:+.2f}, PnL ${top1['pnl']:+,.2f}, "
                 f"{int(top1['trades'])} trades, avg hold {top1['avg_hold']} bars).")
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"saved {REPORT.relative_to(ROOT)}, {CSV.relative_to(ROOT)}, {CSV_15M.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
