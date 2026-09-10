# -*- coding: utf-8 -*-
"""Combination matrix + walk-forward selection for the surviving factors.

Research mode (default):
  0. exclude the last --holdout-days as a consumed development segment
  1. calibrate the fast accounting vs the real engine on the research slice
  2. survivor neighborhood grid: 4 factors x {long, short} x W x T x H
  3. combination matrix: all pairwise AND-confirmed longs x W x T x H
  4. walk-forward simulation: per fold pick best train-Sharpe config, apply
     to the untouched test fold, aggregate the fold equity per pool
  5. rank candidates by fold consistency -> report/combo_matrix.md

Final-judgment mode (--final SPEC):
  evaluate one locked config on the consumed development segment with fast + engine
  accounting. Run this once, after research is frozen.

Usage:
  python scripts/run_combo_matrix.py [--folds 4] [--confirm 4]
  python scripts/run_combo_matrix.py --final "single|aroon_up_25|long|W6048|T1.5|H84"
"""
from __future__ import annotations

import argparse
import sys
import time
from itertools import combinations
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import numpy as np
import pandas as pd

from backtest import BacktestConfig, BacktestEngine
from strategies import EmaCrossStrategy
from analysis.factor_screening import (
    ANN, OZ, Session, build_factors, path_from_targets, pnl_from_path,
    rolling_z,
)
from analysis.combo_screening import (
    SURVIVORS, build_gates, evaluate, flatten, fold_list, holdout_split,
    leg_masks, masks_from_spec, md_table, parse_spec, spec_string, walk_forward,
)

DATA = ROOT / "data" / "xauusd_5m_indicators.csv.gz"
REPORTS = ROOT / "report"


def build_cfg_list(args) -> list[dict]:
    cfgs: list[dict] = []
    for fname in SURVIVORS:
        for W in args.windows:
            for T in args.thrs:
                for side in ("long", "short"):
                    for H in args.holds:
                        cfgs.append({"kind": "single", "factor": fname, "side": side,
                                     "win": W, "thr": T, "hold": H})
    for fa, fb in combinations(SURVIVORS, 2):
        for W in args.windows:
            for T in args.thrs:
                for H in args.holds:
                    cfgs.append({"kind": "combo", "factor": f"{fa}+{fb}", "side": "long",
                                 "win": W, "thr": T, "hold": H})
    return cfgs


def run_grid(cfgs, zget, ses, o, c, n, folds, progress: bool = True,
             long_gate=None, short_gate=None,
             atr=None, stop_atr=None, trail_atr=None, target_atr=None):
    rows = []
    total = len(cfgs)
    for i, cfg in enumerate(cfgs, 1):
        ld, sd_ = masks_from_spec(cfg, zget, long_gate=long_gate,
                                  short_gate=short_gate)
        ev = evaluate(ld, sd_, cfg["hold"], ses, o, c, n, folds, atr,
                      stop_atr, trail_atr, target_atr)
        if ev is None:
            continue
        base = dict(cfg)
        base["spec"] = spec_string(cfg)
        rows.append(flatten(base, ev, folds))
        if progress and (i % 96 == 0 or i == total):
            print(f"    [{i:3d}/{total}] {cfg['factor']:36s} {cfg['side']:5s} "
                  f"W{cfg['win']} T{cfg['thr']:g} H{cfg['hold']}")
    return pd.DataFrame(rows)


def candidate_table(grid: pd.DataFrame, folds, min_trades: int) -> pd.DataFrame:
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


def run_final(spec: str, holdout_days: int, gate_names: str | None = None,
              dev: bool = False) -> None:
    """Judgment day: evaluate one locked spec on the sealed holdout.

    With --dev the holdout is treated as a DEVELOPMENT set (insight only,
    not judgment) - used after the holdout is consumed to test new ideas
    (regime gates, short side, stop-loss) on the known down regime."""
    print(f"loading {DATA.name} ...")
    df = pd.read_csv(DATA)
    ts_sec = df["timestamp"].to_numpy(dtype=np.int64)
    h_idx, h_start = holdout_split(ts_sec, holdout_days)
    n = len(df)
    ts = pd.to_datetime(df["timestamp"], unit="s")
    tag = "DEV (insight only)"
    print(f"full sample {ts.iloc[0]:%Y-%m-%d} -> {ts.iloc[-1]:%Y-%m-%d} ({n:,} bars)")
    print(f"{tag} holdout: {h_start:%Y-%m-%d} -> {ts.iloc[-1]:%Y-%m-%d} "
          f"({n - h_idx:,} bars)\n")

    df_h = df.iloc[h_idx:].reset_index(drop=True)
    n_h = len(df_h)
    ts_sec_h = df_h["timestamp"].to_numpy(dtype=np.int64)
    o = df_h["open"].to_numpy(float)
    c = df_h["close"].to_numpy(float)
    ses = Session(ts_sec_h)

    F = build_factors(df)                      # causal indicators: slice is valid
    cfg = parse_spec(spec)
    zget = lambda fn, W: rolling_z(F[fn], W)[h_idx:]

    long_gate = short_gate = None
    if gate_names:
        gates = build_gates(df)
        gm = np.ones(n, dtype=bool)
        for gn in gate_names.split(","):
            gm &= gates[gn.strip()]
        long_gate = gm[h_idx:]
        print(f"gate: {gate_names} -> {long_gate.sum():,} of {n_h:,} bars allow long\n")

    ld, sd_ = masks_from_spec(cfg, zget, long_gate=long_gate)
    ev = evaluate(ld, sd_, cfg["hold"], ses, o, c, n_h, [])
    if ev is None:
        print("no trades triggered on the holdout for this spec")
        return
    B = ev["_B"]
    m = ev["res"]
    print(f"spec: {spec}")
    print(f"fast accounting : pnl ${m['pnl']:,.0f}  trades {m['trades']}  "
          f"avg ${m['avg_usd']:+,.2f}/trade  PF {m['pf']}  Sharpe {m['sharpe']}  "
          f"maxDD ${m['maxdd']:,.0f}")

    tgtz = np.zeros(n_h)
    for (f, e, s_, last) in ev["_trades"]:
        tgtz[f - 1:last] = s_ * OZ
    res = BacktestEngine(BacktestConfig()).run(df_h, tgtz, warmup_bars=0)
    eng = res.equity[-1] - res.config.initial_capital
    print(f"engine accounting: pnl ${eng:,.0f}  trades {len(res.trades)}  "
          f"delta vs fast ${abs(eng - float(B.sum())):,.2f}")
    if dev:
        verdict = "DEV-INSIGHT" + (" (would PASS)" if m["pnl"] > 0 else " (still negative)")
    else:
        verdict = "DEV-INSIGHT (not a validation verdict)"
    print(f"\nDEVELOPMENT RESULT: {verdict}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--windows", type=int, nargs="+", default=[4032, 6048, 8640])
    ap.add_argument("--thrs", type=float, nargs="+", default=[1.25, 1.5, 1.75, 2.0])
    ap.add_argument("--holds", type=int, nargs="+", default=[24, 36, 84, 120])
    ap.add_argument("--folds", type=int, default=4)
    ap.add_argument("--fold-days", type=int, default=183)
    ap.add_argument("--holdout-days", type=int, default=183)
    ap.add_argument("--min-trades-single", type=int, default=120)
    ap.add_argument("--min-trades-combo", type=int, default=50)
    ap.add_argument("--gate-fold-single", type=int, default=40)
    ap.add_argument("--gate-fold-combo", type=int, default=20)
    ap.add_argument("--confirm", type=int, default=4)
    ap.add_argument("--skip-confirm", action="store_true")
    ap.add_argument("--final", type=str, default=None,
                    help="evaluates a spec on the consumed development segment")
    ap.add_argument("--gate", type=str, default=None,
                    help="comma-separated long regime gates: trend_up,adx_strong,not_choppy,aroon_up")
    ap.add_argument("--short-gate", type=str, default=None,
                    help="comma-separated short regime gates: trend_down,adx_strong,aroon_dn")
    ap.add_argument("--dev", action="store_true",
                    help="treat holdout as development set (insight, not judgment)")
    ap.add_argument("--stop-atr", type=float, default=None,
                    help="ATR stop-loss multiplier (e.g. 2.0 = exit at -2x ATR14)")
    ap.add_argument("--trail-atr", type=float, default=None,
                    help="ATR trailing-stop multiplier")
    ap.add_argument("--target-atr", type=float, default=None,
                    help="ATR profit-target multiplier")
    args = ap.parse_args()

    if args.final:
        run_final(args.final, args.holdout_days, args.gate, args.dev)
        return

    t0 = time.perf_counter()
    print(f"loading {DATA.name} ...")
    df = pd.read_csv(DATA)
    ts_sec = df["timestamp"].to_numpy(dtype=np.int64)
    ts = pd.to_datetime(df["timestamp"], unit="s")
    h_idx, h_start = holdout_split(ts_sec, args.holdout_days)
    n_full = len(df)

    # ---------------- stage 0: exclude consumed development data ----------------
    df = df.iloc[:h_idx].reset_index(drop=True)
    n = len(df)
    ts_sec = df["timestamp"].to_numpy(dtype=np.int64)
    ts_r = ts.iloc[:h_idx].reset_index(drop=True)
    o = df["open"].to_numpy(float)
    c = df["close"].to_numpy(float)
    print(f"full sample {ts.iloc[0]:%Y-%m-%d} -> {ts.iloc[-1]:%Y-%m-%d} ({n_full:,} bars)")
    print(f"consumed development set (excluded): {h_start:%Y-%m-%d} -> {ts.iloc[-1]:%Y-%m-%d} "
          f"({n_full - h_idx:,} bars)")
    print(f"research period: {ts_r.iloc[0]:%Y-%m-%d} -> {ts_r.iloc[-1]:%Y-%m-%d} ({n:,} bars)")
    folds = fold_list(ts_sec, n, args.folds, args.fold_days)
    for f in folds:
        print(f"  fold {f['name']}: test {f['test_start']} -> {f['test_end']} "
              f"({f['test_hi'] - f['test_lo']:,} bars), train prefix {f['train_hi']:,} bars")
    ses = Session(ts_sec)

    # ---------------- stage 1: calibration on research slice ----------------
    print("\n[1] calibrating fast accounting vs engine on the research slice (EMA 9/21) ...")
    strat = EmaCrossStrategy(9, 21)
    tgt = strat.targets(df)
    res = BacktestEngine(BacktestConfig()).run(df, tgt, warmup_bars=strat.warmup_bars)
    eng_net = res.equity[-1] - res.config.initial_capital
    tgt[:strat.warmup_bars] = 0.0
    pos = path_from_targets(tgt, ses.blocked, ses.flat)
    fast_net = float(pnl_from_path(pos, o, c, ses.flat).sum())
    calib_ok = abs(eng_net - fast_net) < 1.0
    print(f"    engine net = ${eng_net:,.0f}   fast net = ${fast_net:,.0f}   "
          f"|delta| = ${abs(eng_net - fast_net):.4f}   -> {'OK' if calib_ok else 'MISMATCH!'}")
    if not calib_ok:
        raise SystemExit("fast accounting does not match the engine - aborting")

    # ---------------- stage 2+3: grids ----------------
    print("\n[2] building z-score cache ...")
    F = build_factors(df)
    zcache: dict[tuple[str, int], np.ndarray] = {}

    def zget(fn: str, W: int) -> np.ndarray:
        key = (fn, W)
        if key not in zcache:
            zcache[key] = rolling_z(F[fn], W)
        return zcache[key]

    # regime gates (Phase 1)
    long_gate = short_gate = None
    if args.gate or args.short_gate:
        gates = build_gates(df)
        if args.gate:
            long_gate = np.ones(n, dtype=bool)
            for gn in args.gate.split(","):
                long_gate &= gates[gn.strip()]
            print(f"    long gate: {args.gate} -> {long_gate.sum():,} of {n:,} bars")
        if args.short_gate:
            short_gate = np.ones(n, dtype=bool)
            for gn in args.short_gate.split(","):
                short_gate &= gates[gn.strip()]
            print(f"    short gate: {args.short_gate} -> {short_gate.sum():,} of {n:,} bars")

    cfgs = build_cfg_list(args)
    n_single = sum(1 for x in cfgs if x["kind"] == "single")
    n_combo = len(cfgs) - n_single
    print(f"\n[3] grid: {n_single} single-factor neighborhood + {n_combo} pairwise AND combos")

    # stop-loss / dynamic exit (Phase 3)
    atr_arr = None
    if args.stop_atr or args.trail_atr or args.target_atr:
        atr_arr = df["atr_14"].to_numpy(float)
        parts = []
        if args.stop_atr: parts.append(f"stop={args.stop_atr:g}")
        if args.trail_atr: parts.append(f"trail={args.trail_atr:g}")
        if args.target_atr: parts.append(f"target={args.target_atr:g}")
        print(f"    ATR stops: {', '.join(parts)} (atr_14)")

    grid = run_grid(cfgs, zget, ses, o, c, n, folds,
                    long_gate=long_gate, short_gate=short_gate,
                    atr=atr_arr, stop_atr=args.stop_atr,
                    trail_atr=args.trail_atr, target_atr=args.target_atr)
    suffix = "_gated" if (args.gate or args.short_gate) else ""
    if atr_arr is not None:
        suffix += "_stopped"
    grid.to_csv(REPORTS / f"combo_wf_results{suffix}.csv", index=False)
    print(f"    {len(grid)} evaluated configs -> combo_wf_results{suffix}.csv")

    # ---------------- stage 4: walk-forward simulation ----------------
    print("\n[4] walk-forward selection simulation ...")
    pools = {
        "singles": grid[grid["kind"] == "single"],
        "combos": grid[grid["kind"] == "combo"],
        "all": grid,
    }
    wf_tables, wf_aggs = {}, {}
    for pname, sub in pools.items():
        gate = args.gate_fold_single if pname == "singles" else \
            args.gate_fold_combo if pname == "combos" else \
            min(args.gate_fold_single, args.gate_fold_combo)
        picks, agg = walk_forward(sub, folds, gate, zget, ses, o, c, n,
                                  long_gate=long_gate, short_gate=short_gate,
                                  atr=atr_arr, stop_atr=args.stop_atr,
                                  trail_atr=args.trail_atr, target_atr=args.target_atr)
        wf_tables[pname], wf_aggs[pname] = picks, agg
        if not agg.empty:
            print(f"    {pname:8s}: {agg.to_dict('records')[0]}")

    # ---------------- stage 5: candidates + report ----------------
    print("\n[5] ranking candidates ...")
    cand_s = candidate_table(grid[grid["kind"] == "single"], folds, args.min_trades_single)
    cand_c = candidate_table(grid[grid["kind"] == "combo"], folds, args.min_trades_combo)

    # engine confirmation of the top candidates
    conf_rows = []
    if not args.skip_confirm:
        pool = pd.concat([cand_s.head(2), cand_c.head(2)]).drop_duplicates("spec")
        for i, (_, r) in enumerate(pool.iterrows(), 1):
            cfg = parse_spec(r["spec"])
            ld, sd_ = masks_from_spec(cfg, zget, long_gate=long_gate,
                                      short_gate=short_gate)
            ev = evaluate(ld, sd_, cfg["hold"], ses, o, c, n, [], atr_arr,
                          args.stop_atr, args.trail_atr, args.target_atr)
            B = ev["_B"]
            tgtz = np.zeros(n)
            for (f_, e_, s_, last) in ev["_trades"]:
                tgtz[f_ - 1:last] = s_ * OZ
            cres = BacktestEngine(BacktestConfig()).run(df, tgtz, warmup_bars=0)
            eng_pnl = cres.equity[-1] - cres.config.initial_capital
            delta = abs(eng_pnl - float(B.sum()))
            conf_rows.append({"spec": r["spec"], "engine_pnl": round(eng_pnl, 0),
                              "engine_trades": len(cres.trades),
                              "fast_pnl": round(float(B.sum()), 0),
                              "delta": round(delta, 2),
                              "res_sharpe": r["res_sharpe"], "pos_folds": int(r["pos_folds"])})
            print(f"    [{i}/{len(pool)}] {r['spec']:60s} delta ${delta:.2f}")

    show_cols = (lambda folds_: ["spec", "res_sharpe", "res_pnl", "res_trades",
                                 "res_avg", "res_pf"] +
                 [f"{f['name']}_test_sharpe" for f in folds_] +
                 [f"{f['name']}_test_trades" for f in folds_] + ["pos_folds", "wf_mean_sharpe"])

    L = []
    L.append("# XAUUSD 5m - Combination Matrix + Walk-Forward Report\n")
    L.append(f"- data: `{DATA.name}` ({n_full:,} bars, {ts.iloc[0]:%Y-%m-%d} -> {ts.iloc[-1]:%Y-%m-%d})")
    L.append(f"- **Consumed development set excluded: {h_start:%Y-%m-%d} -> {ts.iloc[-1]:%Y-%m-%d} "
             f"({n_full - h_idx:,} bars); it is not independent validation.**")
    L.append(f"- research period: {ts_r.iloc[0]:%Y-%m-%d} -> {ts_r.iloc[-1]:%Y-%m-%d} "
             f"({n:,} bars); the previous 70/30 OOS block is inside it")
    L.append(f"- cost model: all-in $0.16/oz round trip; 1 unit = {OZ:.0f} oz; "
             "grid: W " + str(args.windows) + ", T " + str(args.thrs) +
             ", H " + str(args.holds))
    L.append("\n## Walk-forward folds (expanding train, 6-month tests)\n")
    L.append(md_table(pd.DataFrame([{**f, "train_hi": f"{f['train_hi']:,}"}
                                    for f in folds])[["name", "test_start", "test_end",
                                                      "test_hi", "train_hi"]]))
    L.append("\n## Method\n")
    L.append(f"1. **Survivor neighborhood**: the 4 surviving factors x {{long, short}} x "
             f"W x T x H ({n_single} configs). Long = survivor direction "
             "(aroon_up_25/close_vs_ema200/plus_di_14 long@high, gap_pct long@low).")
    L.append(f"2. **Combination matrix**: all {n_combo} pairwise AND-confirmed longs - "
             "both factors must be in their trigger state on the same decision bar.")
    L.append(f"3. **Walk-forward simulation**: per fold, the best train-Sharpe config "
             f"(train trades >= gate, train avg > 0) is applied to the untouched test fold; "
             "fold equities are concatenated per pool.")
    L.append("4. **Candidate ranking**: positive-fold count, then mean fold-test Sharpe, "
             "then research Sharpe. The excluded development segment cannot be used for a pass/fail claim.")
    L.append("\n## Fast-model calibration (research slice)\n")
    L.append(f"EMA 9/21: engine ${eng_net:,.0f} vs fast ${fast_net:,.0f} - "
             f"delta ${abs(eng_net - fast_net):.4f}.\n")
    L.append("## Walk-forward simulation\n")
    for pname in pools:
        L.append(f"\n**pool = {pname}**\n")
        if wf_tables[pname].empty:
            L.append("(no config passed the fold gate)\n")
            continue
        L.append(md_table(wf_tables[pname]) + "\n")
        L.append(md_table(wf_aggs[pname]) + "\n")
    L.append("## Candidate ranking - singles (min "
             f"{args.min_trades_single} research trades, res_avg > 0)\n")
    if cand_s.empty:
        L.append("(none)\n")
    else:
        L.append(md_table(cand_s[show_cols(folds)].head(12)) + "\n")
    L.append("## Candidate ranking - AND combos (min "
             f"{args.min_trades_combo} research trades, res_avg > 0)\n")
    if cand_c.empty:
        L.append("(none)\n")
    else:
        L.append(md_table(cand_c[show_cols(folds)].head(12)) + "\n")
    if conf_rows:
        L.append("## Engine confirmation (top candidates, research slice)\n")
        L.append(md_table(pd.DataFrame(conf_rows)) + "\n")
    L.append("## Development candidates (not approved)\n")
    top_pool = cand_c if not cand_c.empty else cand_s
    best = pd.concat([cand_s.head(1), cand_c.head(1)]).drop_duplicates("spec")
    if best.empty:
        L.append("(no candidate passed the gates)\n")
    else:
        for _, r in best.iterrows():
            L.append(f"- `{r['spec']}`  (pos_folds {r['pos_folds']}, "
                     f"wf_mean_sharpe {r['wf_mean_sharpe']:.2f}, res Sharpe {r['res_sharpe']})")
        L.append("\nDevelopment diagnostic command (not a judgment):\n")
        L.append("```")
        L.append(f"python scripts/run_combo_matrix.py --final \"{best.iloc[0]['spec']}\"")
        L.append("```")
    L.append("## Caveats\n")
    L.append(f"- {len(grid)} configs were ranked (multiple testing); the excluded development "
             "set is consumed and cannot support a final validation claim.")
    L.append("- Fold test metrics attribute a trade to its ENTRY bar; a position open "
             "across a fold boundary is counted in the entry fold (engine-identical "
             "accounting, boundary effects <= 1 trade).")
    L.append("- Combos share the same W and T for both legs (same-scale extremes); "
             "per-leg asymmetry is a possible later refinement.")
    L.append("- NaN z-scores (warm-up, holiday flat candles) never trigger entries.")
    L.append("- Margin/leverage not modeled (fixed 100 oz).")

    out = REPORTS / f"combo_matrix{suffix}.md"
    out.write_text("\n".join(L) + "\n", encoding="utf-8")
    print(f"\nsaved: {out.relative_to(ROOT)}")
    print(f"total runtime: {time.perf_counter() - t0:.0f}s")


if __name__ == "__main__":
    main()
