# -*- coding: utf-8 -*-
"""Factor screening toolkit for the XAUUSD 5m dataset.

Provides:
  build_factors(df)   -> 56 scale-free factors derived from the 64-indicator set
  rolling_z(s, W)     -> trailing z-score (rolling mean/std, min_periods=W//2)
  session_masks(ts)   -> (flat, blocked) boolean masks, identical to the engine's
  pnl_from_path(...)  -> exact mid-accounting per-bar PnL from a position path
  build_path(...)     -> greedy fixed-hold position path from entry decisions
  ic_stats(...)       -> monthly Spearman IC table per factor x horizon
  decile_profile(...) -> forward-return profile across factor quantile bins

Cost model: all-in 0.16 USD/oz round trip -> 0.08 per side (Gate.io actual).
The fast vectorized accounting is mathematically identical to BacktestEngine
(mid fills, next-open execution, session flat at cutoff); top configurations
are re-confirmed with the real engine in scripts/run_screening.py.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from backtest import BacktestConfig, BacktestEngine

COST_SIDE = 0.08          # USD/oz per side (0.16 all-in round trip)
ANN = np.sqrt(288 * 252)  # annualization for 5m bars (library convention)
OZ = 100.0                # 1 unit of signal = 100 oz

# ----------------------------------------------------------------------
# Factor universe: 56 scale-free factors from the 64 indicator columns
# ----------------------------------------------------------------------
FACTOR_GROUPS: dict[str, list[str]] = {}

def _reg(group: str, names: list[str]) -> None:
    FACTOR_GROUPS[group] = names


def build_factors(df: pd.DataFrame) -> pd.DataFrame:
    """Derive scale-free factors. All transforms use current/past data only."""
    c = df["close"]
    F = pd.DataFrame(index=df.index)

    ma = [f"close_vs_sma{p}" for p in (10, 20, 50, 200)] + \
         [f"close_vs_ema{p}" for p in (9, 12, 21, 26, 50, 200)] + \
         ["close_vs_wma20"]
    for p in (10, 20, 50, 200):
        F[f"close_vs_sma{p}"] = (c / df[f"sma_{p}"] - 1.0) * 100.0
    for p in (9, 12, 21, 26, 50, 200):
        F[f"close_vs_ema{p}"] = (c / df[f"ema_{p}"] - 1.0) * 100.0
    F["close_vs_wma20"] = (c / df["wma_20"] - 1.0) * 100.0
    _reg("trend/MA distance (11)", ma)

    macd = ["macd_dif_pct", "macd_dea_pct", "macd_hist_pct"]
    for k in macd:
        F[k] = df[k.replace("_pct", "")] / c * 100.0
    _reg("MACD normalized (3)", macd)

    mom = ["rsi_6", "rsi_14", "rsi_24", "stoch_k_14", "stoch_d_14", "stochrsi_k",
           "stochrsi_d", "kdj_k", "kdj_d", "kdj_j", "cci_14", "williams_r_14",
           "roc_12", "momentum_10_pct"]
    for k in mom[:-1]:
        F[k] = df[k]
    F["momentum_10_pct"] = df["momentum_10"] / c * 100.0
    _reg("momentum oscillators (14)", mom)

    vol = ["tr_pct", "atr_7_pct", "natr_14", "atr_28_pct", "bb_width", "bb_pct_b",
           "kc_pos", "donchian_pos"]
    F["tr_pct"] = df["tr"] / c * 100.0
    F["atr_7_pct"] = df["atr_7"] / c * 100.0
    F["natr_14"] = df["natr_14"]
    F["atr_28_pct"] = df["atr_28"] / c * 100.0
    F["bb_width"] = df["bb_width"]
    F["bb_pct_b"] = df["bb_pct_b"]
    span = (df["kc_up"] - df["kc_low"]).where(lambda x: x != 0)
    F["kc_pos"] = (c - df["kc_low"]) / span
    dspan = (df["donchian_up_20"] - df["donchian_low_20"]).where(lambda x: x != 0)
    F["donchian_pos"] = (c - df["donchian_low_20"]) / dspan
    _reg("volatility/channel position (8)", vol)

    ts_ = ["adx_14", "plus_di_14", "minus_di_14", "aroon_up_25", "aroon_down_25",
           "psar_dist_pct"]
    for k in ts_[:-1]:
        F[k] = df[k]
    F["psar_dist_pct"] = (c / df["psar"] - 1.0) * 100.0
    _reg("trend strength (6)", ts_)

    stat = ["zscore_20", "linreg_slope_20", "hv_20", "hv_96", "hv_ratio",
            "choppiness_14", "candle_body_pct", "upper_shadow_pct",
            "lower_shadow_pct", "hl_range_pct", "gap_pct", "clv",
            "close_vs_ema200_pct", "close_vs_sma20_pct"]
    for k in stat:
        F[k] = df[k]
    _reg("statistical/micro (14)", stat)

    # composite factors (Phase 4)
    comp = ["di_spread", "aroon_osc", "di_ratio", "bb_squeeze", "vol_percentile"]
    F["di_spread"] = df["plus_di_14"] - df["minus_di_14"]
    F["aroon_osc"] = df["aroon_up_25"] - df["aroon_down_25"]
    mdi = df["minus_di_14"].replace(0.0, np.nan)
    F["di_ratio"] = (df["plus_di_14"] / mdi).clip(-10, 10)
    bw = df["bb_width"]
    F["bb_squeeze"] = ((bw - bw.rolling(96, min_periods=48).mean()) /
                       bw.rolling(96, min_periods=48).std().replace(0.0, np.nan))
    F["vol_percentile"] = df["natr_14"].rolling(96, min_periods=48).rank(pct=True) * 100.0
    _reg("composite (5)", comp)

    return F


def factor_list() -> list[str]:
    out: list[str] = []
    for names in FACTOR_GROUPS.values():
        out.extend(names)
    return out


# ----------------------------------------------------------------------
# Rolling z-score
# ----------------------------------------------------------------------
def rolling_z(s: pd.Series, W: int) -> np.ndarray:
    mp = max(2, W // 2)
    m = s.rolling(W, min_periods=mp).mean()
    sd = s.rolling(W, min_periods=mp).std()
    return ((s - m) / sd.replace(0.0, np.nan)).to_numpy()


# ----------------------------------------------------------------------
# Session masks (identical rules to BacktestEngine)
# ----------------------------------------------------------------------
class Session:
    def __init__(self, ts_sec: np.ndarray):
        eng = BacktestEngine(BacktestConfig())
        self.flat, self.blocked = eng._session_masks(ts_sec, True)
        self.flat_idx = np.flatnonzero(self.flat)
        self.blocked_idx = np.flatnonzero(self.blocked)


# ----------------------------------------------------------------------
# Exact per-bar PnL from a position path (mid accounting, == engine)
# ----------------------------------------------------------------------
def pnl_from_path(pos: np.ndarray, o: np.ndarray, c: np.ndarray,
                  flat: np.ndarray, corr: np.ndarray | None = None,
                  cost_side: float = COST_SIDE) -> np.ndarray:
    """B[i] = pos[i-1]*(o[i]-c[i-1]) + pos[i]*(c[i]-o[i]) - cost*|dpos| (+corr).

    pos[k] = oz held during bar k (after the open fill). Session exits at the
    close of a flat bar are corrected via corr (engine exits at close, not at
    the next open)."""
    n = len(pos)
    B = np.zeros(n)
    if n < 2:
        return B
    B[1:] = (pos[:-1] * (o[1:] - c[:-1]) +
             pos[1:] * (c[1:] - o[1:]) -
             cost_side * np.abs(np.diff(pos)))
    if corr is not None:
        B[1:] += corr[1:]
    else:
        fe = np.flatnonzero(flat & (pos != 0.0))
        fe = fe[fe + 1 < n]
        B[fe + 1] += -pos[fe] * (o[fe + 1] - c[fe])
    # BacktestEngine force-closes any remaining terminal position at the last
    # close.  The mark-to-close gain is already present above; charge its final
    # exit side so a dataset that ends before the session cutoff still matches.
    if pos[-1] != 0.0:
        B[-1] -= cost_side * abs(pos[-1])
    return B


def path_from_targets(tgt: np.ndarray, blocked: np.ndarray, flat: np.ndarray,
                      max_oz: float = OZ) -> np.ndarray:
    """Engine-equivalent position path from per-bar target decisions."""
    d = np.where(np.isfinite(tgt), tgt, 0.0)
    d = np.clip(d, -max_oz, max_oz)
    d[blocked] = 0.0
    pos = np.zeros(len(d))
    pos[1:] = np.where(flat[:-1], 0.0, d[:-1])
    return pos


# ----------------------------------------------------------------------
# Greedy fixed-hold path builder (no pyramiding, no mid-hold flips)
# ----------------------------------------------------------------------
def build_path(long_dec: np.ndarray, short_dec: np.ndarray, H: int,
               ses: Session, o: np.ndarray, c: np.ndarray,
               n: int) -> tuple[np.ndarray, np.ndarray, list[tuple]]:
    """Entry decisions at close -> fill next open -> hold H bars -> exit at open.

    Session rules mirror the engine: entry decisions on blocked bars are
    dropped; a position is cut at the close of the first flat bar in its hold
    window, or at the open after the first (non-flat) blocked bar."""
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
        e = f + H                                    # fixed-hold exit fill bar
        j = np.searchsorted(bi, f)
        kb = bi[j] if j < len(bi) else n             # first blocked bar >= f
        j2 = np.searchsorted(fi, f)
        kf = fi[j2] if j2 < len(fi) else n           # first flat bar >= f
        if kb < e:                                   # session interferes
            last, e_eff = kb, kb + 1
            if kf == kb:                             # flat -> exit at close kb
                if e_eff > n - 1:
                    continue
                corr[e_eff] = -s * OZ * (o[e_eff] - c[kb])
        else:
            last, e_eff = e - 1, e
            if e_eff > n - 1:
                continue
        pos[f:last + 1] = s * OZ
        trades.append((f, e_eff, s, last))
        prev_e = e_eff
    return pos, corr, trades


# ----------------------------------------------------------------------
# Config metrics
# ----------------------------------------------------------------------
def config_metrics(B: np.ndarray, trades: list[tuple], lo: int, hi: int,
                   ann: float = ANN) -> dict:
    """Metrics from a per-bar PnL series already denominated in USD (pos in oz)."""
    b = B[lo:hi]
    if len(b) == 0:
        return {"pnl": float("nan"), "trades": 0, "avg_usd": float("nan"),
                "pf": float("nan"), "sharpe": float("nan"), "maxdd": float("nan")}
    tot = float(b.sum())
    sd = float(b.std())
    sharpe = float(b.mean() / sd * ann) if sd > 0 else 0.0
    cum = np.cumsum(b)
    maxdd = float((cum - np.maximum.accumulate(cum)).min()) if len(cum) else 0.0

    cb = np.cumsum(B)
    tn = []
    for (f, e, s, last) in trades:
        if lo <= f < hi:
            tn.append(cb[min(e, len(B) - 1)] - cb[f - 1])
    tn = np.asarray(tn)
    ntr = int(len(tn))
    if ntr and tn.std() == 0:
        pf = float("inf") if tn.sum() > 0 else 0.0
    elif ntr:
        gp = tn[tn > 0].sum()
        gl = -tn[tn < 0].sum()
        pf = float(gp / gl) if gl > 0 else float("inf")
    else:
        pf = float("nan")
    return {
        "pnl": round(tot, 0),
        "trades": ntr,
        "avg_usd": round(float(tn.mean()), 2) if ntr else float("nan"),
        "pf": round(pf, 3) if ntr else float("nan"),
        "sharpe": round(sharpe, 2),
        "maxdd": round(maxdd, 0),
    }


# ----------------------------------------------------------------------
# Information coefficient
# ----------------------------------------------------------------------
def _spearman(a: np.ndarray, b: np.ndarray, min_n: int = 200) -> float:
    m = np.isfinite(a) & np.isfinite(b)
    if m.sum() < min_n:
        return float("nan")
    ra = pd.Series(a[m]).rank().to_numpy()
    rb = pd.Series(b[m]).rank().to_numpy()
    sa, sb = ra.std(), rb.std()
    if sa == 0 or sb == 0:
        return float("nan")
    return float(np.corrcoef(ra, rb)[0, 1])


def forward_returns(close: np.ndarray, h: int) -> np.ndarray:
    fwd = np.full(len(close), np.nan)
    fwd[:-h] = close[h:] / close[:-h] - 1.0
    return fwd


def ic_stats(F: pd.DataFrame, close: np.ndarray, ts: pd.Series, is_end: int,
             horizons: tuple[int, ...] = (12, 84, 288)) -> pd.DataFrame:
    """Monthly Spearman IC on IS + full-sample IS/OOS Spearman per factor."""
    per = ts.dt.to_period("M").to_numpy()
    rows = []
    for col in F.columns:
        x = F[col].to_numpy()
        for h in horizons:
            fwd = forward_returns(close, h)
            by_m: dict = {}
            for i in range(is_end):
                by_m.setdefault(per[i], []).append(i)
            ics = []
            for _, idx in by_m.items():
                idx = np.asarray(idx)
                ic = _spearman(x[idx], fwd[idx], min_n=100)
                if np.isfinite(ic):
                    ics.append(ic)
            ics = np.asarray(ics)
            is_spr = _spearman(x[:is_end], fwd[:is_end])
            oos_spr = _spearman(x[is_end:], fwd[is_end:])
            if len(ics) > 2 and ics.std() > 0:
                icm, icsd = ics.mean(), ics.std()
                icir = icm / icsd
                t = icir * np.sqrt(len(ics))
            else:
                icm = ics.mean() if len(ics) else float("nan")
                icir = t = float("nan")
                icsd = float("nan")
            rows.append({
                "factor": col, "h": h,
                "ic_mean": round(float(icm), 5),
                "ic_std": round(float(icsd), 5) if np.isfinite(icsd) else float("nan"),
                "icir": round(float(icir), 3) if np.isfinite(icir) else float("nan"),
                "t": round(float(t), 2) if np.isfinite(t) else float("nan"),
                "pos_pct": round(float((ics > 0).mean()), 3) if len(ics) else float("nan"),
                "is_spr": round(float(is_spr), 5) if np.isfinite(is_spr) else float("nan"),
                "oos_spr": round(float(oos_spr), 5) if np.isfinite(oos_spr) else float("nan"),
                "months": int(len(ics)),
            })
    return pd.DataFrame(rows)


def decile_profile(x: np.ndarray, fwd: np.ndarray, is_end: int,
                   q: int = 10) -> pd.DataFrame:
    """Mean forward return per factor quantile bin (bins from IS only)."""
    xis = x[:is_end]
    m = np.isfinite(xis) & np.isfinite(fwd[:is_end])
    edges = np.nanquantile(xis[m], np.linspace(0, 1, q + 1)[1:-1])
    edges = np.unique(edges)
    if len(edges) < 3:
        return pd.DataFrame()
    out = []
    for name, sl in (("IS", slice(0, is_end)), ("OOS", slice(is_end, None))):
        xx, ff = x[sl], fwd[sl]
        mm = np.isfinite(xx) & np.isfinite(ff)
        bins = np.searchsorted(edges, xx[mm])
        dfb = pd.DataFrame({"bin": bins, "fwd": ff[mm]}).groupby("bin")["fwd"]
        for b, v in dfb:
            out.append({"seg": name, "bin": int(b) + 1, "n": int(v.count()),
                        "fwd_bp": round(float(v.mean()) * 1e4, 2)})
    return pd.DataFrame(out).pivot(index="bin", columns="seg", values="fwd_bp")
