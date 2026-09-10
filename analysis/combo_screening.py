# -*- coding: utf-8 -*-
"""Combination matrix + walk-forward toolkit for the surviving XAUUSD factors.

Protocol (validation revision 2026-09-10):
  * the last `--holdout-days` (default 183) days are a consumed development
    segment: excluded from research selection and never presented as validation;
  * research period = everything before the holdout start;
  * expanding-window walk-forward: 6-month test folds, selection on the train
    prefix only (the old 70/30 OOS block is now inside the research period);
  * candidates are ranked by walk-forward consistency. A later, newly accrued
    six-month segment is required for an independent final judgment.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from analysis.factor_screening import (
    ANN, OZ, Session, build_path, config_metrics, pnl_from_path, rolling_z,
)

FOLD_DAYS = 183

# Survivors of report/factor_screening.md: factor -> long-when side.
# "high" = long when the z-score is extreme high (momentum),
# "low"  = long when the z-score is extreme low  (reversal).
SURVIVORS: dict[str, str] = {
    "aroon_up_25": "high",
    "close_vs_ema200": "high",
    "plus_di_14": "high",
    "gap_pct": "low",
}

# Downside-momentum family for the systematic short-side study
# (scripts/run_short_study.py): factor -> "long-when" side, shorts take the
# opposite leg. aroon_up_25 z extreme LOW = no fresh highs -> decline;
# aroon_down_25 / minus_di_14 z extreme HIGH = fresh lows / down-pressure.
SHORT_FAMILY: dict[str, str] = {
    "aroon_up_25": "high",
    "aroon_down_25": "low",
    "minus_di_14": "low",
}

# Extended short family: adds close_vs_ema200 (z low -> short, below long MA)
# and rsi_14 (z high -> short, overbought reversal).
SHORT_FAMILY_EXT: dict[str, str] = {
    "aroon_up_25": "high",
    "aroon_down_25": "low",
    "minus_di_14": "low",
    "close_vs_ema200": "high",
    "rsi_14": "low",
}


def build_gates(df: pd.DataFrame) -> dict[str, np.ndarray]:
    """Boolean regime masks. True = allow trading on that bar.

    All inputs are existing indicator columns -> zero new computation."""
    c = df["close"].to_numpy()
    g = {
        "trend_up":   c > df["ema_200"].to_numpy(),
        "trend_down": c < df["ema_200"].to_numpy(),
        "adx_strong": df["adx_14"].to_numpy() > 25.0,
        "not_choppy": df["choppiness_14"].to_numpy() < 50.0,
        "aroon_up":   df["aroon_up_25"].to_numpy() > df["aroon_down_25"].to_numpy(),
        "aroon_dn":   df["aroon_down_25"].to_numpy() > df["aroon_up_25"].to_numpy(),
    }
    return {k: np.asarray(v, dtype=bool) for k, v in g.items()}


def leg_masks(z: np.ndarray, side: str, T: float) -> tuple[np.ndarray, np.ndarray]:
    """(long_dec, short_dec) decision masks for one factor leg at threshold T.

    NaN z-scores never trigger (comparisons with NaN are False)."""
    if side == "high":
        return z >= T, z <= -T
    return z <= -T, z >= T


def holdout_split(ts_sec: np.ndarray, holdout_days: int = FOLD_DAYS) -> tuple[int, pd.Timestamp]:
    """Bar index where the excluded consumed development segment starts."""
    t = pd.to_datetime(ts_sec, unit="s").to_numpy()
    start = (t[-1] - np.timedelta64(holdout_days, "D")).astype("datetime64[D]")
    start = start.astype("datetime64[ns]")
    return int(np.searchsorted(t, start, side="left")), pd.Timestamp(start)


def fold_list(ts_sec: np.ndarray, research_end: int, n_folds: int,
              fold_days: int = FOLD_DAYS) -> list[dict]:
    """Expanding-window walk-forward folds over the research period.

    Test folds are the last `n_folds` blocks of `fold_days` days, chronological
    (earliest test first); the train window of fold j is the full prefix [0, test_lo)."""
    t = pd.to_datetime(ts_sec[:research_end], unit="s").to_numpy()
    edges = [t[-1] - np.timedelta64(fold_days * k, "D") for k in range(n_folds, -1, -1)]
    idx = [int(np.searchsorted(t, e, side="left")) for e in edges]
    folds: list[dict] = []
    for j in range(n_folds):
        lo, hi = idx[j], idx[j + 1]
        if lo <= 0 or hi - lo < 1000:
            continue
        folds.append({
            "name": f"f{j + 1}",
            "test_start": pd.Timestamp(t[lo]).date().isoformat(),
            "test_end": pd.Timestamp(t[hi - 1]).date().isoformat(),
            "train_hi": lo, "test_lo": lo, "test_hi": hi,
        })
    return folds


def build_path_stopped(long_dec: np.ndarray, short_dec: np.ndarray, H: int,
                       ses: Session, o: np.ndarray, c: np.ndarray, n: int,
                       atr: np.ndarray | None = None,
                       stop_atr: float | None = None,
                       trail_atr: float | None = None,
                       target_atr: float | None = None
                       ) -> tuple[np.ndarray, np.ndarray, list[tuple]]:
    """Fixed-hold path with optional ATR stop-loss / trailing / target exits.

    Stops are checked at each bar's CLOSE (mark-to-close).  When a stop fires
    the position exits at that close (corrected via corr, same mechanism as
    session-flat exits).  When no stop fires the behaviour is identical to
    build_path (exit at open after H bars or session event)."""
    from analysis.factor_screening import build_path
    if atr is None or (stop_atr is None and trail_atr is None and target_atr is None):
        return build_path(long_dec, short_dec, H, ses, o, c, n)

    cand = np.flatnonzero(long_dec | short_dec)
    pos = np.zeros(n)
    corr = np.zeros(n)
    trades: list[tuple] = []
    if len(cand) == 0:
        return pos, corr, trades
    cand = cand[~ses.blocked[cand]]
    fi, bi = ses.flat_idx, ses.blocked_idx
    prev_e = -1
    for d in cand:
        f = d + 1
        if f <= prev_e or f > n - 2:
            continue
        s = 1.0 if long_dec[d] else -1.0
        entry_px = o[f]
        max_fav = 0.0  # max favorable excursion for trailing
        e = f + H
        stopped = False
        for i in range(f, min(e, n)):
            # session check
            if ses.blocked[i]:
                last, e_eff = i, i + 1
                if e_eff > n - 1:
                    break
                if ses.flat[i]:
                    corr[e_eff] = -s * OZ * (o[e_eff] - c[i])
                else:
                    pass  # blocked non-flat: exit at open next bar (no corr)
                stopped = True
                break
            if ses.flat[i] and i > f:
                last, e_eff = i, i + 1
                if e_eff > n - 1:
                    break
                corr[e_eff] = -s * OZ * (o[e_eff] - c[i])
                stopped = True
                break
            # stop checks (mark-to-close)
            fav = s * (c[i] - entry_px)
            max_fav = max(max_fav, fav)
            a = atr[i] if np.isfinite(atr[i]) and atr[i] > 0 else 0.0
            if a > 0:
                if stop_atr is not None and fav <= -stop_atr * a:
                    last, e_eff = i, i + 1
                    if e_eff > n - 1:
                        break
                    corr[e_eff] = -s * OZ * (o[e_eff] - c[i])
                    stopped = True
                    break
                if target_atr is not None and fav >= target_atr * a:
                    last, e_eff = i, i + 1
                    if e_eff > n - 1:
                        break
                    corr[e_eff] = -s * OZ * (o[e_eff] - c[i])
                    stopped = True
                    break
                if trail_atr is not None and i > f and fav <= max_fav - trail_atr * a:
                    last, e_eff = i, i + 1
                    if e_eff > n - 1:
                        break
                    corr[e_eff] = -s * OZ * (o[e_eff] - c[i])
                    stopped = True
                    break
        if not stopped:
            last, e_eff = e - 1, e
            if e_eff > n - 1:
                continue
        pos[f:last + 1] = s * OZ
        trades.append((f, e_eff, s, last))
        prev_e = e_eff
    return pos, corr, trades


def evaluate(long_dec: np.ndarray, short_dec: np.ndarray, H: int, ses: Session,
             o: np.ndarray, c: np.ndarray, n: int,
             folds: list[dict], atr: np.ndarray | None = None,
             stop_atr: float | None = None, trail_atr: float | None = None,
             target_atr: float | None = None, ann: float = ANN) -> dict | None:
    """Build the position path once; metrics for the research period + per-fold
    train/test windows (train = prefix [0, test_lo), test = [test_lo, test_hi)).

    When atr + stop/trail/target are provided, uses build_path_stopped for
    ATR-based dynamic exits; otherwise uses the fixed-hold build_path."""
    if atr is not None and (stop_atr or trail_atr or target_atr):
        pos, corr, trades = build_path_stopped(long_dec, short_dec, H, ses,
                                               o, c, n, atr,
                                               stop_atr, trail_atr, target_atr)
    else:
        pos, corr, trades = build_path(long_dec, short_dec, H, ses, o, c, n)
    if not trades:
        return None
    B = pnl_from_path(pos, o, c, ses.flat, corr)
    out: dict = {"_B": B, "_trades": trades,
                 "res": config_metrics(B, trades, 0, n, ann=ann)}
    for f in folds:
        out[f["name"]] = {
            "train": config_metrics(B, trades, 0, f["test_lo"], ann=ann),
            "test": config_metrics(B, trades, f["test_lo"], f["test_hi"], ann=ann),
        }
    return out


def flatten(base: dict, ev: dict, folds: list[dict]) -> dict:
    """Flatten an evaluate() result into one CSV/report row."""
    row = dict(base)
    r = ev["res"]
    row.update({"res_sharpe": r["sharpe"], "res_pnl": r["pnl"],
                "res_trades": r["trades"], "res_avg": r["avg_usd"],
                "res_pf": r["pf"], "res_maxdd": r["maxdd"]})
    for f in folds:
        k = f["name"]
        tr, te = ev[k]["train"], ev[k]["test"]
        row.update({f"{k}_train_sharpe": tr["sharpe"], f"{k}_train_trades": tr["trades"],
                    f"{k}_train_avg": tr["avg_usd"],
                    f"{k}_test_sharpe": te["sharpe"], f"{k}_test_pnl": te["pnl"],
                    f"{k}_test_trades": te["trades"], f"{k}_test_avg": te["avg_usd"],
                    f"{k}_test_pf": te["pf"]})
    return row


def spec_string(base: dict) -> str:
    """Machine-readable config spec, e.g. 'combo|aroon_up_25+gap_pct|long|W6048|T1.5|H84'."""
    if base["kind"] == "combo":
        fkey = base["factor"]
    else:
        fkey = base["factor"]
    return (f"{base['kind']}|{fkey}|{base['side']}"
            f"|W{int(base['win'])}|T{base['thr']:g}|H{int(base['hold'])}")


def parse_spec(spec: str) -> dict:
    kind, fkey, side, wtok, ttok, htok = spec.split("|")
    return {"kind": kind, "factor": fkey, "side": side,
            "win": int(wtok[1:]), "thr": float(ttok[1:]), "hold": int(htok[1:])}


def masks_from_spec(cfg: dict, zget, side_map: dict | None = None,
                    long_gate: np.ndarray | None = None,
                    short_gate: np.ndarray | None = None
                    ) -> tuple[np.ndarray, np.ndarray]:
    """Decision masks for a parsed spec; zget(factor) -> z-score array.

    side_map: factor -> "long-when" side (default SURVIVORS).  For the short
    study pass SHORT_FAMILY_EXT so the leg direction matches the family.
    long_gate / short_gate: boolean arrays ANDed with the respective decisions
    (regime filters)."""
    sm = side_map if side_map is not None else SURVIVORS
    if cfg["kind"] == "single":
        z = zget(cfg["factor"], cfg["win"])
        ld0, sd0 = leg_masks(z, sm[cfg["factor"]], cfg["thr"])
        if cfg["side"] == "long":
            ld, sd_ = ld0, np.zeros_like(ld0)
        else:
            ld, sd_ = np.zeros_like(ld0), sd0
    else:
        names = cfg["factor"].split("+")
        ld = np.ones(len(zget(names[0], cfg["win"])), dtype=bool)
        for fn in names:
            l_, _ = leg_masks(zget(fn, cfg["win"]), sm[fn], cfg["thr"])
            ld &= l_
        sd_ = np.zeros_like(ld)
    if long_gate is not None:
        ld = ld & long_gate
    if short_gate is not None:
        sd_ = sd_ & short_gate
    return ld, sd_


def md_table(df: pd.DataFrame, floatfmt: str = "{:.2f}") -> str:
    """Render a DataFrame as a GitHub-flavored markdown table."""
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
                cells.append(floatfmt.format(v) if pd.notna(v) else "-")
            else:
                cells.append(str(v))
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


def walk_forward(grid: pd.DataFrame, folds: list[dict], gate: int, zget,
                 ses: Session, o: np.ndarray, c: np.ndarray,
                 n: int, side_map: dict | None = None,
                 long_gate: np.ndarray | None = None,
                 short_gate: np.ndarray | None = None,
                 atr: np.ndarray | None = None,
                 stop_atr: float | None = None,
                 trail_atr: float | None = None,
                 target_atr: float | None = None,
                 ann: float = ANN
                 ) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Walk-forward selection simulation.

    Per fold: pick the best train-Sharpe config among gated ones, apply it to
    the untouched test fold; aggregate the fold segments into one equity."""
    picks = []
    for f in folds:
        k = f["name"]
        cand = grid[(grid[f"{k}_train_trades"] >= gate) &
                    (grid[f"{k}_train_avg"] > 0) & grid[f"{k}_train_sharpe"].notna()]
        if cand.empty:
            continue
        best = cand.sort_values(f"{k}_train_sharpe", ascending=False).iloc[0]
        picks.append({"fold": k, "test_window": f"{f['test_start']} -> {f['test_end']}",
                      "spec": best["spec"],
                      "train_sharpe": best[f"{k}_train_sharpe"],
                      "train_trades": int(best[f"{k}_train_trades"]),
                      "test_sharpe": best[f"{k}_test_sharpe"],
                      "test_pnl": best[f"{k}_test_pnl"],
                      "test_trades": int(best[f"{k}_test_trades"]),
                      "test_avg": best[f"{k}_test_avg"],
                      "test_pf": best[f"{k}_test_pf"]})
    if not picks:
        return pd.DataFrame(), pd.DataFrame()
    picks_df = pd.DataFrame(picks)
    # aggregate: rebuild each selected config's path, concatenate test segments
    segs, tot_pnl, tot_tr, pos_folds = [], 0.0, 0, 0
    for p in picks:
        cfg = parse_spec(p["spec"])
        ld, sd_ = masks_from_spec(cfg, zget, side_map, long_gate, short_gate)
        ev = evaluate(ld, sd_, cfg["hold"], ses, o, c, n, [], atr,
                      stop_atr, trail_atr, target_atr, ann=ann)
        B = ev["_B"]
        f = next(x for x in folds if x["name"] == p["fold"])
        seg = B[f["test_lo"]:f["test_hi"]]
        segs.append(seg)
        tot_pnl += float(seg.sum())
        tot_tr += int(p["test_trades"])
        pos_folds += int(p["test_pnl"] > 0)
    cat = np.concatenate(segs)
    agg = {"folds": len(picks), "folds_positive": pos_folds,
           "wf_pnl": round(tot_pnl, 0), "wf_trades": tot_tr,
           "wf_avg": round(tot_pnl / tot_tr, 2) if tot_tr else float("nan"),
           "wf_sharpe": round(float(cat.mean() / cat.std() * ann), 2) if cat.std() > 0 else 0.0}
    return picks_df, pd.DataFrame([agg])
