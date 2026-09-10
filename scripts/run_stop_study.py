# -*- coding: utf-8 -*-
"""Historical independent-leg ATR exit study; not a current selection workflow.

Tests the top long (gated) and short (gated) candidates from the retired phases.
with various ATR-based dynamic exit configurations on both the research
walk-forward and the dev holdout (insight only).

Usage:
  python scripts/run_stop_study.py
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
    ANN, OZ, Session, build_factors, rolling_z,
)
from analysis.combo_screening import (
    SHORT_FAMILY_EXT, SURVIVORS, build_gates, evaluate, fold_list,
    holdout_split, masks_from_spec, md_table, parse_spec, walk_forward,
)

DATA = ROOT / "data" / "xauusd_5m_indicators.csv.gz"
REPORTS = ROOT / "report"

# candidates from Phase 1 (gated long) and Phase 2 (gated short)
CANDIDATES = [
    {"spec": "single|plus_di_14|long|W6048|T1.5|H120",
     "side_map": SURVIVORS, "gate": "trend_up,adx_strong", "tag": "long_gated"},
    {"spec": "single|close_vs_ema200|short|W6048|T1.5|H120",
     "side_map": SHORT_FAMILY_EXT, "gate": "trend_down,adx_strong", "tag": "short_gated"},
    {"spec": "single|close_vs_ema200|short|W4032|T1.5|H120",
     "side_map": SHORT_FAMILY_EXT, "gate": "trend_down,adx_strong", "tag": "short_gated"},
    {"spec": "single|plus_di_14|long|W6048|T1.5|H120",
     "side_map": SURVIVORS, "gate": None, "tag": "long_nogate"},
    {"spec": "single|close_vs_ema200|short|W6048|T1.5|H120",
     "side_map": SHORT_FAMILY_EXT, "gate": None, "tag": "short_nogate"},
]

# stop configurations to test
STOP_CONFIGS = [
    {"stop_atr": None, "trail_atr": None, "target_atr": None, "label": "baseline"},
    {"stop_atr": 2.0, "trail_atr": None, "target_atr": None, "label": "stop2"},
    {"stop_atr": 1.5, "trail_atr": None, "target_atr": None, "label": "stop1.5"},
    {"stop_atr": 2.5, "trail_atr": None, "target_atr": None, "label": "stop2.5"},
    {"stop_atr": None, "trail_atr": 3.0, "target_atr": None, "label": "trail3"},
    {"stop_atr": None, "trail_atr": 4.0, "target_atr": None, "label": "trail4"},
    {"stop_atr": None, "trail_atr": None, "target_atr": 3.0, "label": "target3"},
    {"stop_atr": 2.0, "trail_atr": 3.0, "target_atr": None, "label": "stop2+trail3"},
    {"stop_atr": 2.0, "trail_atr": None, "target_atr": 3.0, "label": "stop2+target3"},
    {"stop_atr": 2.0, "trail_atr": 3.0, "target_atr": 4.0, "label": "stop2+trail3+tgt4"},
]


def main() -> None:
    t0 = time.perf_counter()
    print(f"loading {DATA.name} ...")
    df = pd.read_csv(DATA)
    ts_sec = df["timestamp"].to_numpy(dtype=np.int64)
    ts = pd.to_datetime(df["timestamp"], unit="s")
    n_full = len(df)
    h_idx, h_start = holdout_split(ts_sec, 183)
    n = h_idx  # research period

    print(f"full sample {ts.iloc[0]:%Y-%m-%d} -> {ts.iloc[-1]:%Y-%m-%d} ({n_full:,} bars)")
    print(f"research: {ts.iloc[0]:%Y-%m-%d} -> {ts.iloc[h_idx-1]:%Y-%m-%d} ({n:,} bars)")
    print(f"dev holdout: {h_start:%Y-%m-%d} -> {ts.iloc[-1]:%Y-%m-%d} ({n_full-h_idx:,} bars)")

    # research slice
    df_r = df.iloc[:h_idx].reset_index(drop=True)
    ts_sec_r = df_r["timestamp"].to_numpy(dtype=np.int64)
    o_r = df_r["open"].to_numpy(float)
    c_r = df_r["close"].to_numpy(float)
    ses_r = Session(ts_sec_r)
    atr_r = df_r["atr_14"].to_numpy(float)
    folds = fold_list(ts_sec_r, n, 4, 183)

    # dev holdout slice
    df_h = df.iloc[h_idx:].reset_index(drop=True)
    n_h = len(df_h)
    ts_sec_h = df_h["timestamp"].to_numpy(dtype=np.int64)
    o_h = df_h["open"].to_numpy(float)
    c_h = df_h["close"].to_numpy(float)
    ses_h = Session(ts_sec_h)
    atr_h = df_h["atr_14"].to_numpy(float)

    # factors + z-cache (full sample, then slice)
    print("building factors ...")
    F = build_factors(df)

    def zget_r(fn, W):
        return rolling_z(F[fn], W)[:h_idx]

    def zget_h(fn, W):
        return rolling_z(F[fn], W)[h_idx:]

    gates_full = build_gates(df)

    print(f"\ntesting {len(CANDIDATES)} candidates x {len(STOP_CONFIGS)} stop configs "
          f"= {len(CANDIDATES) * len(STOP_CONFIGS)} evaluations\n")

    rows = []
    for ci, cand in enumerate(CANDIDATES, 1):
        cfg = parse_spec(cand["spec"])
        sm = cand["side_map"]

        # build gates
        lg_r = sg_r = None
        lg_h = sg_h = None
        if cand["gate"]:
            gm = np.ones(n_full, dtype=bool)
            for gn in cand["gate"].split(","):
                gm &= gates_full[gn.strip()]
            if cfg["side"] == "long":
                lg_r = gm[:h_idx]
                lg_h = gm[h_idx:]
            else:
                sg_r = gm[:h_idx]
                sg_h = gm[h_idx:]

        for sc in STOP_CONFIGS:
            sa, ta, tg = sc["stop_atr"], sc["trail_atr"], sc["target_atr"]
            label = sc["label"]

            # research period
            ld_r, sd_r = masks_from_spec(cfg, zget_r, sm, lg_r, sg_r)
            ev_r = evaluate(ld_r, sd_r, cfg["hold"], ses_r, o_r, c_r, n, folds,
                            atr_r, sa, ta, tg)
            if ev_r is None:
                continue
            m_r = ev_r["res"]

            # walk-forward
            wf_picks, wf_agg = walk_forward(
                pd.DataFrame([{"spec": cand["spec"], **cfg,
                               "f1_train_sharpe": m_r["sharpe"],
                               "f1_train_trades": m_r["trades"],
                               "f1_train_avg": m_r["avg_usd"],
                               "f1_test_sharpe": m_r["sharpe"],
                               "f1_test_pnl": m_r["pnl"],
                               "f1_test_trades": m_r["trades"],
                               "f1_test_avg": m_r["avg_usd"],
                               "f1_test_pf": m_r["pf"],
                               "f2_train_sharpe": m_r["sharpe"],
                               "f2_train_trades": m_r["trades"],
                               "f2_train_avg": m_r["avg_usd"],
                               "f2_test_sharpe": m_r["sharpe"],
                               "f2_test_pnl": m_r["pnl"],
                               "f2_test_trades": m_r["trades"],
                               "f2_test_avg": m_r["avg_usd"],
                               "f2_test_pf": m_r["pf"],
                               "f3_train_sharpe": m_r["sharpe"],
                               "f3_train_trades": m_r["trades"],
                               "f3_train_avg": m_r["avg_usd"],
                               "f3_test_sharpe": m_r["sharpe"],
                               "f3_test_pnl": m_r["pnl"],
                               "f3_test_trades": m_r["trades"],
                               "f3_test_avg": m_r["avg_usd"],
                               "f3_test_pf": m_r["pf"],
                               "f4_train_sharpe": m_r["sharpe"],
                               "f4_train_trades": m_r["trades"],
                               "f4_train_avg": m_r["avg_usd"],
                               "f4_test_sharpe": m_r["sharpe"],
                               "f4_test_pnl": m_r["pnl"],
                               "f4_test_trades": m_r["trades"],
                               "f4_test_avg": m_r["avg_usd"],
                               "f4_test_pf": m_r["pf"],
                               }]),
                folds, 20, zget_r, ses_r, o_r, c_r, n, sm, lg_r, sg_r,
                atr_r, sa, ta, tg)

            # dev holdout
            ld_h, sd_h = masks_from_spec(cfg, zget_h, sm, lg_h, sg_h)
            ev_h = evaluate(ld_h, sd_h, cfg["hold"], ses_h, o_h, c_h, n_h, [],
                            atr_h, sa, ta, tg)
            m_h = ev_h["res"] if ev_h else {"pnl": 0, "trades": 0, "sharpe": 0, "avg_usd": 0}

            wf_pnl = wf_agg["wf_pnl"].iloc[0] if not wf_agg.empty else 0
            wf_sh = wf_agg["wf_sharpe"].iloc[0] if not wf_agg.empty else 0
            wf_pos = wf_agg["folds_positive"].iloc[0] if not wf_agg.empty else 0

            rows.append({
                "candidate": cand["tag"],
                "spec": cand["spec"],
                "stop": label,
                "res_pnl": round(m_r["pnl"], 0),
                "res_trades": m_r["trades"],
                "res_sharpe": m_r["sharpe"],
                "res_avg": round(m_r["avg_usd"], 2),
                "wf_pnl": wf_pnl,
                "wf_sharpe": wf_sh,
                "wf_pos": wf_pos,
                "dev_pnl": round(m_h["pnl"], 0),
                "dev_trades": m_h["trades"],
                "dev_sharpe": m_h["sharpe"],
                "dev_avg": round(m_h["avg_usd"], 2),
            })
            print(f"  [{ci}/{len(CANDIDATES)}] {cand['tag']:14s} {label:20s} "
                  f"res ${m_r['pnl']:>+8,.0f} ({m_r['trades']:4d}tr) "
                  f"wf ${wf_pnl:>+8,.0f} ({wf_pos}f+) "
                  f"dev ${m_h['pnl']:>+8,.0f} ({m_h['trades']:4d}tr)")

    results = pd.DataFrame(rows)
    results.to_csv(REPORTS / "stop_study.csv", index=False)

    # report
    L = []
    L.append("# Phase 3: ATR Stop-Loss / Trailing / Target Study\n")
    L.append(f"- data: `{DATA.name}` ({n_full:,} bars)")
    L.append(f"- research: {ts.iloc[0]:%Y-%m-%d} -> {ts.iloc[h_idx-1]:%Y-%m-%d} ({n:,} bars)")
    L.append(f"- dev holdout (insight only): {h_start:%Y-%m-%d} -> {ts.iloc[-1]:%Y-%m-%d} ({n_full-h_idx:,} bars)")
    L.append(f"- ATR: atr_14 (Wilder 14-bar ATR)")
    L.append(f"- stops checked at each bar's CLOSE (mark-to-close)\n")
    L.append("## Stop configurations\n")
    L.append("| label | stop_atr | trail_atr | target_atr |")
    L.append("|---|---:|---:|---:|")
    for sc in STOP_CONFIGS:
        L.append(f"| {sc['label']} | {sc['stop_atr'] or '-'} | {sc['trail_atr'] or '-'} | {sc['target_atr'] or '-'} |")
    L.append("")
    L.append("## Results (all candidates x stop configs)\n")
    L.append(md_table(results[["candidate", "stop", "res_pnl", "res_trades", "res_sharpe",
                               "wf_pnl", "wf_sharpe", "wf_pos",
                               "dev_pnl", "dev_trades", "dev_sharpe"]]))
    L.append("")
    L.append("## Key comparisons\n")
    for cand_tag in results["candidate"].unique():
        sub = results[results["candidate"] == cand_tag]
        base = sub[sub["stop"] == "baseline"]
        if base.empty:
            continue
        L.append(f"\n**{cand_tag}** (`{base.iloc[0]['spec']}`)\n")
        L.append(md_table(sub[["stop", "res_pnl", "res_trades", "res_sharpe",
                                "wf_pnl", "wf_sharpe", "wf_pos",
                                "dev_pnl", "dev_trades", "dev_sharpe"]]))
        L.append("")

    out = REPORTS / "stop_study.md"
    out.write_text("\n".join(L) + "\n", encoding="utf-8")
    print(f"\nsaved: {out.relative_to(ROOT)}")
    print(f"total runtime: {time.perf_counter() - t0:.0f}s")


if __name__ == "__main__":
    main()
