"""Shared single-account research primitives.

All selection callers pass only a research slice.  Feature calculations are
trailing and may receive earlier bars, but never use bars after the slice.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict

import numpy as np
import pandas as pd

from analysis.combo_screening import SHORT_FAMILY_EXT, build_gates, leg_masks
from analysis.factor_screening import ANN, OZ, Session, build_factors, pnl_from_path, rolling_z
from backtest import BacktestConfig, BacktestEngine

LONG_FAMILY = {
    "plus_di_14": "high", "aroon_up_25": "high", "di_ratio": "high",
    "atr_28_pct": "low", "natr_14": "low", "bb_squeeze": "high",
}
SHORT_FAMILY = {k: SHORT_FAMILY_EXT[k] for k in
                ("aroon_down_25", "minus_di_14", "close_vs_ema200", "rsi_14")}
WINDOWS = (2016, 6048)
THRESHOLDS = (1.5, 2.0)
HOLDS = (12, 84)
REGIMES = ("none", "trend", "trend_adx", "trend_not_choppy")
SESSIONS = ("all", "london", "new_york", "overlap")
EXITS = (
    ("none", {}), ("stop2", {"stop_loss_atr": 2.0}),
    ("stop2_5", {"stop_loss_atr": 2.5}),
    ("trail3", {"trailing_stop_atr": 3.0}),
    ("trail4", {"trailing_stop_atr": 4.0}),
    ("target3", {"take_profit_atr": 3.0}),
    ("stop2_trail3", {"stop_loss_atr": 2.0, "trailing_stop_atr": 3.0}),
)


@dataclass(frozen=True)
class Component:
    side: str
    factor: str
    direction: str
    window: int
    threshold: float
    hold: int
    regime: str
    session: str

    @property
    def key(self) -> str:
        return (f"{self.side}:{self.factor}:W{self.window}:T{self.threshold:g}:H{self.hold}:"
                f"{self.regime}:{self.session}")


def components(side: str, windows: tuple[int, ...] | None = None,
               holds: tuple[int, ...] | None = None) -> list[Component]:
    family = LONG_FAMILY if side == "long" else SHORT_FAMILY
    ws = WINDOWS if windows is None else windows
    hs = HOLDS if holds is None else holds
    return [Component(side, factor, direction, w, t, h, regime, session)
            for factor, direction in family.items() for w in ws for t in THRESHOLDS
            for h in hs for regime in REGIMES for session in SESSIONS]


# Legacy pre-revision integrated system (report/system_attribution.md frozen
# spec); attribution and vol-target studies must reproduce its $+1,162.17
# research PnL, so this spec is pinned, not grid-searched.
LONG_ATTR = Component("long", "plus_di_14", LONG_FAMILY["plus_di_14"],
                      6048, 1.5, 120, "trend_adx", "all")
SHORT_ATTR = Component("short", "close_vs_ema200", SHORT_FAMILY["close_vs_ema200"],
                       6048, 1.5, 120, "trend_adx", "all")


def session_mask(ts: np.ndarray, name: str, bar_seconds: int = 300) -> np.ndarray:
    if name == "all":
        return np.ones(len(ts), dtype=bool)
    close_min = ((ts + bar_seconds) % 86400) // 60
    bounds = {"london": (7 * 60, 17 * 60), "new_york": (13 * 60, 21 * 60),
              "overlap": (13 * 60, 17 * 60)}
    lo, hi = bounds[name]
    return (close_min >= lo) & (close_min < hi)


def regime_mask(df: pd.DataFrame, side: str, name: str, gates: dict[str, np.ndarray] | None = None) -> np.ndarray:
    g = gates if gates is not None else build_gates(df)
    if name == "none":
        return np.ones(len(df), dtype=bool)
    trend = g["trend_up"] if side == "long" else g["trend_down"]
    if name == "trend":
        return trend
    if name == "trend_adx":
        return trend & g["adx_strong"]
    if name == "trend_not_choppy":
        return trend & g["not_choppy"]
    raise ValueError(f"unknown regime {name}")


def decisions(df: pd.DataFrame, component: Component, factors: pd.DataFrame | None = None,
              gates: dict[str, np.ndarray] | None = None,
              bar_seconds: int = 300) -> np.ndarray:
    factors = factors if factors is not None else build_factors(df)
    z = rolling_z(factors[component.factor], component.window)
    long_dec, short_dec = leg_masks(z, component.direction, component.threshold)
    base = long_dec if component.side == "long" else short_dec
    return base & regime_mask(df, component.side, component.regime, gates) & session_mask(
        df["timestamp"].to_numpy(np.int64), component.session, bar_seconds)


def unified_targets(long_dec: np.ndarray, short_dec: np.ndarray, long_hold: int,
                    short_hold: int, oz: float = OZ) -> tuple[np.ndarray, int]:
    out = np.zeros(len(long_dec))
    side, expires, conflicts = 0, -1, 0
    for i in range(len(out)):
        if side and i >= expires:
            side = 0
        if long_dec[i] and short_dec[i]:
            side, expires, conflicts = 0, i, conflicts + 1
        elif long_dec[i] and side != 1:
            side, expires = 1, i + long_hold - 1
        elif short_dec[i] and side != -1:
            side, expires = -1, i + short_hold - 1
        out[i] = side * oz
    return out, conflicts


def system_target(df: pd.DataFrame, long: Component | None, short: Component | None,
                  factors: pd.DataFrame | None = None, gates: dict[str, np.ndarray] | None = None,
                  oz: float = OZ, bar_seconds: int = 300) -> tuple[np.ndarray, int]:
    ld = decisions(df, long, factors, gates, bar_seconds) if long else np.zeros(len(df), dtype=bool)
    sd = decisions(df, short, factors, gates, bar_seconds) if short else np.zeros(len(df), dtype=bool)
    return unified_targets(ld, sd, long.hold if long else 1, short.hold if short else 1, oz)


def bar_metrics(result, lo: int = 0, hi: int | None = None, ann: float = ANN) -> dict:
    hi = len(result.equity) if hi is None else hi
    pnl = np.diff(np.r_[result.config.initial_capital, result.equity])[lo:hi]
    curve = np.cumsum(pnl)
    dd = float((curve - np.maximum.accumulate(curve)).min()) if len(curve) else 0.0
    sharpe = float(pnl.mean() / pnl.std() * ann) if len(pnl) > 2 and pnl.std() else 0.0
    return {"pnl": float(pnl.sum()), "sharpe": sharpe, "maxdd": dd}


def run_engine(df: pd.DataFrame, long: Component | None, short: Component | None,
               exit_name: str = "none", factors: pd.DataFrame | None = None,
               gates: dict[str, np.ndarray] | None = None, oz: float = OZ,
               bar_seconds: int = 300):
    exit_args = dict(EXITS)[exit_name]
    target, conflicts = system_target(df, long, short, factors, gates, oz,
                                      bar_seconds=bar_seconds)
    result = BacktestEngine(BacktestConfig(max_position_oz=oz, bar_seconds=bar_seconds,
                                           **exit_args)).run(
        df, target, atr=df["atr_14"].to_numpy(float) if exit_args else None,
        meta={"long": asdict(long) if long else None, "short": asdict(short) if short else None,
              "exit": exit_name, "conflicts": conflicts},
    )
    return result, target, bar_metrics(result), conflicts


def fast_component_score(df: pd.DataFrame, component: Component, factors: pd.DataFrame | None = None,
                         gates: dict[str, np.ndarray] | None = None, bar_seconds: int = 300,
                         ann: float = ANN) -> dict:
    target, _ = system_target(df, component if component.side == "long" else None,
                              component if component.side == "short" else None, factors, gates,
                              bar_seconds=bar_seconds)
    ses = Session(df["timestamp"].to_numpy(np.int64), bar_seconds=bar_seconds)
    pos = np.zeros(len(df))
    pos[1:] = np.where(ses.flat[:-1], 0.0, target[:-1])
    B = pnl_from_path(pos, df["open"].to_numpy(float), df["close"].to_numpy(float), ses.flat)
    sharpe = float(B.mean() / B.std() * ann) if B.std() else 0.0
    return {"component": component, "pnl": float(B.sum()), "sharpe": sharpe,
            "trades_proxy": int(np.count_nonzero(np.diff(pos))), "avg": float(B.sum() / max(np.count_nonzero(np.diff(pos)) / 2, 1))}


def atr_size_series(atr: np.ndarray, ref_oz: float = 1.0, med_window: int = 2016,
                    min_periods: int = 288, floor: float = 0.25,
                    cap: float = 2.0) -> np.ndarray:
    """Trailing ATR risk budget: clip(ref_oz * med_t / atr_t, floor, cap).

    med_t is the trailing (expanding-until-full) median of atr; bars with a
    non-finite/non-positive atr fall back to `floor`.  Output at t depends on
    atr[..t] only.
    """
    med = pd.Series(atr).rolling(med_window, min_periods=min_periods).median().to_numpy()
    with np.errstate(invalid="ignore", divide="ignore"):
        ratio = np.where(np.isfinite(atr) & (atr > 0) & np.isfinite(med),
                         ref_oz * med / np.where(atr > 0, atr, 1.0), np.nan)
    size = np.clip(ratio, floor, cap)
    return np.where(np.isfinite(size), size, floor)


def vol_scaled_target(df: pd.DataFrame, long: Component | None, short: Component | None,
                      ref_oz: float = 1.0, med_window: int = 2016, min_periods: int = 288,
                      floor: float = 0.25, cap: float = 2.0,
                      factors: pd.DataFrame | None = None,
                      gates: dict[str, np.ndarray] | None = None) -> tuple[np.ndarray, int]:
    """ATR-scaled single-account target.

    The base signal is the unified ±1 oz path; the size is decided at the
    same bar close as the signal that opens or reverses an episode and held
    until the episode ends.  The engine fills every target change, so a
    continuously re-sized target would trade a small resize nearly every
    bar; freezing the size per episode keeps the trade stream identical to
    the fixed-size system.  The deciding bar's signal and size both use
    data up to its close only.  The z-signal warm-up outlasts the median
    warm-up, so no live decision depends on the floor fallback.
    """
    base, conflicts = system_target(df, long, short, factors, gates, oz=1.0)
    size = atr_size_series(df["atr_14"].to_numpy(float), ref_oz, med_window,
                           min_periods, floor, cap)
    prev = np.r_[0.0, base[:-1]]
    decide = (base != 0) & (prev != base)
    held = pd.Series(np.where(decide, size, np.nan)).ffill().to_numpy()
    held = np.where(np.isfinite(held), held, size)
    return base * held, conflicts
