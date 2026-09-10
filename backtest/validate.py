"""Validation utilities: hand-checked accounting tests + no-lookahead check."""

from __future__ import annotations

import numpy as np
import pandas as pd

from .config import BacktestConfig
from .engine import BacktestEngine


def _mk_df(rows: list[tuple[int, float, float, float, float]], t0: int = 0) -> pd.DataFrame:
    """rows of (open, high, low, close) with 5m spacing starting at t0."""
    ts = [t0 + 300 * i for i in range(len(rows))]
    return pd.DataFrame(
        {"timestamp": ts, "open": [r[0] for r in rows], "high": [r[1] for r in rows],
         "low": [r[2] for r in rows], "close": [r[3] for r in rows]}
    )


def synthetic_pnl_check(verbose: bool = True) -> None:
    """Hand-computed expectations; any mismatch means broken accounting."""
    cfg = BacktestConfig(round_trip_cost_usd=0.0, commission_bps=0.0,
                         intraday_only=False, max_position_oz=100.0)
    eng = BacktestEngine(cfg)
    rows = [(100, 100.5, 99.5, 100.2), (100.2, 101, 100, 101),
            (101, 102, 100.8, 102), (103, 103.5, 102.5, 103)]
    df = _mk_df(rows)

    # --- long: target +100 decided at close b0 -> fill open b1 = 100.2,
    #           flat decided at close b2 -> fill open b3 = 103.0
    r = eng.run(df, np.array([100, 100, 0, 0], float))
    t = r.trades.iloc[0]
    assert r.trades.shape[0] == 1
    assert abs(t["entry_px"] - 100.2) < 1e-9 and abs(t["exit_px"] - 103.0) < 1e-9
    assert abs(t["net_pnl"] - 280.0) < 1e-9, t["net_pnl"]
    assert t["bars_held"] == 2
    assert abs(r.equity[-1] - (10_000 + 280)) < 1e-9

    # --- short: target -100 decided at close b1 -> fill open b2 = 101.0,
    #           flat decided at close b2 -> fill open b3 = 103.0
    r = eng.run(df, np.array([0, -100, 0, 0], float))
    t = r.trades.iloc[0]
    assert abs(t["entry_px"] - 101.0) < 1e-9 and abs(t["exit_px"] - 103.0) < 1e-9
    assert abs(t["net_pnl"] - (-200.0)) < 1e-9, t["net_pnl"]
    assert abs(r.equity[-1] - (10_000 - 200)) < 1e-9

    # --- TP: exit at bar low under the deliberately conservative OHLC rule.
    eng2 = BacktestEngine(BacktestConfig(round_trip_cost_usd=0, max_position_oz=100.0,
                                         intraday_only=False,
                                         stop_loss_usd=1.0, take_profit_usd=1.0))
    r = eng2.run(df, np.array([100, 100, 0, 0], float))
    t = r.trades.iloc[0]
    assert t["exit_reason"] == "take_profit" and abs(t["exit_px"] - 100.8) < 1e-9
    assert abs(t["net_pnl"] - 60.0) < 1e-9

    # --- stop priority: bar touching BOTH SL and TP levels -> stop first
    df2 = _mk_df([(100, 100.5, 99.5, 100.2), (100.2, 101, 100, 101),
                  (101, 102, 99.0, 100.5), (103, 103.5, 102.5, 103)])
    r = eng2.run(df2, np.array([100, 100, 0, 0], float))
    t = r.trades.iloc[0]
    assert t["exit_reason"] == "stop_loss" and abs(t["exit_px"] - 99.0) < 1e-9

    # --- friction: 1.4/oz round-trip -> 0.7/oz/side
    eng3 = BacktestEngine(BacktestConfig(round_trip_cost_usd=1.4, max_position_oz=100.0,
                                         intraday_only=False))
    r = eng3.run(df, np.array([100, 100, 0, 0], float))
    t = r.trades.iloc[0]
    assert abs(t["net_pnl"] - (280.0 - 2 * 0.7 * 100)) < 1e-9   # costs 140
    assert abs(t["costs"] - 140.0) < 1e-9

    # --- session flat: cutoff 00:10, block 0min -> forced exit at close 101.5
    cfg4 = BacktestConfig(round_trip_cost_usd=0, max_position_oz=100.0, intraday_only=True,
                          eod_flat_utc="00:10", friday_flat_utc="00:10",
                          entry_block_minutes=0)
    r = BacktestEngine(cfg4).run(_mk_df(rows[:2]), np.array([100, 100], float))
    t = r.trades.iloc[0]
    assert t["exit_reason"] == "session" and abs(t["exit_px"] - 101.0) < 1e-9
    # bar1 closes at 00:10 == cutoff -> session exit at ITS close (101.0)

    if verbose:
        print("synthetic_pnl_check: PASS (long/short/TP/stop-priority/friction/session)")


def prefix_consistency_check(
    engine: BacktestEngine,
    df: pd.DataFrame,
    strategy,
    warmup_bars: int = 0,
    frac: float = 0.8,
    verbose: bool = True,
) -> bool:
    """Rebuild targets on a prefix and compare the common completed history.

    ``strategy`` must expose ``targets(df)`` or be a callable accepting a
    dataframe.  Recomputing it is the crucial difference from replaying a
    precomputed target array: a future-reading strategy changes at the cut.
    """
    k = int(len(df) * frac)
    make_targets = strategy.targets if hasattr(strategy, "targets") else strategy
    full_targets = np.asarray(make_targets(df), dtype=float)
    prefix = df.iloc[:k].reset_index(drop=True)
    prefix_targets = np.asarray(make_targets(prefix), dtype=float)
    targets_match = np.array_equal(full_targets[:k], prefix_targets)
    r_full = engine.run(df, full_targets, warmup_bars)
    r_pre = engine.run(prefix, prefix_targets, warmup_bars)

    # The prefix's final bar is legitimately force-closed by the engine, so
    # compare only bars that are complete in both runs.
    ok = np.array_equal(r_full.equity[:k - 1], r_pre.equity[:k - 1])
    cols = ["entry_i", "exit_i", "side", "oz", "entry_px", "exit_px", "net_pnl", "exit_reason"]
    t_full = r_full.trades
    t_pre = r_pre.trades
    if not t_full.empty:
        t_full = t_full[t_full["exit_i"] < k - 1][cols].reset_index(drop=True)
    if not t_pre.empty:
        t_pre = t_pre[t_pre["exit_i"] < k - 1][cols].reset_index(drop=True)
    same_trades = len(t_full) == len(t_pre) and (
        t_full.empty or t_full.equals(t_pre)
    )
    if verbose:
        status = "PASS" if (targets_match and ok and same_trades) else "FAIL"
        print(f"prefix_consistency_check (recomputed first {frac:.0%}): {status} "
              f"[{len(t_pre)} overlapping trades, targets identical: {targets_match}, equity bit-identical: {ok}]")
    return bool(targets_match and ok and same_trades)
