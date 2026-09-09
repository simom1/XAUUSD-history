"""Run a baseline backtest from the command line.

Usage:
  python scripts/run_backtest.py --strategy ema_cross_9_21
  python scripts/run_backtest.py --strategy donchian_breakout_20 --cost-rt 0.16
  python scripts/run_backtest.py --strategy ema_cross_9_21 --overnight --sl 5.0
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd

from backtest import BacktestConfig, BacktestEngine, format_report
from backtest.validate import prefix_consistency_check, synthetic_pnl_check
from strategies import make_strategy

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "xauusd_5m_indicators.csv.gz"
REPORTS = ROOT / "report"


def main() -> None:
    ap = argparse.ArgumentParser(description="XAUUSD 5m intraday backtest")
    ap.add_argument("--strategy", default="ema_cross_9_21")
    ap.add_argument("--cost-rt", type=float, default=0.16,
                    help="all-in round-trip cost USD/oz (spread+slippage+commission)")
    ap.add_argument("--commission-bps", type=float, default=0.0)
    ap.add_argument("--capital", type=float, default=100_000.0)
    ap.add_argument("--oz", type=float, default=100.0, help="max position in ounces")
    ap.add_argument("--sl", type=float, default=None, help="stop loss USD/oz")
    ap.add_argument("--tp", type=float, default=None, help="take profit USD/oz")
    ap.add_argument("--overnight", action="store_true", help="disable intraday flat")
    ap.add_argument("--no-check", action="store_true", help="skip no-lookahead check")
    ap.add_argument("--save", action="store_true", help="save report + trades to report/")
    args = ap.parse_args()

    synthetic_pnl_check()

    cfg = BacktestConfig(
        initial_capital=args.capital,
        max_position_oz=args.oz,
        round_trip_cost_usd=args.cost_rt,
        commission_bps=args.commission_bps,
        intraday_only=not args.overnight,
        stop_loss_usd=args.sl,
        take_profit_usd=args.tp,
    )
    print(f"loading {DATA.name} ...")
    df = pd.read_csv(DATA)
    strat = make_strategy(args.strategy)
    engine = BacktestEngine(cfg)
    result = strat.run(engine, df)

    if not args.no_check:
        prefix_consistency_check(engine, df, strat.targets(df),
                                 warmup_bars=strat.warmup_bars)

    report = format_report(result, name=strat.name)
    print(report)

    if args.save:
        REPORTS.mkdir(exist_ok=True)
        md = REPORTS / f"backtest_{strat.name}.md"
        tr = REPORTS / f"backtest_{strat.name}_trades.csv"
        md.write_text(report, encoding="utf-8")
        result.trades.to_csv(tr, index=False)
        print(f"saved: {md.relative_to(ROOT)}\n       {tr.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
