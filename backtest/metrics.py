"""Performance metrics and markdown report formatting."""

from __future__ import annotations

import numpy as np
import pandas as pd

TRADING_DAYS = 252
BARS_PER_DAY = 288


def compute_metrics(result) -> dict:
    """Compute headline stats from a BacktestResult."""
    eq = pd.Series(result.equity, index=pd.to_datetime(result.timestamps, unit="s"))
    trades = result.trades
    cfg = result.config

    total_ret = eq.iloc[-1] / cfg.initial_capital - 1.0
    years = max((eq.index[-1] - eq.index[0]).total_seconds(), 1.0) / (365.25 * 86400)
    cagr = (1.0 + total_ret) ** (1.0 / years) - 1.0 if total_ret > -1 else -1.0

    # Research-wide headline metric: 5-minute dollar PnL Sharpe.  This is
    # intentionally the same convention used by the screening pipeline.
    bar_pnl = eq.diff().dropna()
    sharpe = (float(bar_pnl.mean() / bar_pnl.std() * np.sqrt(BARS_PER_DAY * TRADING_DAYS))
              if len(bar_pnl) > 2 and bar_pnl.std() > 0 else 0.0)
    downside_pnl = bar_pnl[bar_pnl < 0]
    sortino = (float(bar_pnl.mean() / downside_pnl.std() * np.sqrt(BARS_PER_DAY * TRADING_DAYS))
               if len(downside_pnl) > 2 and downside_pnl.std() > 0 else 0.0)

    daily = eq.resample("1D").last().dropna()

    peak = eq.cummax()
    dd = eq / peak - 1.0
    max_dd = float(dd.min())

    m: dict = {
        "total_return_pct": total_ret * 100.0,
        "cagr_pct": cagr * 100.0,
        "sharpe": sharpe,
        "sortino": sortino,
        "max_drawdown_pct": max_dd * 100.0,
        "final_equity": float(eq.iloc[-1]),
        "years": years,
    }

    if trades.empty:
        m.update(n_trades=0, win_rate_pct=0.0, profit_factor=0.0,
                 avg_net_pnl=0.0, avg_bars_held=0.0, exposure_pct=0.0,
                 total_costs=0.0, avg_trades_per_day=0.0)
        return m

    pnl = trades["net_pnl"]
    wins, losses = pnl[pnl > 0], pnl[pnl <= 0]
    gross_win = float(wins.sum())
    gross_loss = float(-losses.sum())
    bars_in_pos = int(trades["bars_held"].sum())

    m.update(
        n_trades=len(trades),
        win_rate_pct=float((pnl > 0).mean() * 100.0),
        profit_factor=gross_win / gross_loss if gross_loss > 0 else float("inf"),
        avg_net_pnl=float(pnl.mean()),
        avg_bars_held=float(trades["bars_held"].mean()),
        exposure_pct=bars_in_pos / len(result.equity) * 100.0,
        total_costs=float(trades["costs"].sum()),
        avg_trades_per_day=len(trades) / max(len(daily), 1),
    )
    return m


def format_report(result, name: str = "strategy") -> str:
    """Render a compact markdown report."""
    m = compute_metrics(result)
    cfg = result.config
    lines = [
        f"## Backtest report — {name}",
        "",
        f"- period: {pd.to_datetime(result.timestamps[0], unit='s'):%Y-%m-%d} → "
        f"{pd.to_datetime(result.timestamps[-1], unit='s'):%Y-%m-%d} ({m['years']:.2f}y, 5m bars)",
        f"- engine: next-open fills | all-in cost ${cfg.round_trip_cost_usd:.2f}/oz round-trip (${cfg.round_trip_cost_usd/2:.2f}/side)"
        f" | commission {cfg.commission_bps:.1f} bps",
        f"- session: {'intraday flat ' + cfg.eod_flat_utc + ' UTC (Fri ' + cfg.friday_flat_utc + ')' if cfg.intraday_only else 'overnight allowed'}"
        + (f" | SL ${cfg.stop_loss_usd}" if cfg.stop_loss_usd else "")
        + (f" | TP ${cfg.take_profit_usd}" if cfg.take_profit_usd else ""),
        "",
        "| metric | value |",
        "|---|---:|",
        f"| total return | {m['total_return_pct']:+.2f}% |",
        f"| CAGR | {m['cagr_pct']:+.2f}% |",
        f"| Sharpe (5m USD PnL, ann.) | {m['sharpe']:.2f} |",
        f"| Sortino (5m USD PnL) | {m['sortino']:.2f} |",
        f"| max drawdown | {m['max_drawdown_pct']:.2f}% |",
        f"| trades | {m['n_trades']} ({m['avg_trades_per_day']:.1f}/day) |",
        f"| win rate | {m['win_rate_pct']:.1f}% |",
        f"| profit factor | {m['profit_factor']:.2f} |",
        f"| avg net PnL/trade | ${m['avg_net_pnl']:+.2f} |",
        f"| avg holding | {m['avg_bars_held']:.1f} bars ({m['avg_bars_held']*5:.0f} min) |",
        f"| exposure (time in market) | {m['exposure_pct']:.1f}% |",
        f"| total friction paid | ${m['total_costs']:,.0f} |",
        f"| final equity | ${m['final_equity']:,.0f} |",
        f"| runtime | {result.runtime_sec:.1f}s |",
        "",
        "> Note: fixed-oz position sizing; margin/interest not modeled. "
        "Equity can go negative for always-in-market strategies at this leverage "
        "(100 oz ≈ 2.6x notional on $100k at $2,600/oz).",
    ]

    tr = result.trades
    if not tr.empty and "exit_reason" in tr:
        lines += ["", "### exits by reason", "", "| reason | trades | net PnL |", "|---|---:|---:|"]
        for reason, g in tr.groupby("exit_reason"):
            lines.append(f"| {reason} | {len(g)} | ${g['net_pnl'].sum():+,.0f} |")

    return "\n".join(lines) + "\n"
