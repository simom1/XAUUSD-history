# -*- coding: utf-8 -*-
"""Factor screening pipeline: IC study + single-factor grid backtest.

Stages:
  0. calibrate the fast vectorized accounting against the real engine (EMA 9/21)
  1. monthly Spearman IC per factor x horizon (IS only for selection)
  2. single-factor grid backtest: rolling-z entries, fixed hold, exact cost model
  3. re-confirm top configurations with the real event-driven engine
  4. write report/factor_screening.md + CSVs

Usage:
  python scripts/run_screening.py [--is-frac 0.7] [--min-trades 150]
                                  [--confirm 6] [--skip-confirm]
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
from strategies import EmaCrossStrategy
from analysis.factor_screening import (
    ANN, COST_SIDE, OZ, Session, build_factors, build_path, config_metrics, decile_profile,
    factor_list, forward_returns, ic_stats, pnl_from_path, path_from_targets,
    rolling_z,
)

DATA = ROOT / "data" / "xauusd_5m_indicators.csv.gz"
REPORTS = ROOT / "report"


def md_table(df: pd.DataFrame, floatfmt: str = "{:.2f}") -> str:
    if df.empty:
        return "(empty)"
    cols = list(df.columns)
    lines = ["| " + " | ".join(cols) + " |",
             "|" + "|".join("---:" for _ in cols) + "|"]
    for _, r in df.iterrows():
        cells = []
        for col in cols:
            v = r[col]
            if isinstance(v, float):
                cells.append(floatfmt.format(v))
            else:
                cells.append(str(v))
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", type=Path, default=DATA,
                    help="indicator csv.gz (default: 5m dataset)")
    ap.add_argument("--bar-seconds", type=int, default=300,
                    help="bar duration in seconds (300=5m, 900=15m)")
    ap.add_argument("--tag", default="",
                    help="suffix for output files/reports (e.g. _15m)")
    ap.add_argument("--is-frac", type=float, default=0.7)
    ap.add_argument("--windows", type=int, nargs="+", default=[2016, 6048])
    ap.add_argument("--thrs", type=float, nargs="+", default=[1.5, 2.5])
    ap.add_argument("--holds", type=int, nargs="+", default=[12, 84])
    ap.add_argument("--min-trades", type=int, default=150)
    ap.add_argument("--top", type=int, default=25)
    ap.add_argument("--confirm", type=int, default=6)
    ap.add_argument("--skip-confirm", action="store_true")
    ap.add_argument("--research-end", default="2026-03-10",
                    help="exclusive UTC date; later data is development-only")
    args = ap.parse_args()
    ann = float(np.sqrt(86400 / args.bar_seconds * 252))

    t0 = time.perf_counter()
    print(f"loading {args.data.name} ...")
    df_all = pd.read_csv(args.data)
    cutoff = pd.Timestamp(args.research_end, tz="UTC").timestamp()
    df = df_all[df_all["timestamp"] < cutoff].reset_index(drop=True)
    n = len(df)
    ts_sec = df["timestamp"].to_numpy(dtype=np.int64)
    ts = pd.to_datetime(df["timestamp"], unit="s")
    o = df["open"].to_numpy(float)
    c = df["close"].to_numpy(float)
    is_end = int(n * args.is_frac)
    print(f"research cutoff={args.research_end} (exclusive; later data is development-only)")
    print(f"bars={n:,}  IS=[0:{is_end:,}] {ts.iloc[0]:%Y-%m-%d} -> {ts.iloc[is_end]:%Y-%m-%d}"
          f"   OOS=[{is_end:,}:{n:,}] {ts.iloc[is_end]:%Y-%m-%d} -> {ts.iloc[-1]:%Y-%m-%d}")
    ses = Session(ts_sec, bar_seconds=args.bar_seconds)

    # ---------------- stage 0: fast-model calibration ----------------
    print("\n[0] calibrating fast accounting vs engine (EMA 9/21) ...")
    strat = EmaCrossStrategy(9, 21)
    tgt = strat.targets(df)
    res = BacktestEngine(BacktestConfig(bar_seconds=args.bar_seconds)).run(
        df, tgt, warmup_bars=strat.warmup_bars)
    eng_net = res.equity[-1] - res.config.initial_capital
    tgt[:strat.warmup_bars] = 0.0
    pos = path_from_targets(tgt, ses.blocked, ses.flat)
    fast_net = float(pnl_from_path(pos, o, c, ses.flat).sum())
    calib_ok = abs(eng_net - fast_net) < 1.0
    print(f"    engine net = ${eng_net:,.0f}   fast net = ${fast_net:,.0f}   "
          f"|delta| = ${abs(eng_net - fast_net):.4f}   -> {'OK' if calib_ok else 'MISMATCH!'}")
    if not calib_ok:
        raise SystemExit("fast accounting does not match the engine - aborting")

    # ---------------- stage 1: IC study ----------------
    print("\n[1] information coefficient study ...")
    F = build_factors(df)
    names = factor_list()
    assert all(col in F.columns for col in names), "factor universe mismatch"
    ic_df = ic_stats(F, c, ts, is_end, horizons=(12, 84, 288))
    ic_df.to_csv(REPORTS / f"factor_ic_results{args.tag}.csv", index=False)
    print(f"    {len(ic_df)} IC rows -> factor_ic_results{args.tag}.csv")

    # ---------------- stage 2: grid backtest ----------------
    print("\n[2] single-factor grid backtest ...")
    rows = []
    for fi_, fname in enumerate(names, 1):
        s = F[fname]
        for W in args.windows:
            z = rolling_z(s, W)
            for T in args.thrs:
                el_raw = z >= T
                es_raw = z <= -T
                for sgn in (1, -1):
                    ld, sd_ = (el_raw, es_raw) if sgn > 0 else (es_raw, el_raw)
                    for H in args.holds:
                        p, corr, trades = build_path(ld, sd_, H, ses, o, c, n)
                        if not trades:
                            continue
                        B = pnl_from_path(p, o, c, ses.flat, corr)
                        lo_is = max(0, trades[0][0] - 1)
                        m_is = config_metrics(B, trades, lo_is, is_end, ann=ann)
                        m_os = config_metrics(B, trades, is_end, n, ann=ann)
                        m_fl = config_metrics(B, trades, lo_is, n, ann=ann)
                        rows.append({
                            "factor": fname, "win": W, "thr": T,
                            "long_when": "high" if sgn > 0 else "low", "hold": H,
                            "is_sharpe": m_is["sharpe"], "is_pnl": m_is["pnl"],
                            "is_trades": m_is["trades"], "is_avg_usd": m_is["avg_usd"],
                            "is_pf": m_is["pf"], "is_maxdd": m_is["maxdd"],
                            "oos_sharpe": m_os["sharpe"], "oos_pnl": m_os["pnl"],
                            "oos_trades": m_os["trades"], "oos_avg_usd": m_os["avg_usd"],
                            "oos_pf": m_os["pf"],
                            "all_trades": m_fl["trades"], "all_pnl": m_fl["pnl"],
                            "all_avg_usd": m_fl["avg_usd"], "all_pf": m_fl["pf"],
                        })
        print(f"    [{fi_:2d}/{len(names)}] {fname}")
    grid = pd.DataFrame(rows)
    grid.to_csv(REPORTS / f"factor_grid_results{args.tag}.csv", index=False)
    print(f"    {len(grid)} configurations -> factor_grid_results{args.tag}.csv")

    ok = grid[grid["is_trades"] >= args.min_trades].copy()
    ok = ok.sort_values("is_sharpe", ascending=False).reset_index(drop=True)
    print(f"    {len(ok)} / {len(grid)} configs pass min IS trades >= {args.min_trades}")

    # ---------------- stage 3: engine confirmation ----------------
    confirm_rows = []
    if not args.skip_confirm and len(ok):
        print("\n[3] engine confirmation of top configs (one per factor) ...")
        seen: set[str] = set()
        picked = []
        for _, r in ok.iterrows():
            if r["factor"] in seen:
                continue
            seen.add(r["factor"])
            picked.append(r)
            if len(picked) >= args.confirm:
                break
        for k, r in enumerate(picked, 1):
            z = rolling_z(F[r["factor"]], int(r["win"]))
            T, H = float(r["thr"]), int(r["hold"])
            if r["long_when"] == "high":
                ld, sd_ = z >= T, z <= -T
            else:
                ld, sd_ = z <= -T, z >= T
            p, corr, trades = build_path(ld, sd_, H, ses, o, c, n)
            tgtz = np.zeros(n)
            for (f, e, sgn_, last) in trades:
                tgtz[f - 1:last] = sgn_ * OZ
            cres = BacktestEngine(BacktestConfig(bar_seconds=args.bar_seconds)).run(
                df, tgtz, warmup_bars=0, meta={"config": r.to_dict()})
            eng_pnl = cres.equity[-1] - cres.config.initial_capital
            eng_tr = len(cres.trades)
            eng_cost = float(cres.trades["costs"].sum()) if eng_tr else 0.0
            tr = cres.trades
            if eng_tr:
                gp = tr.loc[tr["net_pnl"] > 0, "net_pnl"].sum()
                gl = -tr.loc[tr["net_pnl"] < 0, "net_pnl"].sum()
                eng_pf = float(gp / gl) if gl > 0 else float("inf")
            else:
                eng_pf = float("nan")
            fast_full = float(pnl_from_path(p, o, c, ses.flat, corr).sum())
            confirm_rows.append({
                "config": f"{r['factor']} | W{int(r['win'])} T{T:.1f} "
                          f"long@{r['long_when']} H{H}",
                "engine_pnl": round(eng_pnl, 0),
                "engine_trades": eng_tr,
                "engine_pf": round(eng_pf, 3) if np.isfinite(eng_pf) else float("nan"),
                "engine_costs": round(eng_cost, 0),
                "fast_pnl": round(fast_full, 0),
                "delta": round(abs(eng_pnl - fast_full), 2),
                "is_sharpe": r["is_sharpe"], "oos_sharpe": r["oos_sharpe"],
                "oos_pnl": r["oos_pnl"],
            })
            print(f"    [{k}/{len(picked)}] {r['factor']:24s} engine ${eng_pnl:>10,.0f} "
                  f"fast ${fast_full:>10,.0f}  delta ${abs(eng_pnl - fast_full):.2f}")
    conf_df = pd.DataFrame(confirm_rows)

    # ---------------- stage 4: decile profiles ----------------
    print("\n[4] decile profiles for top IC factors ...")
    ic84 = ic_df[ic_df["h"] == 84].copy()
    ic84["abst"] = ic84["t"].abs()
    top_ic = ic84.sort_values("abst", ascending=False).head(5)
    fwd84 = forward_returns(c, 84)
    dec_md = []
    for _, r in top_ic.iterrows():
        prof = decile_profile(F[r["factor"]].to_numpy(), fwd84, is_end)
        dec_md.append(f"\n**{r['factor']}** (monthly-IC t = {r['t']}, "
                      f"IS spr = {r['is_spr']}, OOS spr = {r['oos_spr']})\n")
        if prof.empty:
            dec_md.append("(degenerate distribution, skipped)\n")
        else:
            prof = prof.reset_index()
            prof.columns = [str(cc) for cc in prof.columns]
            dec_md.append(md_table(prof, floatfmt="{:+.2f}") + "\n")

    # ---------------- report ----------------
    print("\n[5] writing report ...")
    top = ok.head(args.top)
    show = top[["factor", "win", "thr", "long_when", "hold",
                "is_sharpe", "is_pnl", "is_trades", "is_avg_usd", "is_pf",
                "oos_sharpe", "oos_pnl", "oos_trades", "oos_avg_usd", "oos_pf"]].copy()
    show.insert(0, "rank", range(1, len(show) + 1))

    n_cfg = len(grid)
    tf_label = {300: "5m", 900: "15m", 1800: "30m", 3600: "1h"}.get(args.bar_seconds,
               f"{args.bar_seconds}s")
    L = []
    L.append(f"# XAUUSD {tf_label} - Factor Screening Report\n")
    L.append(f"> Research-only revision: {args.research_end} onward is excluded from selection and remains a consumed development set.\n")
    L.append(f"- data: `{args.data.name}` ({n:,} bars, {ts.iloc[0]:%Y-%m-%d} -> {ts.iloc[-1]:%Y-%m-%d})")
    L.append(f"- IS/OOS split: first {args.is_frac:.0%} IS "
             f"({ts.iloc[0]:%Y-%m-%d} -> {ts.iloc[is_end]:%Y-%m-%d}), "
             f"last {1 - args.is_frac:.0%} OOS ({ts.iloc[is_end]:%Y-%m-%d} -> {ts.iloc[-1]:%Y-%m-%d})")
    L.append(f"- cost model: all-in $0.16/oz round trip ($0.08/side); 1 unit = {OZ:.0f} oz")
    L.append(f"- data quality: see `report/data_quality_5m.md` "
             f"(verdict: clean; 22 holiday flat candles -> 88 structural NaN cells in 4 columns)")
    L.append("\n## Method\n")
    L.append(f"1. **Factor universe**: {len(names)} scale-free factors derived from the "
             "64-indicator set (price-level indicators converted to % distance / channel position).")
    L.append(f"2. **IC study**: monthly Spearman rank IC vs forward returns "
             f"h in {tuple(int(x) for x in (12, 84, 288))} bars "
             f"({args.bar_seconds / 60:.0f}m bars -> "
             f"{12 * args.bar_seconds / 3600:.0f}h / {84 * args.bar_seconds / 3600:.0f}h / "
             f"{288 * args.bar_seconds / 3600:.0f}h); "
             "selection uses IS months only, OOS Spearman reported as stability check.")
    L.append(f"3. **Grid backtest**: entry when trailing z-score (windows {args.windows}) "
             f"crosses +/-{args.thrs}, fixed hold {args.holds} bars, long-when-high (momentum) "
             "vs long-when-low (reversal) both evaluated; exact engine accounting "
             "(next-open fills, session flat 21:00 UTC / Fri 20:45, entry block 15 min, "
             "$0.16 RT cost). Direction & params selected on IS; OOS untouched.")
    L.append("\n## Fast-model calibration\n")
    L.append("EMA 9/21 baseline: engine vs vectorized accounting "
             f"(net $ over full sample): engine ${eng_net:,.0f} vs fast ${fast_net:,.0f} "
             f"- delta ${abs(eng_net - fast_net):.4f} (float noise).\n")
    L.append("## IC results (h = 84 bars ~ 7h, top 15 by |t|)\n")
    t84 = ic84.sort_values("abst", ascending=False).head(15)[
        ["factor", "ic_mean", "icir", "t", "pos_pct", "is_spr", "oos_spr", "months"]]
    L.append(md_table(t84, floatfmt="{:+.4f}") +
             f"\n\n(full table: `report/factor_ic_results{args.tag}.csv`, horizons 12/84/288)\n")
    L.append("## Single-factor grid - top "
             f"{min(args.top, len(show))} by IS Sharpe (min {args.min_trades} IS trades)\n")
    L.append(md_table(show, floatfmt="{:+.2f}") + "\n")
    L.append(f"Full grid: `report/factor_grid_results.csv` ({n_cfg} configs). "
             f"Columns `is_*`/`oos_*` are in/out-of-sample; `pnl` in USD on {OZ:.0f} oz; "
             f"`avg_usd` = average NET PnL per trade after the ${2 * COST_SIDE * OZ:.2f} cost hurdle.\n")
    if not conf_df.empty:
        L.append("## Engine confirmation (top configs, full sample)\n")
        L.append(md_table(conf_df, floatfmt="{:+.2f}") + "\n")
    L.append("## Decile profiles (fwd 7h return in bp, IS quantile bins applied to both segments)\n")
    L.extend(dec_md)
    L.append("## Caveats\n")
    L.append(f"- **Multiple testing**: {n_cfg} IS configurations were ranked; the best IS "
             "Sharpe is inflated by selection. The OOS columns are the honest check "
             "(same sign & similar magnitude = robust).")
    L.append("- IC uses overlapping forward returns (monthly blocks mitigate but do not "
             "eliminate cross-correlation); treat |t| < 3 as noise given ~27 IS months.")
    L.append("- Rolling z-scores need a warm-up (min_periods = W/2); early IS bars are "
             "inactive for some configs.")
    L.append("- 22 holiday flat candles produce structural NaNs in 4 factors; NaN never "
             "generates entries (comparisons with NaN are False).")
    L.append("- No volume data exists on Gate.io TradFi klines; volume factors out of scope.")
    L.append(f"- Margin/leverage not modeled (fixed {OZ:.0f} oz).")

    out = REPORTS / f"factor_screening{args.tag}.md"
    out.write_text("\n".join(L) + "\n", encoding="utf-8")
    print(f"\nsaved: {out.relative_to(ROOT)}")
    print(f"total runtime: {time.perf_counter() - t0:.0f}s")


if __name__ == "__main__":
    main()
