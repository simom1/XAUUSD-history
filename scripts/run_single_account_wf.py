"""Single-account complete-system walk-forward candidate research.

Per expanding train window (research period only, dev set never touched):
  1. fast no-exit screen of single-factor legs from the established robust
     subset -> top 3 long + top 3 short components by train Sharpe;
  2. 3x3 unified single-account systems x 4 regime filters x 4 UTC session
     filters on the fast path (no-exit), top 2 regime/session per system;
  3. all 7 exit rules scored by the EVENT ENGINE on the train prefix only;
  4. each test fold executes only the complete system chosen on its train
     window.

A static development candidate must be the train-window pick in >= 3 folds;
otherwise the report states that no candidate exists.  USD @ 1 oz,
$0.16/oz round-trip cost throughout.
"""
from __future__ import annotations

import sys
import time
from itertools import product
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import numpy as np
import pandas as pd

from analysis.combo_screening import (SHORT_FAMILY_EXT, SURVIVORS, build_gates,
                                      fold_list, holdout_split, leg_masks,
                                      md_table)
from analysis.factor_screening import (ANN, OZ, Session, build_factors,
                                       config_metrics, path_from_targets,
                                       pnl_from_path, rolling_z)
from backtest import BacktestConfig, BacktestEngine
from scripts.run_integration import unified_targets

DATA = ROOT / "data" / "xauusd_5m_indicators.csv.gz"
REPORT = ROOT / "report" / "single_account_wf.md"
PICKS_CSV = ROOT / "report" / "single_account_wf_picks.csv"

FAMILY = {**SURVIVORS, **SHORT_FAMILY_EXT}          # factor -> long-when side
W_GRID = (4032, 6048, 8640)
T_GRID = (1.25, 1.5, 1.75, 2.0)
H_GRID = (24, 36, 84, 120)
LEG_MIN_TRADES = 40
SYS_MIN_TRADES = 30
EXIT_MIN_TRADES = 20
TOP_K = 3

REGIMES = ("all", "trend_up", "trend_down", "not_choppy")
SESSIONS = ("all", "asia", "london", "ny")
EXITS = (
    ("none", {}),
    ("stop2", {"stop_loss_atr": 2.0}),
    ("stop2.5", {"stop_loss_atr": 2.5}),
    ("stop3", {"stop_loss_atr": 3.0}),
    ("trail3", {"trailing_stop_atr": 3.0}),
    ("target3", {"take_profit_atr": 3.0}),
    ("stop2+target3", {"stop_loss_atr": 2.0, "take_profit_atr": 3.0}),
)


def seg_bar_metrics(res, lo: int, hi: int) -> dict:
    pnl = np.diff(np.r_[res.config.initial_capital, res.equity])[lo:hi]
    curve = np.cumsum(pnl)
    dd = float((curve - np.maximum.accumulate(curve)).min()) if len(curve) else 0.0
    sh = float(pnl.mean() / pnl.std() * ANN) if len(pnl) > 2 and pnl.std() else 0.0
    tr = res.trades
    tr = tr[(tr["entry_i"] >= lo) & (tr["entry_i"] < hi)] if not tr.empty else tr
    return {"pnl": float(pnl.sum()), "sharpe": sh, "maxdd": dd, "trades": int(len(tr)),
            "avg": float(tr["net_pnl"].mean()) if len(tr) else float("nan"),
            "costs": float(tr["costs"].sum()) if len(tr) else 0.0}


def trades_from_pos(pos: np.ndarray) -> list[tuple]:
    """(f, e, s, last) trade tuples from a signed position path."""
    trades = []
    run_start = None
    for i, p in enumerate(pos):
        if p != 0 and run_start is None:
            run_start = i
        elif p == 0 and run_start is not None:
            trades.append((run_start, i, 1.0 if pos[run_start] > 0 else -1.0, i - 1))
            run_start = None
    if run_start is not None:
        trades.append((run_start, len(pos) - 1, 1.0 if pos[run_start] > 0 else -1.0, len(pos) - 2))
    return trades


def main() -> None:
    t_start = time.time()
    df = pd.read_csv(DATA)
    ts_sec = df["timestamp"].to_numpy(np.int64)
    ts = pd.to_datetime(ts_sec, unit="s")
    n = len(df)
    h_idx, dev_start = holdout_split(ts_sec, 183)
    folds = fold_list(ts_sec, h_idx, 4)
    factors, gates = build_factors(df), build_gates(df)
    atr_arr = df["atr_14"].to_numpy(float)
    o = df["open"].to_numpy(float)
    c = df["close"].to_numpy(float)
    ses = Session(ts_sec)
    hours = ts.hour.to_numpy()

    regime_masks = {"all": np.ones(n, bool), "trend_up": gates["trend_up"],
                    "trend_down": gates["trend_down"], "not_choppy": gates["not_choppy"]}
    session_masks = {"all": np.ones(n, bool), "asia": hours < 7,
                     "london": (hours >= 7) & (hours < 13), "ny": (hours >= 13) & (hours < 21)}

    zcache: dict[tuple, np.ndarray] = {}

    def zget(name, W):
        key = (name, W)
        if key not in zcache:
            zcache[key] = rolling_z(factors[name], W)
        return zcache[key]

    # leg paths are fold-independent: cache (factor,W,T,H,side) -> (B, trades)
    leg_cache: dict[tuple, tuple] = {}

    def leg_eval(factor, W, T, H, side, train_hi):
        key = (factor, W, T, H, side)
        if key not in leg_cache:
            z = zget(factor, W)
            l0, s0 = leg_masks(z, FAMILY[factor], T)
            dec = l0 if side == "long" else s0
            other = np.zeros(n, bool)
            ld, sd = (dec, other) if side == "long" else (other, dec)
            from analysis.factor_screening import build_path
            pos, corr, tr = build_path(ld, sd, H, ses, o, c, n)
            B = pnl_from_path(pos, o, c, ses.flat, corr)
            leg_cache[key] = (B, tr)
        B, tr = leg_cache[key]
        return config_metrics(B, tr, 0, train_hi)

    def fast_unified(ldec, sdec, lH, sH, train_hi):
        """Unified-account no-exit fast metrics on [0, train_hi)."""
        tgt, _ = unified_targets(ldec, sdec, lH, sH)
        pos = path_from_targets(tgt, ses.blocked, ses.flat, OZ)
        B = pnl_from_path(pos, o, c, ses.flat)
        return config_metrics(B, trades_from_pos(pos), 0, train_hi)

    pick_rows, notes = [], []
    for f in folds:
        t0 = time.time()
        train_hi, test_lo, test_hi = f["train_hi"], f["test_lo"], f["test_hi"]

        # ---- 1) leg screen (fast no-exit, train prefix only) ----
        cand_l, cand_s = [], []
        for factor in FAMILY:
            for W in W_GRID:
                for T in T_GRID:
                    for H in H_GRID:
                        m = leg_eval(factor, W, T, H, "long", train_hi)
                        if m["trades"] >= LEG_MIN_TRADES and m["avg_usd"] > 0:
                            cand_l.append((m["sharpe"], factor, W, T, H))
                        m = leg_eval(factor, W, T, H, "short", train_hi)
                        if m["trades"] >= LEG_MIN_TRADES and m["avg_usd"] > 0:
                            cand_s.append((m["sharpe"], factor, W, T, H))
        top_l = sorted(cand_l, key=lambda x: -x[0])[:TOP_K]
        top_s = sorted(cand_s, key=lambda x: -x[0])[:TOP_K]
        if len(top_l) < 2 or len(top_s) < 2:
            notes.append(f"{f['name']}: only {len(top_l)} long / {len(top_s)} short legs qualify")
            continue

        # ---- 2) systems x regime x session (fast no-exit, train only) ----
        sys_list = []
        for (lsh, lf, lW, lT, lH), (ssh, sf, sW, sT, sH) in product(top_l, top_s):
            ldec0, _ = leg_masks(zget(lf, lW), FAMILY[lf], lT)
            _, sdec0 = leg_masks(zget(sf, sW), FAMILY[sf], sT)
            best_rs = []
            for rg, sn in product(REGIMES, SESSIONS):
                filt = regime_masks[rg] & session_masks[sn]
                ldec, sdec = ldec0 & filt, sdec0 & filt
                if not (ldec.any() or sdec.any()):
                    continue
                m = fast_unified(ldec, sdec, lH, sH, train_hi)
                if m["trades"] >= SYS_MIN_TRADES and np.isfinite(m["sharpe"]):
                    best_rs.append((m["sharpe"], rg, sn))
            best_rs.sort(key=lambda x: -x[0])
            for sh, rg, sn in best_rs[:2]:
                sys_list.append({"lspec": f"{lf}|W{lW}|T{lT:g}|H{lH}",
                                 "sspec": f"{sf}|W{sW}|T{sT:g}|H{sH}",
                                 "ldec0": ldec0, "sdec0": sdec0, "lH": lH, "sH": sH,
                                 "regime": rg, "session": sn, "fast_sharpe": sh})

        # ---- 3) engine-scored exits on the train prefix ----
        fold_best = None
        for s in sys_list:
            filt = regime_masks[s["regime"]] & session_masks[s["session"]]
            tgt, _ = unified_targets(s["ldec0"] & filt, s["sdec0"] & filt, s["lH"], s["sH"])
            for exit_name, kw in EXITS:
                res = BacktestEngine(BacktestConfig(**kw)).run(
                    df, tgt, atr=atr_arr if kw else None)
                tr_m = seg_bar_metrics(res, 0, train_hi)
                if tr_m["trades"] < EXIT_MIN_TRADES:
                    continue
                if fold_best is None or tr_m["sharpe"] > fold_best["train_sharpe"]:
                    fold_best = {**s, "exit": exit_name, "kw": kw,
                                 "train_sharpe": tr_m["sharpe"],
                                 "train_trades": tr_m["trades"], "tgt": tgt}

        if fold_best is None:
            notes.append(f"{f['name']}: no system passed the exit gate")
            continue

        # ---- 4) execute the chosen system on the untouched test fold ----
        res = BacktestEngine(BacktestConfig(**fold_best["kw"])).run(
            df, fold_best["tgt"], atr=atr_arr if fold_best["kw"] else None)
        te = seg_bar_metrics(res, test_lo, test_hi)
        spec = (f"L:{fold_best['lspec']} + S:{fold_best['sspec']}"
                f"|regime={fold_best['regime']}|session={fold_best['session']}"
                f"|exit={fold_best['exit']}")
        pick_rows.append({
            "fold": f["name"], "test_window": f"{f['test_start']} -> {f['test_end']}",
            "spec": spec, "train_sharpe": round(fold_best["train_sharpe"], 2),
            "train_trades": fold_best["train_trades"],
            "test_sharpe": round(te["sharpe"], 2), "test_pnl": round(te["pnl"], 2),
            "test_trades": te["trades"], "test_avg": round(te["avg"], 2),
            "test_maxdd": round(te["maxdd"], 2),
            "_bar_pnl": np.diff(np.r_[res.config.initial_capital, res.equity])[test_lo:test_hi],
        })
        print(f"{f['name']}: {spec}  test ${te['pnl']:+.2f} ({te['trades']} trades) "
              f"[{time.time() - t0:.0f}s]")

    picks = pd.DataFrame([{k: v for k, v in r.items() if k != "_bar_pnl"} for r in pick_rows])
    picks.to_csv(PICKS_CSV, index=False)

    lines = [
        "# Single-Account Complete-System Walk-Forward (research period only)",
        "",
        f"- folds within research 2023-09-13 -> {ts[h_idx - 1]:%Y-%m-%d}; "
        f"consumed dev set {dev_start:%Y-%m-%d} -> {ts[-1]:%Y-%m-%d} untouched here.",
        f"- factor universe (established robust subset): {', '.join(sorted(FAMILY))}",
        f"- grid: W{list(W_GRID)} x T{list(T_GRID)} x H{list(H_GRID)}; fast no-exit screen -> "
        f"top{TOP_K} legs/side -> 3x3 unified systems",
        f"- filters: regime {list(REGIMES)} x session {list(SESSIONS)} (top-2 per system); "
        f"exits {[e[0] for e in EXITS]} scored by the event engine on train only",
        "- per fold the test segment executes only the train-chosen complete system.",
        "- sizing 1 oz; cost $0.16/oz round trip; PnL USD. Selection never sees test data.",
        "",
        "## Per-fold execution",
        "",
        md_table(picks) if not picks.empty else "(no fold produced a qualifying system)",
        "",
    ]

    if not picks.empty:
        cat = np.concatenate([r["_bar_pnl"] for r in pick_rows])
        tot_pnl = float(sum(r["test_pnl"] for r in pick_rows))
        tot_tr = int(sum(r["test_trades"] for r in pick_rows))
        pos_folds = int(sum(r["test_pnl"] > 0 for r in pick_rows))
        wf_sharpe = float(cat.mean() / cat.std() * ANN) if cat.std() > 0 else 0.0
        agg = {"folds": len(picks), "folds_positive": pos_folds,
               "wf_pnl": round(tot_pnl, 2), "wf_trades": tot_tr,
               "wf_avg": round(tot_pnl / tot_tr, 2) if tot_tr else float("nan"),
               "wf_sharpe": round(wf_sharpe, 2)}
        freq = picks["spec"].value_counts()
        static = freq[freq >= 3]
        gates_ok = pos_folds >= 3 and tot_tr >= 100 and (tot_pnl / tot_tr > 0)
        lines += [
            "## Walk-forward aggregate (fold-chosen systems)",
            "",
            md_table(pd.DataFrame([agg])),
            "",
            f"- candidate gates (>=3/4 folds positive, >=100 trades, positive avg): "
            f"{'PASS' if gates_ok else 'FAIL'}",
            "",
            "## Spec selection frequency across folds",
            "",
            md_table(freq.rename("times_chosen").reset_index()),
            "",
        ]
        if len(static):
            spec = static.index[0]
            lines += [f"- static dev candidate: `{spec}` (chosen {int(static.iloc[0])} folds)",
                      f"- dev diagnostic: run `python scripts/run_dev_diagnostic.py --spec \"{spec}\"` exactly once."]
        else:
            lines += ["- **No static candidate: no complete system was independently chosen by >= 3 folds.**",
                      "- No dev-set diagnostic is run; the next judgment requires >= 6 new continuous months of data."]
    else:
        lines += ["- **No candidate: no fold produced a qualifying system.**"]
    if notes:
        lines += ["", "notes: " + "; ".join(notes)]
    lines += ["", f"- runtime: {time.time() - t_start:.0f}s"]

    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"saved {REPORT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
