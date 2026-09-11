# -*- coding: utf-8 -*-
"""Rank-aggregation signal engine for the scalping factor adaptation study.

The nested walk-forward (`run_scalping_nested_wf.py`) showed that the specific
factor-pair selection overfits: 4 folds picked 4 different long factors and 4
different short factors, yielding only 2/4 positive test folds.  The structural
dimensions (exit=none, window=288-576, family=reversal, regime=trend variants,
session=active) were stable on 4/4 folds.

This module replaces the unstable "pick one factor pair" step with a
**rank-aggregation** signal: the top-N mean-reversion factors (determined by IC
screening on the train prefix) are combined into a single long/short decision
via one of three methods:

  - ``vote``        : discrete vote count >= vote_min
  - ``rank_avg``    : cross-factor rank average -> rolling_z -> threshold
  - ``z_composite`` : equal-weight z-score average -> rolling_z -> threshold

The factor *family* (top-N reversal factors) is determined by IC screening and
is relatively stable across folds; the aggregation *parameters* (method,
vote_min, window, threshold, hold, regime, session) are grid-searched.  This
separation targets the root cause of the nested-WF failure: selection variance
in the specific factor pair.

All signals use trailing ``rolling_z`` (no look-ahead).  IC screening uses only
the train prefix.  The fast vectorized scoring is mathematically identical to
``fast_component_score`` in ``system_research.py`` (mid fills, next-open
execution, session flat at cutoff).
"""
from __future__ import annotations

from dataclasses import dataclass, asdict

import numpy as np
import pandas as pd
from numba import njit

from analysis.combo_screening import build_gates
from analysis.factor_screening import (
    ANN, OZ, Session, build_factors, ic_stats, pnl_from_path, rolling_z,
)
from analysis.system_research import (
    EXITS, bar_metrics, regime_mask, session_mask, unified_targets,
)
from backtest import BacktestConfig, BacktestEngine

ANN_5M = float(ANN)  # sqrt(288 * 252), 5m bar annualization


@njit(cache=True)
def _unified_targets_jit(long_dec, short_dec, long_hold, short_hold, oz):
    """Numba-compiled unified_targets — identical logic, ~50x faster loop."""
    n = len(long_dec)
    out = np.zeros(n)
    side = 0
    expires = -1
    conflicts = 0
    for i in range(n):
        if side and i >= expires:
            side = 0
        if long_dec[i] and short_dec[i]:
            side = 0
            expires = i
            conflicts += 1
        elif long_dec[i] and side != 1:
            side = 1
            expires = i + long_hold - 1
        elif short_dec[i] and side != -1:
            side = -1
            expires = i + short_hold - 1
        out[i] = side * oz
    return out, conflicts


# ----------------------------------------------------------------------
# Configuration
# ----------------------------------------------------------------------
@dataclass(frozen=True)
class AggregationConfig:
    """Rank-aggregation configuration (replaces the single factor pair).

    The factor *family* (top-N reversal factors) is determined separately by
    IC screening; this config holds the aggregation *parameters* that are
    grid-searched.
    """
    method: str            # "vote" | "rank_avg" | "z_composite"
    n_factors: int         # top-N reversal factors to combine
    window: int            # z-score rolling window (bars)
    threshold: float       # z-score trigger threshold
    vote_min: int          # vote method: minimum agreeing factors (others: ignored)
    hold: int              # holding period (bars) for both long and short
    regime: str            # regime gate name
    session: str           # session gate name
    exit_name: str         # exit configuration name (key into EXITS)

    @property
    def key(self) -> str:
        return (f"{self.method}:N{self.n_factors}:W{self.window}:T{self.threshold:g}"
                f":V{self.vote_min}:H{self.hold}:{self.regime}:{self.session}:{self.exit_name}")


# ----------------------------------------------------------------------
# Factor family selection (stable step)
# ----------------------------------------------------------------------
def select_reversal_factors(
    factors: pd.DataFrame,
    close: np.ndarray,
    ts_dt: pd.Series,
    n: int,
    top_n: int = 10,
    horizon: int = 12,
) -> list[str]:
    """IC screening -> top-N reversal (mean-reversion) factors, by |ICIR| desc.

    A factor is "reversal" if its IC mean is negative (low factor value ->
    high forward return).  This is the stable family-determination step;
    the specific factor *pair* is not selected here.

    Returns a list of factor names (length <= top_n), strongest first.
    """
    ic_df = ic_stats(factors, close, ts_dt, n, horizons=(horizon,))
    ih = ic_df[ic_df.h == horizon].copy()
    # reversal: IC < 0 (low factor -> high return = mean reversion)
    rev = ih[ih.ic_mean < 0].copy()
    rev["abs_icir"] = rev["icir"].abs()
    rev = rev.sort_values("abs_icir", ascending=False)
    return rev["factor"].head(top_n).tolist()


# ----------------------------------------------------------------------
# Aggregation signal (three methods)
# ----------------------------------------------------------------------
def _vote_signal(
    z_list: list[np.ndarray],
    threshold: float, vote_min: int,
) -> tuple[np.ndarray, np.ndarray]:
    """Discrete vote: >= vote_min factors agree -> trigger."""
    n = len(z_list[0])
    long_votes = np.zeros(n, dtype=int)
    short_votes = np.zeros(n, dtype=int)
    for z in z_list:
        long_votes += (z <= -threshold).astype(int)
        short_votes += (z >= threshold).astype(int)
    return long_votes >= vote_min, short_votes >= vote_min


def _rank_avg_composite(z_list: list[np.ndarray]) -> np.ndarray:
    """Cross-factor rank average -> standardize to [-1,1]."""
    N = len(z_list)
    z_matrix = np.column_stack(z_list)
    ranks = np.argsort(np.argsort(z_matrix, axis=1, kind="stable"), axis=1, kind="stable").astype(float)
    if N > 1:
        return (ranks.mean(axis=1) / (N - 1)) * 2.0 - 1.0
    return ranks[:, 0] * 2.0 - 1.0


def _rank_avg_signal(
    z_list: list[np.ndarray],
    window: int, threshold: float,
    z_comp: np.ndarray | None = None,
) -> tuple[np.ndarray, np.ndarray]:
    """Cross-factor rank average -> standardize to [-1,1] -> rolling_z -> threshold.

    Robust to outlier z-scores (rank caps extreme values).
    z_comp: pre-computed rolling_z of the composite (skip re-computation).
    """
    if z_comp is None:
        composite = _rank_avg_composite(z_list)
        z_comp = rolling_z(pd.Series(composite), window)
    return z_comp <= -threshold, z_comp >= threshold


def _z_composite_raw(z_list: list[np.ndarray]) -> np.ndarray:
    """Equal-weight z-score average (before rolling_z)."""
    return np.column_stack(z_list).mean(axis=1)


def _z_composite_signal(
    z_list: list[np.ndarray],
    window: int, threshold: float,
    z_comp: np.ndarray | None = None,
) -> tuple[np.ndarray, np.ndarray]:
    """Equal-weight z-score average -> rolling_z -> threshold.

    Preserves extreme-value information (unlike rank_avg).
    z_comp: pre-computed rolling_z of the composite (skip re-computation).
    """
    if z_comp is None:
        composite = _z_composite_raw(z_list)
        z_comp = rolling_z(pd.Series(composite), window)
    return z_comp <= -threshold, z_comp >= threshold


def _z_list_from_factors(
    factors: pd.DataFrame, factor_names: list[str], window: int,
    z_cache: dict | None = None,
) -> list[np.ndarray]:
    """Build per-factor z-score list, using cache if available."""
    if z_cache is not None:
        return [z_cache[(window, name)] for name in factor_names]
    return [rolling_z(factors[name], window) for name in factor_names]


def aggregation_signal(
    df: pd.DataFrame,
    factors: pd.DataFrame,
    factor_names: list[str],
    cfg: AggregationConfig,
    gates: dict[str, np.ndarray] | None = None,
    bar_seconds: int = 300,
    z_cache: dict | None = None,
    composite_cache: dict | None = None,
) -> tuple[np.ndarray, np.ndarray]:
    """Rank-aggregation long/short decision masks (boolean arrays).

    Applies regime_mask & session_mask after the aggregation.  Regime depends
    on side (trend_up for long, trend_down for short), matching
    ``system_research.decisions``.

    z_cache: optional dict[(window, factor_name) -> np.ndarray] of pre-computed
        rolling z-scores, to avoid redundant computation in grid search.
    composite_cache: optional dict[(method, n_factors, window) -> np.ndarray] of
        pre-computed rolling_z of the composite signal.  Only used by
        rank_avg / z_composite (vote has no composite rolling_z).
    """
    if not factor_names:
        n = len(df)
        return np.zeros(n, dtype=bool), np.zeros(n, dtype=bool)

    z_list = _z_list_from_factors(factors, factor_names, cfg.window, z_cache)
    if cfg.method == "vote":
        long_dec, short_dec = _vote_signal(z_list, cfg.threshold, cfg.vote_min)
    elif cfg.method == "rank_avg":
        z_comp = composite_cache.get((cfg.method, cfg.n_factors, cfg.window)) if composite_cache else None
        long_dec, short_dec = _rank_avg_signal(z_list, cfg.window, cfg.threshold, z_comp)
    elif cfg.method == "z_composite":
        z_comp = composite_cache.get((cfg.method, cfg.n_factors, cfg.window)) if composite_cache else None
        long_dec, short_dec = _z_composite_signal(z_list, cfg.window, cfg.threshold, z_comp)
    else:
        raise ValueError(f"unknown aggregation method: {cfg.method}")

    ts = df["timestamp"].to_numpy(np.int64)
    g = gates if gates is not None else build_gates(df)
    long_dec = long_dec & regime_mask(df, "long", cfg.regime, g) & session_mask(ts, cfg.session, bar_seconds)
    short_dec = short_dec & regime_mask(df, "short", cfg.regime, g) & session_mask(ts, cfg.session, bar_seconds)
    return long_dec, short_dec


# ----------------------------------------------------------------------
# Target path + engine
# ----------------------------------------------------------------------
def aggregation_target(
    df: pd.DataFrame,
    factors: pd.DataFrame,
    factor_names: list[str],
    cfg: AggregationConfig,
    gates: dict[str, np.ndarray] | None = None,
    oz: float = OZ,
    bar_seconds: int = 300,
    z_cache: dict | None = None,
    composite_cache: dict | None = None,
) -> tuple[np.ndarray, int]:
    """Aggregation signal -> unified_targets -> signed position path."""
    long_dec, short_dec = aggregation_signal(df, factors, factor_names, cfg, gates,
                                              bar_seconds, z_cache, composite_cache)
    return unified_targets(long_dec, short_dec, cfg.hold, cfg.hold, oz)


def run_aggregation_engine(
    df: pd.DataFrame,
    factors: pd.DataFrame,
    factor_names: list[str],
    cfg: AggregationConfig,
    gates: dict[str, np.ndarray] | None = None,
    oz: float = OZ,
    bar_seconds: int = 300,
    ann: float = ANN_5M,
    z_cache: dict | None = None,
    composite_cache: dict | None = None,
) -> tuple:
    """Run the event-consistent backtest engine on an aggregation config.

    Returns (result, target, metrics_dict, conflicts) — same shape as
    ``system_research.run_engine``.
    """
    target, conflicts = aggregation_target(df, factors, factor_names, cfg, gates,
                                            oz, bar_seconds, z_cache, composite_cache)
    exit_args = dict(EXITS)[cfg.exit_name]
    cfg_kwargs = dict(max_position_oz=oz, bar_seconds=bar_seconds, **exit_args)
    result = BacktestEngine(BacktestConfig(**cfg_kwargs)).run(
        df, target,
        atr=df["atr_14"].to_numpy(float) if exit_args else None,
        meta={"config": asdict(cfg), "factor_names": list(factor_names),
              "conflicts": conflicts},
    )
    return result, target, bar_metrics(result, ann=ann), conflicts


def fast_aggregation_score(
    df: pd.DataFrame,
    factors: pd.DataFrame,
    factor_names: list[str],
    cfg: AggregationConfig,
    gates: dict[str, np.ndarray] | None = None,
    bar_seconds: int = 300,
    ann: float = ANN_5M,
    z_cache: dict | None = None,
    composite_cache: dict | None = None,
    session: Session | None = None,
) -> dict:
    """Vectorized fast score (no exit), for grid pre-filtering.

    Logic mirrors ``system_research.fast_component_score``: mid fills,
    next-open execution, session flat at cutoff.  PnL is identical to the
    engine with exit_name="none" (confirmed by test_fast_score_vs_engine).

    session: optional pre-computed Session object (only depends on timestamp
        + bar_seconds, so it can be reused across all configs in a grid).
    """
    # Use JIT-compiled unified_targets for ~50x speedup over the Python loop.
    long_dec, short_dec = aggregation_signal(df, factors, factor_names, cfg,
                                              gates, bar_seconds, z_cache,
                                              composite_cache)
    target, _ = _unified_targets_jit(long_dec, short_dec, cfg.hold, cfg.hold,
                                     float(OZ))
    ses = session if session is not None else Session(
        df["timestamp"].to_numpy(np.int64), bar_seconds=bar_seconds)
    pos = np.zeros(len(df))
    pos[1:] = np.where(ses.flat[:-1], 0.0, target[:-1])
    o = df["open"].to_numpy(float)
    c = df["close"].to_numpy(float)
    B = pnl_from_path(pos, o, c, ses.flat)
    sharpe = float(B.mean() / B.std() * ann) if B.std() else 0.0
    trades = int(np.count_nonzero(np.diff(pos)))
    return {"config": cfg, "pnl": float(B.sum()), "sharpe": sharpe,
            "trades_proxy": trades,
            "avg": float(B.sum() / max(trades / 2, 1))}


def build_z_cache(
    factors: pd.DataFrame, factor_names: list[str], windows: tuple[int, ...],
) -> dict:
    """Pre-compute rolling z-scores for all (window, factor) pairs.

    Avoids redundant rolling_z calls in grid search (5k+ configs share the
    same z-scores; only the aggregation method / threshold / vote_min differ).
    """
    cache = {}
    for w in windows:
        for name in factor_names:
            cache[(w, name)] = rolling_z(factors[name], w)
    return cache


def build_composite_cache(
    factors: pd.DataFrame, family: list[str],
    methods: tuple[str, ...], n_factors_list: tuple[int, ...],
    windows: tuple[int, ...], z_cache: dict,
) -> dict:
    """Pre-compute rolling_z of the composite signal for all (method, N, window).

    The composite depends only on (method, n_factors, window); threshold and
    vote_min are applied AFTER rolling_z.  This reduces O(grid_size) rolling_z
    calls to O(methods * n_factors * windows) = ~18 calls.

    vote has no composite rolling_z (threshold is applied directly to factor
    z-scores), so it is not included in this cache.
    """
    cache = {}
    for method in methods:
        if method == "vote":
            continue
        for nf in n_factors_list:
            if nf > len(family):
                continue
            fn = family[:nf]
            for w in windows:
                z_list = [z_cache[(w, name)] for name in fn]
                if method == "rank_avg":
                    composite = _rank_avg_composite(z_list)
                elif method == "z_composite":
                    composite = _z_composite_raw(z_list)
                else:
                    continue
                cache[(method, nf, w)] = rolling_z(pd.Series(composite), w)
    return cache


# ----------------------------------------------------------------------
# Train-prefix selection (for nested walk-forward)
# ----------------------------------------------------------------------
def build_grid(
    methods: tuple[str, ...] = ("vote", "rank_avg", "z_composite"),
    n_factors: tuple[int, ...] = (5, 7, 10),
    windows: tuple[int, ...] = (288, 576),
    thresholds: tuple[float, ...] = (1.5, 2.0),
    vote_mins: tuple[int, ...] = (2, 3, 4),
    holds: tuple[int, ...] = (6, 12, 24),
    regimes: tuple[str, ...] = ("none", "trend", "trend_adx", "trend_not_choppy"),
    sessions: tuple[str, ...] = ("all", "london", "new_york", "overlap"),
    exits: tuple[str, ...] = ("none", "stop1_5", "trail2"),
) -> list[AggregationConfig]:
    """Build the full aggregation-parameter grid.

    vote_min is only meaningful for the "vote" method but is stored in all
    configs (ignored by rank_avg / z_composite).
    """
    grid = []
    for method in methods:
        for nf in n_factors:
            for w in windows:
                for t in thresholds:
                    for vm in vote_mins:
                        for h in holds:
                            for regime in regimes:
                                for sess in sessions:
                                    for ex in exits:
                                        grid.append(AggregationConfig(
                                            method, nf, w, t, vm, h, regime, sess, ex))
    return grid


def select_aggregation_on_train(
    train_df: pd.DataFrame,
    grid: list[AggregationConfig],
    max_n_factors: int = 15,
    horizon: int = 12,
    fast_window: int = 48,
    bar_seconds: int = 300,
    ann: float = ANN_5M,
    min_trades: int = 20,
    top_k_engine: int = 20,
) -> dict | None:
    """Full aggregation selection pipeline on a train prefix.

    1. IC screening -> top-max_n_factors reversal factors (stable family).
    2. Fast-score every grid config (each takes the first n_factors from the
       family list, so families are nested and comparable).
    3. Top-K by Sharpe -> event engine re-score.
    4. Return best config + train metrics + top-5 for stability analysis.

    Returns None if selection fails (no eligible config).
    """
    n = len(train_df)
    factors = build_factors(train_df, fast_window=fast_window)
    gates = build_gates(train_df)
    close = train_df["close"].to_numpy(float)
    ts_dt = pd.to_datetime(train_df["datetime_utc"])

    # 1. Factor family (stable step)
    family = select_reversal_factors(factors, close, ts_dt, n,
                                     top_n=max_n_factors, horizon=horizon)
    if not family:
        return None

    # Pre-compute z-cache for all (window, factor) pairs in the grid
    grid_windows = sorted({cfg.window for cfg in grid})
    z_cache = build_z_cache(factors, family, grid_windows)

    # Pre-compute composite cache for rank_avg / z_composite methods.
    # Composite rolling_z depends only on (method, n_factors, window), so we
    # compute it once per unique triple instead of once per grid config.
    grid_methods = sorted({cfg.method for cfg in grid})
    grid_n_factors = sorted({cfg.n_factors for cfg in grid})
    composite_cache = build_composite_cache(
        factors, family, grid_methods, grid_n_factors, grid_windows, z_cache
    )

    # 2. Fast score every config (reuse one Session for all configs)
    ses = Session(train_df["timestamp"].to_numpy(np.int64), bar_seconds=bar_seconds)
    scores = []
    for cfg in grid:
        if cfg.n_factors > len(family):
            continue
        factor_names = family[:cfg.n_factors]
        s = fast_aggregation_score(train_df, factors, factor_names, cfg, gates,
                                   bar_seconds, ann, z_cache, composite_cache, ses)
        scores.append((cfg, s))

    eligible = [(cfg, s) for cfg, s in scores
                if s["avg"] > 0 and s["trades_proxy"] >= min_trades]
    eligible.sort(key=lambda x: x[1]["sharpe"], reverse=True)
    if not eligible:
        return None

    # 3. Engine re-score top-K
    engine_results = []
    for cfg, _ in eligible[:top_k_engine]:
        factor_names = family[:cfg.n_factors]
        result, _, m, _ = run_aggregation_engine(train_df, factors, factor_names,
                                                  cfg, gates, bar_seconds=bar_seconds, ann=ann)
        engine_results.append((cfg, m, result))

    engine_results.sort(key=lambda x: x[1]["sharpe"], reverse=True)
    best_cfg, best_m, best_result = engine_results[0]

    return {
        "config": best_cfg,
        "factor_names": family[:best_cfg.n_factors],
        "all_reversal_factors": family,
        "train_metrics": best_m,
        "train_trades": int(len(best_result.trades)),
        "top5": [(cfg, m) for cfg, m, _ in engine_results[:5]],
        "n_grid": len(scores),
        "n_eligible": len(eligible),
    }


def evaluate_aggregation_on_test(
    research: pd.DataFrame,
    test_lo: int,
    test_hi: int,
    cfg: AggregationConfig,
    factor_names: list[str],
    fast_window: int = 48,
    bar_seconds: int = 300,
    ann: float = ANN_5M,
) -> dict:
    """Evaluate a frozen aggregation config on the test period [test_lo, test_hi).

    Factors/gates are rebuilt on the full prefix [0, test_hi) (trailing
    computation uses earlier bars only, never test-period future data).
    """
    eval_df = research.iloc[:test_hi].reset_index(drop=True)
    factors = build_factors(eval_df, fast_window=fast_window)
    gates = build_gates(eval_df)
    result, _, _, _ = run_aggregation_engine(eval_df, factors, factor_names, cfg,
                                              gates, bar_seconds=bar_seconds, ann=ann)
    fm = bar_metrics(result, test_lo, test_hi, ann=ann)
    test_trades = result.trades[
        (result.trades.entry_i >= test_lo) & (result.trades.entry_i < test_hi)]
    if test_trades.empty:
        wr = pf = 0.0
        avg_hold = 0.0
    else:
        wins = float(test_trades.loc[test_trades.net_pnl > 0, "net_pnl"].sum())
        losses = float(-test_trades.loc[test_trades.net_pnl < 0, "net_pnl"].sum())
        wr = round(float((test_trades.net_pnl > 0).mean() * 100), 1)
        pf = round(wins / losses, 3) if losses > 0 else float("inf")
        avg_hold = round(float(test_trades.bars_held.mean()), 1)
    return {"pnl": round(fm["pnl"], 2), "sharpe": round(fm["sharpe"], 3),
            "maxdd": round(fm["maxdd"], 2), "trades": int(len(test_trades)),
            "wr": wr, "pf": pf, "avg_hold": avg_hold}
