"""Backtest framework for XAUUSD CFD 5m intraday strategies.

No-lookahead by construction:
- target position decided at close of bar i -> filled at OPEN of bar i+1
- every fill crosses the spread (half_spread + slippage per side)
- intrabar SL/TP via high/low; when both could trigger in one bar, STOP first (conservative)
- intraday mode force-flattens at the daily cutoff (earlier on Friday, weekend gap)
"""

from .config import BacktestConfig
from .engine import BacktestEngine, BacktestResult
from .metrics import compute_metrics, format_report
from .validate import synthetic_pnl_check, prefix_consistency_check

__all__ = [
    "BacktestConfig",
    "BacktestEngine",
    "BacktestResult",
    "compute_metrics",
    "format_report",
    "synthetic_pnl_check",
    "prefix_consistency_check",
]
