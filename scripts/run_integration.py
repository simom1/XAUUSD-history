"""Single-account long/short integration report.

The 2026-03-10 -> 2026-09-09 segment is a consumed development set.  It is
reported for diagnosis only and is never used to choose or tune this system.
"""
from __future__ import annotations

import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import numpy as np
import pandas as pd

from analysis.combo_screening import (SHORT_FAMILY_EXT, SURVIVORS, build_gates,
                                      holdout_split, masks_from_spec, parse_spec)
from analysis.factor_screening import ANN, OZ, build_factors, rolling_z
from backtest import BacktestConfig, BacktestEngine, compute_metrics

DATA = ROOT / "data" / "xauusd_5m_indicators.csv.gz"
REPORT = ROOT / "report" / "integrated_system.md"
LONG_SPEC = "single|plus_di_14|long|W6048|T1.5|H120"
SHORT_SPEC = "single|close_vs_ema200|short|W6048|T1.5|H120"
LONG_GATE = "trend_up,adx_strong"
SHORT_GATE = "trend_down,adx_strong"


def _gate(gates: dict[str, np.ndarray], names: str) -> np.ndarray:
    out = np.ones(len(next(iter(gates.values()))), dtype=bool)
    for name in names.split(","):
        out &= gates[name.strip()]
    return out


def unified_targets(long_dec: np.ndarray, short_dec: np.ndarray, long_hold: int,
                    short_hold: int, oz: float = OZ) -> tuple[np.ndarray, int]:
    """One account: reverse on an opposite signal; a simultaneous signal is flat."""
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


def _bar_metrics(result, lo: int, hi: int) -> dict[str, float]:
    pnl = np.diff(np.r_[result.config.initial_capital, result.equity])[lo:hi]
    total = float(pnl.sum())
    sharpe = float(pnl.mean() / pnl.std() * ANN) if len(pnl) > 2 and pnl.std() else 0.0
    curve = np.cumsum(pnl)
    dd = float((curve - np.maximum.accumulate(curve)).min()) if len(curve) else 0.0
    return {"pnl": total, "sharpe": sharpe, "maxdd": dd}


def main() -> None:
    df = pd.read_csv(DATA)
    ts = pd.to_datetime(df["timestamp"], unit="s")
    h_idx, dev_start = holdout_split(df["timestamp"].to_numpy(np.int64), 183)
    factors, gates = build_factors(df), build_gates(df)
    long_cfg, short_cfg = parse_spec(LONG_SPEC), parse_spec(SHORT_SPEC)

    def zget(name, window):
        return rolling_z(factors[name], window)

    long_dec, _ = masks_from_spec(long_cfg, zget, SURVIVORS, _gate(gates, LONG_GATE), None)
    _, short_dec = masks_from_spec(short_cfg, zget, SHORT_FAMILY_EXT, None, _gate(gates, SHORT_GATE))
    target, conflicts = unified_targets(long_dec, short_dec, long_cfg["hold"], short_cfg["hold"])
    if np.max(np.abs(target)) > OZ:
        raise RuntimeError("unified target exceeds 100 oz")

    cfg = BacktestConfig(stop_loss_atr=2.5)
    result = BacktestEngine(cfg).run(df, target, atr=df["atr_14"].to_numpy(float),
                                     meta={"strategy": "integrated_single_account"})
    full = compute_metrics(result)
    research = _bar_metrics(result, 0, h_idx)
    dev = _bar_metrics(result, h_idx, len(df))
    fold_edges = np.linspace(0, h_idx, 5, dtype=int)
    fold_rows = []
    for i, (lo, hi) in enumerate(zip(fold_edges[:-1], fold_edges[1:]), 1):
        m = _bar_metrics(result, int(lo), int(hi))
        fold_rows.append(f"| f{i} | ${m['pnl']:+,.0f} | {m['sharpe']:.2f} | ${m['maxdd']:,.0f} |")

    lines = [
        "# Integrated Long-Short System — single-account revision", "",
        f"- data: {ts.iloc[0]:%Y-%m-%d} -> {ts.iloc[-1]:%Y-%m-%d} ({len(df):,} 5m bars)",
        f"- research period: {ts.iloc[0]:%Y-%m-%d} -> {ts.iloc[h_idx - 1]:%Y-%m-%d}",
        f"- consumed development set: {dev_start:%Y-%m-%d} -> {ts.iloc[-1]:%Y-%m-%d}; not a validation result.",
        "- execution: one $100,000 account, max 100 oz, next-open fills, $0.16/oz round-trip cost.",
        "- exits: entry ATR(14) fixed stop 2.5×; all protective exits fill at the adverse bar extreme.",
        "- metric: annualized 5-minute USD PnL Sharpe (sqrt(288×252)); margin, financing and liquidation are not modeled.", "",
        "## Locked development specification", "",
        f"- long: `{LONG_SPEC}`, gates `{LONG_GATE}`",
        f"- short: `{SHORT_SPEC}`, gates `{SHORT_GATE}`",
        "- opposing signals reverse at the next open; simultaneous signals flatten the account.",
        f"- simultaneous signal conflicts observed: {conflicts}", "",
        "## Results", "", "| segment | PnL | 5m Sharpe | max drawdown |", "|---|---:|---:|---:|",
        f"| research | ${research['pnl']:+,.0f} | {research['sharpe']:.2f} | ${research['maxdd']:,.0f} |",
        f"| consumed development set | ${dev['pnl']:+,.0f} | {dev['sharpe']:.2f} | ${dev['maxdd']:,.0f} |",
        f"| full history | ${full['final_equity'] - cfg.initial_capital:+,.0f} | {full['sharpe']:.2f} | {full['max_drawdown_pct']:.2f}% |", "",
        "## Internal research folds", "", "| fold | PnL | 5m Sharpe | max drawdown |", "|---|---:|---:|---:|",
        *fold_rows, "", "## Status", "",
        "This is a development candidate only. Do not tune from the consumed development set. "
        "After at least six new continuous months of data are available, freeze that new segment and run the pre-locked single-account specification once through the event engine.",
    ]
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"saved {REPORT.relative_to(ROOT)}")
    print(f"research ${research['pnl']:+,.0f}; development ${dev['pnl']:+,.0f}; full ${full['final_equity'] - cfg.initial_capital:+,.0f}")


if __name__ == "__main__":
    main()
