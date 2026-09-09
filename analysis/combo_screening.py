# -*- coding: utf-8 -*-
"""Combination matrix + walk-forward toolkit for the surviving XAUUSD factors.

Protocol (locked 2026-09-09):
  * the last `--holdout-days` (default 183) days of the dataset are a SEALED
    holdout: never used for selection, tuning or reporting in research mode;
  * research period = everything before the holdout start;
  * expanding-window walk-forward: 6-month test folds, selection on the train
    prefix only (the old 70/30 OOS block is now inside the research period);
  * candidates are ranked by walk-forward consistency; the final judgment of
    a locked candidate happens on the sealed holdout via `--final SPEC`.
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


def leg_masks(z: np.ndarray, side: str, T: float) -> tuple[np.ndarray, np.ndarray]:
    """(long_dec, short_dec) decision masks for one factor leg at threshold T.

    NaN z-scores never trigger (comparisons with NaN are False)."""
    if side == "high":
        return z >= T, z <= -T
    return z <= -T, z >= T


def holdout_split(ts_sec: np.ndarray, holdout_days: int = FOLD_DAYS) -> tuple[int, pd.Timestamp]:
    """Bar index where the sealed holdout starts (day-floor, holdout_days back)."""
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


def evaluate(long_dec: np.ndarray, short_dec: np.ndarray, H: int, ses: Session,
             o: np.ndarray, c: np.ndarray, n: int,
             folds: list[dict]) -> dict | None:
    """Build the position path once; metrics for the research period + per-fold
    train/test windows (train = prefix [0, test_lo), test = [test_lo, test_hi))."""
    pos, corr, trades = build_path(long_dec, short_dec, H, ses, o, c, n)
    if not trades:
        return None
    B = pnl_from_path(pos, o, c, ses.flat, corr)
    out: dict = {"_B": B, "_trades": trades,
                 "res": config_metrics(B, trades, 0, n)}
    for f in folds:
        out[f["name"]] = {
            "train": config_metrics(B, trades, 0, f["test_lo"]),
            "test": config_metrics(B, trades, f["test_lo"], f["test_hi"]),
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


def masks_from_spec(cfg: dict, zget) -> tuple[np.ndarray, np.ndarray]:
    """Decision masks for a parsed spec; zget(factor) -> z-score array."""
    if cfg["kind"] == "single":
        z = zget(cfg["factor"], cfg["win"])
        ld0, sd0 = leg_masks(z, SURVIVORS[cfg["factor"]], cfg["thr"])
        if cfg["side"] == "long":
            return ld0, np.zeros_like(ld0)
        return np.zeros_like(ld0), sd0
    names = cfg["factor"].split("+")
    ld = np.ones(len(zget(names[0], cfg["win"])), dtype=bool)
    for fn in names:
        l_, _ = leg_masks(zget(fn, cfg["win"]), SURVIVORS[fn], cfg["thr"])
        ld &= l_
    return ld, np.zeros_like(ld)
