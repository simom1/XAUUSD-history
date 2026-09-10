# -*- coding: utf-8 -*-
"""Phase 4: New composite factor screening.

Tests the 5 new composite factors (di_spread, aroon_osc, di_ratio,
bb_squeeze, vol_percentile) via IC study + single-factor grid with
walk-forward validation and dev holdout insight.

Usage:
  python scripts/run_factor_expansion.py
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import numpy as np
import pandas as pd

from analysis.factor_screening import (
    ANN, OZ, Session, build_factors, rolling_z, forward_returns, ic_stats,
)
from analysis.combo_screening import (
    SURVIVORS, build_gates, evaluate, fold_list, holdout_split,
    leg_masks, masks_from_spec, md_table, parse_spec, spec_string, walk_forward,
)

DATA = ROOT / "data" / "xauusd_5m_indicators.csv.gz"
REPORTS = ROOT / "report"

# new composite factors and their long-when direction
NEW_FACTORS = {
    "di_spread": "high",       # +DI > -DI = bullish
    "aroon_osc": "high",       # aroon up > aroon down = bullish
    "di_ratio": "high",        # +DI / -DI > 1 = bullish
    "bb_squeeze": "low",       # squeeze (low width) = breakout pending
    "vol_percentile": "low",   # low vol percentile = calm before move
}

WINDOWS = [4032, 6048, 8640]
THRS = [1.25, 1.5, 1.75, 2.0]
HOLDS = [24, 36, 84, 120]


def main() -> None:
    t0 = time.perf_counter()
    print(f"loading {DATA.name} ...")
    df = pd.read_csv(DATA)
    ts_sec = df["timestamp"].to_numpy(dtype=np.int64)
    ts = pd.to_datetime(df["timestamp"], unit="s")
    n_full = len(df)
    h_idx, h_start = holdout_split(ts_sec, 183)
    n = h_idx

    print(f"full sample {ts.iloc[0]:%Y-%m-%d} -> {ts.iloc[-1]:%Y-%m-%d} ({n_full:,} bars)")
    print(f"research: {ts.iloc[0]:%Y-%m-%d} -> {ts.iloc[h_idx-1]:%Y-%m-%d} ({n:,} bars)")
    print(f"dev holdout: {h_start:%Y-%m-%d} -> {ts.iloc[-1]:%Y-%m-%d} ({n_full-h_idx:,} bars)")

    df_r = df.iloc[:h_idx].reset_index(drop=True)
    ts_sec_r = df_r["timestamp"].to_numpy(dtype=np.int64)
    o_r = df_r["open"].to_numpy(float)
    c_r = df_r["close"].to_numpy(float)
    ses_r = Session(ts_sec_r)
    atr_r = df_r["atr_14"].to_numpy(float)
    folds = fold_list(ts_sec_r, n, 4, 183)

    df_h = df.iloc[h_idx:].reset_index(drop=True)
    n_h = len(df_h)
    ts_sec_h = df_h["timestamp"].to_numpy(dtype=np.int64)
    o_h = df_h["open"].to_numpy(float)
    c_h = df_h["close"].to_numpy(float)
    ses_h = Session(ts_sec_h)
    atr_h = df_h["atr_14"].to_numpy(float)

    print("building factors ...")
    F = build_factors(df)

    def zget_r(fn, W):
        return rolling_z(F[fn], W)[:h_idx]

    def zget_h(fn, W):
        return rolling_z(F[fn], W)[h_idx:]

    # ---- IC study ----
    print("\n[1] IC study (Spearman, monthly, 12/84/288-bar forward return) ...")
    F_r = F.iloc[:h_idx][list(NEW_FACTORS.keys())]
    close_r = df_r["close"].to_numpy(float)
    ts_r = pd.to_datetime(df_r["timestamp"], unit="s")
    ic_df = ic_stats(F_r, close_r, ts_r, n)
    ic_rows = []
    for fn in NEW_FACTORS:
        sub = ic_df[ic_df["factor"] == fn].sort_values("h")
        r12 = sub[sub["h"] == 12].iloc[0] if not sub[sub["h"] == 12].empty else None
        if r12 is not None:
            ic_rows.append({"factor": fn, "ic_mean": r12["ic_mean"],
                            "ic_std": r12["ic_std"], "ic_ir": r12["icir"],
                            "direction": NEW_FACTORS[fn]})
            print(f"    {fn:18s} IC {r12['ic_mean']:+.4f}  IR {r12['icir']:+.3f}")
        else:
            ic_rows.append({"factor": fn, "ic_mean": 0, "ic_std": 0,
                            "ic_ir": 0, "direction": NEW_FACTORS[fn]})

    # ---- grid screening ----
    print(f"\n[2] grid: {len(NEW_FACTORS)} factors x 2 sides x "
          f"{len(WINDOWS)}W x {len(THRS)}T x {len(HOLDS)}H "
          f"= {len(NEW_FACTORS)*2*len(WINDOWS)*len(THRS)*len(HOLDS)} configs")

    cfgs = []
    for fn, direction in NEW_FACTORS.items():
        for W in WINDOWS:
            for T in THRS:
                for side in ("long", "short"):
                    for H in HOLDS:
                        cfgs.append({"kind": "single", "factor": fn, "side": side,
                                     "win": W, "thr": T, "hold": H,
                                     "direction": direction})

    rows = []
    for i, cfg in enumerate(cfgs, 1):
        z = zget_r(cfg["factor"], cfg["win"])
        ld0, sd0 = leg_masks(z, cfg["direction"], cfg["thr"])
        if cfg["side"] == "long":
            ld, sd_ = ld0, np.zeros_like(ld0)
        else:
            ld, sd_ = np.zeros_like(ld0), sd0
        ev = evaluate(ld, sd_, cfg["hold"], ses_r, o_r, c_r, n, folds)
        if ev is None:
            continue
        base = dict(cfg)
        base["spec"] = spec_string(cfg)
        from analysis.combo_screening import flatten
        rows.append(flatten(base, ev, folds))
        if i % 48 == 0 or i == len(cfgs):
            print(f"    [{i:3d}/{len(cfgs)}] {cfg['factor']:18s} {cfg['side']:5s} "
                  f"W{cfg['win']} T{cfg['thr']:g} H{cfg['hold']}")

    grid = pd.DataFrame(rows)
    grid.to_csv(REPORTS / "factor_expansion_grid.csv", index=False)
    print(f"    {len(grid)} configs evaluated")

    # ---- walk-forward ----
    print("\n[3] walk-forward ...")
    wf_long = walk_forward(grid[grid["side"] == "long"], folds, 40,
                           zget_r, ses_r, o_r, c_r, n, side_map=NEW_FACTORS)
    wf_short = walk_forward(grid[grid["side"] == "short"], folds, 40,
                            zget_r, ses_r, o_r, c_r, n, side_map=NEW_FACTORS)
    print(f"    long:  {wf_long[1].to_dict('records')[0] if not wf_long[1].empty else 'none'}")
    print(f"    short: {wf_short[1].to_dict('records')[0] if not wf_short[1].empty else 'none'}")

    # ---- top candidates + dev holdout ----
    print("\n[4] top candidates on dev holdout ...")
    for side_label, sub in [("long", grid[grid["side"] == "long"]),
                            ("short", grid[grid["side"] == "short"])]:
        ok = sub[sub["res_trades"] >= 80].copy()
        if ok.empty:
            continue
        ok["pos_folds"] = [sum(r[f"{f['name']}_test_pnl"] > 0 for f in folds)
                           for _, r in ok.iterrows()]
        ok = ok.sort_values(["pos_folds", "res_sharpe"], ascending=False)
        print(f"\n  ** {side_label} top 5 **")
        for _, r in ok.head(5).iterrows():
            cfg = parse_spec(r["spec"])
            z = zget_h(cfg["factor"], cfg["win"])
            ld0, sd0 = leg_masks(z, NEW_FACTORS[cfg["factor"]], cfg["thr"])
            if cfg["side"] == "long":
                ld_h, sd_h = ld0, np.zeros_like(ld0)
            else:
                ld_h, sd_h = np.zeros_like(ld0), sd0
            ev_h = evaluate(ld_h, sd_h, cfg["hold"], ses_h, o_h, c_h, n_h, [])
            m_h = ev_h["res"] if ev_h else {"pnl": 0, "trades": 0, "sharpe": 0}
            print(f"    {r['spec']:55s} res ${r['res_pnl']:>+8,.0f} "
                  f"({r['res_trades']:4d}tr, {r['pos_folds']}f+) "
                  f"dev ${m_h['pnl']:>+8,.0f} ({m_h['trades']:4d}tr)")

    # ---- also test best long with stop2.5 on dev ----
    print("\n[5] best long candidates with stop_atr=2.5 on dev holdout ...")
    ok = grid[(grid["side"] == "long") & (grid["res_trades"] >= 80)].copy()
    if not ok.empty:
        ok["pos_folds"] = [sum(r[f"{f['name']}_test_pnl"] > 0 for f in folds)
                           for _, r in ok.iterrows()]
        ok = ok.sort_values(["pos_folds", "res_sharpe"], ascending=False)
        for _, r in ok.head(3).iterrows():
            cfg = parse_spec(r["spec"])
            z = zget_h(cfg["factor"], cfg["win"])
            ld0, sd0 = leg_masks(z, NEW_FACTORS[cfg["factor"]], cfg["thr"])
            ld_h, sd_h = ld0, np.zeros_like(ld0)
            ev_h = evaluate(ld_h, sd_h, cfg["hold"], ses_h, o_h, c_h, n_h, [],
                            atr_h, 2.5, None, None)
            m_h = ev_h["res"] if ev_h else {"pnl": 0, "trades": 0, "sharpe": 0}
            print(f"    {r['spec']:55s} stop2.5 dev ${m_h['pnl']:>+8,.0f} "
                  f"({m_h['trades']:4d}tr, Sharpe {m_h['sharpe']:.2f})")

    # ---- report ----
    L = []
    L.append("# Phase 4: New Composite Factor Screening\n")
    L.append(f"- data: `{DATA.name}` ({n_full:,} bars)")
    L.append(f"- research: {ts.iloc[0]:%Y-%m-%d} -> {ts.iloc[h_idx-1]:%Y-%m-%d} ({n:,} bars)")
    L.append(f"- dev holdout (insight only): {h_start:%Y-%m-%d} -> {ts.iloc[-1]:%Y-%m-%d} ({n_full-h_idx:,} bars)")
    L.append(f"- new factors: {', '.join(NEW_FACTORS.keys())}\n")
    L.append("## IC study (12-bar forward return, Spearman)\n")
    L.append(md_table(pd.DataFrame(ic_rows)))
    L.append("")
    L.append("## Walk-forward results\n")
    for label, (picks, agg) in [("long", wf_long), ("short", wf_short)]:
        L.append(f"\n**{label}**\n")
        if not picks.empty:
            L.append(md_table(picks) + "\n")
        if not agg.empty:
            L.append(md_table(agg) + "\n")
    L.append("## Top candidates (research)\n")
    for side_label, sub in [("long", grid[grid["side"] == "long"]),
                            ("short", grid[grid["side"] == "short"])]:
        ok = sub[sub["res_trades"] >= 80].copy()
        if ok.empty:
            continue
        ok["pos_folds"] = [sum(r[f"{f['name']}_test_pnl"] > 0 for f in folds)
                           for _, r in ok.iterrows()]
        ok = ok.sort_values(["pos_folds", "res_sharpe"], ascending=False)
        L.append(f"\n**{side_label}**\n")
        cols = ["spec", "res_sharpe", "res_pnl", "res_trades", "res_avg", "pos_folds"]
        L.append(md_table(ok[cols].head(10)) + "\n")

    out = REPORTS / "factor_expansion.md"
    out.write_text("\n".join(L) + "\n", encoding="utf-8")
    print(f"\nsaved: {out.relative_to(ROOT)}")
    print(f"total runtime: {time.perf_counter() - t0:.0f}s")


if __name__ == "__main__":
    main()
