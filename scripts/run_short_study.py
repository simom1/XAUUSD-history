# -*- coding: utf-8 -*-
"""Phase 2: Systematic short-side study.

Scans the SHORT_FAMILY_EXT neighborhood (5 factors x short x W x T x H),
walk-forward 4 folds, ranks candidates, then runs the top shorts on the
consumed holdout (2026-03->09, down regime) as a DEVELOPMENT insight set.

Usage:
  python scripts/run_short_study.py
  python scripts/run_short_study.py --short-gate trend_down,adx_strong
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import numpy as np
import pandas as pd

from backtest import BacktestConfig, BacktestEngine
from analysis.factor_screening import (
    ANN, OZ, Session, build_factors, pnl_from_path, rolling_z,
)
from analysis.combo_screening import (
    SHORT_FAMILY_EXT, build_gates, evaluate, flatten, fold_list,
    holdout_split, leg_masks, masks_from_spec, md_table, parse_spec,
    spec_string, walk_forward,
)

DATA = ROOT / "data" / "xauusd_5m_indicators.csv.gz"
REPORTS = ROOT / "report"


def build_short_cfgs(windows, thrs, holds) -> list[dict]:
    cfgs = []
    for fname in SHORT_FAMILY_EXT:
        for W in windows:
            for T in thrs:
                for H in holds:
                    cfgs.append({"kind": "single", "factor": fname,
                                 "side": "short", "win": W, "thr": T, "hold": H})
    return cfgs


def candidate_table(grid, folds, min_trades):
    ok = grid[grid["res_trades"] >= min_trades].copy()
    if ok.empty:
        return ok
    ok["pos_folds"] = [sum(r[f"{f['name']}_test_pnl"] > 0 for f in folds)
                       for _, r in ok.iterrows()]
    foldcols = [f"{f['name']}_test_sharpe" for f in folds]
    ok["wf_mean_sharpe"] = ok[foldcols].mean(axis=1)
    ok = ok[ok["res_avg"] > 0]
    ok = ok.sort_values(["pos_folds", "wf_mean_sharpe", "res_sharpe"],
                        ascending=False).reset_index(drop=True)
    return ok


def run_dev_holdout(spec, df_full, h_idx, gate_names=None):
    """Run one short spec on the consumed holdout as development insight."""
    n = len(df_full)
    df_h = df_full.iloc[h_idx:].reset_index(drop=True)
    n_h = len(df_h)
    ts_sec_h = df_h["timestamp"].to_numpy(dtype=np.int64)
    o = df_h["open"].to_numpy(float)
    c = df_h["close"].to_numpy(float)
    ses = Session(ts_sec_h)
    F = build_factors(df_full)
    cfg = parse_spec(spec)
    zget = lambda fn, W: rolling_z(F[fn], W)[h_idx:]
    short_gate = None
    if gate_names:
        gates = build_gates(df_full)
        gm = np.ones(n, dtype=bool)
        for gn in gate_names.split(","):
            gm &= gates[gn.strip()]
        short_gate = gm[h_idx:]
    ld, sd_ = masks_from_spec(cfg, zget, side_map=SHORT_FAMILY_EXT,
                              short_gate=short_gate)
    ev = evaluate(ld, sd_, cfg["hold"], ses, o, c, n_h, [])
    if ev is None:
        return None
    return ev["res"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--windows", type=int, nargs="+", default=[4032, 6048, 8640])
    ap.add_argument("--thrs", type=float, nargs="+", default=[1.25, 1.5, 1.75, 2.0])
    ap.add_argument("--holds", type=int, nargs="+", default=[24, 36, 84, 120])
    ap.add_argument("--folds", type=int, default=4)
    ap.add_argument("--fold-days", type=int, default=183)
    ap.add_argument("--holdout-days", type=int, default=183)
    ap.add_argument("--min-trades", type=int, default=120)
    ap.add_argument("--gate-fold", type=int, default=40)
    ap.add_argument("--short-gate", type=str, default=None)
    args = ap.parse_args()

    t0 = time.perf_counter()
    print(f"loading {DATA.name} ...")
    df = pd.read_csv(DATA)
    df_full = df.copy()
    ts_sec = df["timestamp"].to_numpy(dtype=np.int64)
    ts = pd.to_datetime(df["timestamp"], unit="s")
    h_idx, h_start = holdout_split(ts_sec, args.holdout_days)
    n_full = len(df)

    df = df.iloc[:h_idx].reset_index(drop=True)
    n = len(df)
    ts_sec = df["timestamp"].to_numpy(dtype=np.int64)
    ts_r = ts.iloc[:h_idx].reset_index(drop=True)
    o = df["open"].to_numpy(float)
    c = df["close"].to_numpy(float)
    print(f"full sample {ts.iloc[0]:%Y-%m-%d} -> {ts.iloc[-1]:%Y-%m-%d} ({n_full:,} bars)")
    print(f"DEV holdout (insight): {h_start:%Y-%m-%d} -> {ts.iloc[-1]:%Y-%m-%d} ({n_full - h_idx:,} bars)")
    print(f"research period: {ts_r.iloc[0]:%Y-%m-%d} -> {ts_r.iloc[-1]:%Y-%m-%d} ({n:,} bars)")
    folds = fold_list(ts_sec, n, args.folds, args.fold_days)
    for f in folds:
        print(f"  fold {f['name']}: test {f['test_start']} -> {f['test_end']}")
    ses = Session(ts_sec)

    print("\n[1] building factors + z-score cache ...")
    F = build_factors(df)
    zcache = {}
    def zget(fn, W):
        key = (fn, W)
        if key not in zcache:
            zcache[key] = rolling_z(F[fn], W)
        return zcache[key]

    short_gate = None
    if args.short_gate:
        gates = build_gates(df)
        short_gate = np.ones(n, dtype=bool)
        for gn in args.short_gate.split(","):
            short_gate &= gates[gn.strip()]
        print(f"    short gate: {args.short_gate} -> {short_gate.sum():,} of {n:,} bars")

    cfgs = build_short_cfgs(args.windows, args.thrs, args.holds)
    print(f"\n[2] short-side grid: {len(cfgs)} configs "
          f"({len(SHORT_FAMILY_EXT)} factors x {len(args.windows)} W x "
          f"{len(args.thrs)} T x {len(args.holds)} H, all side=short)")
    rows = []
    for i, cfg in enumerate(cfgs, 1):
        ld, sd_ = masks_from_spec(cfg, zget, side_map=SHORT_FAMILY_EXT,
                                  short_gate=short_gate)
        ev = evaluate(ld, sd_, cfg["hold"], ses, o, c, n, folds)
        if ev is None:
            continue
        base = dict(cfg)
        base["spec"] = spec_string(cfg)
        rows.append(flatten(base, ev, folds))
        if i % 80 == 0 or i == len(cfgs):
            print(f"    [{i:3d}/{len(cfgs)}] {cfg['factor']:20s} W{cfg['win']} T{cfg['thr']:g} H{cfg['hold']}")
    grid = pd.DataFrame(rows)
    suffix = "_gated" if args.short_gate else ""
    grid.to_csv(REPORTS / f"short_wf_results{suffix}.csv", index=False)
    print(f"    {len(grid)} evaluated -> short_wf_results{suffix}.csv")

    print("\n[3] walk-forward selection ...")
    picks, agg = walk_forward(grid, folds, args.gate_fold, zget, ses, o, c, n,
                              side_map=SHORT_FAMILY_EXT, short_gate=short_gate)
    if not agg.empty:
        print(f"    {agg.to_dict('records')[0]}")

    print("\n[4] ranking candidates ...")
    cand = candidate_table(grid, folds, args.min_trades)
    show_cols = ["spec", "res_sharpe", "res_pnl", "res_trades", "res_avg", "res_pf"]
    for f in folds:
        show_cols += [f"{f['name']}_test_sharpe", f"{f['name']}_test_pnl"]
    show_cols += ["pos_folds", "wf_mean_sharpe"]

    # engine confirmation of top 3
    conf_rows = []
    if not cand.empty:
        for i, (_, r) in enumerate(cand.head(3).iterrows(), 1):
            cfg = parse_spec(r["spec"])
            ld, sd_ = masks_from_spec(cfg, zget, side_map=SHORT_FAMILY_EXT,
                                      short_gate=short_gate)
            ev = evaluate(ld, sd_, cfg["hold"], ses, o, c, n, [])
            B = ev["_B"]
            tgtz = np.zeros(n)
            for (f_, e_, s_, last) in ev["_trades"]:
                tgtz[f_ - 1:last] = s_ * OZ
            cres = BacktestEngine(BacktestConfig()).run(df, tgtz, warmup_bars=0)
            eng_pnl = cres.equity[-1] - cres.config.initial_capital
            delta = abs(eng_pnl - float(B.sum()))
            conf_rows.append({"spec": r["spec"], "engine_pnl": round(eng_pnl, 0),
                              "delta": round(delta, 2), "pos_folds": int(r["pos_folds"])})
            print(f"    [{i}/3] {r['spec']:55s} delta ${delta:.2f}")

    # dev holdout insight for top 3
    dev_rows = []
    if not cand.empty:
        print("\n[5] dev holdout insight (2026-03->09, down regime) ...")
        for _, r in cand.head(3).iterrows():
            m = run_dev_holdout(r["spec"], df_full, h_idx, args.short_gate)
            if m:
                dev_rows.append({"spec": r["spec"], "dev_pnl": m["pnl"],
                                 "dev_trades": m["trades"], "dev_avg": m["avg_usd"],
                                 "dev_sharpe": m["sharpe"], "dev_pf": m["pf"]})
                print(f"    {r['spec']:55s} pnl ${m['pnl']:,.0f}  "
                      f"trades {m['trades']}  Sharpe {m['sharpe']}")

    # report
    L = ["# XAUUSD 5m - Short-Side Study\n"]
    L.append(f"- data: `{DATA.name}` ({n_full:,} bars)")
    L.append(f"- research: {ts_r.iloc[0]:%Y-%m-%d} -> {ts_r.iloc[-1]:%Y-%m-%d} ({n:,} bars)")
    L.append(f"- DEV holdout (insight, not judgment): {h_start:%Y-%m-%d} -> "
             f"{ts.iloc[-1]:%Y-%m-%d} ({n_full - h_idx:,} bars, down regime)")
    L.append(f"- factors: {list(SHORT_FAMILY_EXT.keys())}")
    L.append(f"- grid: W {args.windows}, T {args.thrs}, H {args.holds}, all side=short")
    if args.short_gate:
        L.append(f"- short gate: {args.short_gate}")
    L.append("\n## Walk-forward folds\n")
    L.append(md_table(pd.DataFrame(folds)[["name", "test_start", "test_end"]]))
    L.append("\n## Walk-forward simulation\n")
    if not agg.empty:
        L.append(md_table(agg) + "\n")
    if not picks.empty:
        L.append(md_table(picks) + "\n")
    L.append(f"\n## Candidate ranking (min {args.min_trades} trades, res_avg > 0)\n")
    if cand.empty:
        L.append("(none)\n")
    else:
        L.append(md_table(cand[show_cols].head(15)) + "\n")
    if conf_rows:
        L.append("## Engine confirmation (research slice)\n")
        L.append(md_table(pd.DataFrame(conf_rows)) + "\n")
    if dev_rows:
        L.append("## Dev holdout insight (2026-03->09, down regime)\n")
        L.append(md_table(pd.DataFrame(dev_rows)) + "\n")
        L.append("Note: the holdout is CONSUMED (used for the long-side judgment). "
                 "These short results are development insight, not independent judgment.\n")
    L.append("## Short-side factor logic\n")
    L.append("| factor | long-when | short trigger | logic |")
    L.append("|---|:---|---|---|")
    L.append("| minus_di_14 | low | z > +T | down-pressure dominant |")
    L.append("| aroon_down_25 | low | z > +T | fresh lows |")
    L.append("| aroon_up_25 | high | z < -T | no fresh highs -> decline |")
    L.append("| close_vs_ema200 | high | z < -T | below long MA |")
    L.append("| rsi_14 | low | z > +T | overbought reversal |")

    out = REPORTS / f"short_study{suffix}.md"
    out.write_text("\n".join(L) + "\n", encoding="utf-8")
    print(f"\nsaved: {out.relative_to(ROOT)}")
    print(f"total runtime: {time.perf_counter() - t0:.0f}s")


if __name__ == "__main__":
    main()
