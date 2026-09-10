"""Hand-checked scenarios for the scalping exit mechanisms:

- trail_activate_atr: trailing stop arms only after the best price moves the
  activation distance in favor (trailing take-profit).
- breakeven_activate_atr: after the activation distance, an exit-no-worse-than-
  entry stop becomes active and fills at the entry price.
- priority: stop_loss > trailing_stop > breakeven > take_profit.
"""
from __future__ import annotations

import unittest

import numpy as np

from backtest import BacktestConfig, BacktestEngine
from backtest.validate import _mk_df

ATR = 5.0


def _run(bars, target, **cfg_kwargs):
    df = _mk_df(bars)
    cfg = BacktestConfig(intraday_only=False, **cfg_kwargs)
    return BacktestEngine(cfg).run(df, np.asarray(target, float), atr=np.full(len(df), ATR))


class TrailActivationTest(unittest.TestCase):
    def test_unarmed_trail_does_not_exit(self):
        # Long entry 100 at bar 1.  Plain trail 1xATR(5) exits at the bar-1 low
        # (best 103, level 98, low 94).  With activation 1xATR the trail is not
        # armed yet (profit 3 < 5), so bar 1 survives; on bar 2 the best reaches
        # 108 (profit 8 >= 5), the trail arms, level 103, and the low 103 exits.
        bars = [(100, 100, 100, 100),
                (100, 103, 94, 103),
                (103, 108, 103, 108),
                (108, 108, 108, 108)]
        target = [1, 1, 1, 1]
        plain = _run(bars, target, trailing_stop_atr=1.0)
        armed = _run(bars, target, trailing_stop_atr=1.0, trail_activate_atr=1.0)
        self.assertEqual(plain.trades.iloc[0].exit_reason, "trailing_stop")
        self.assertAlmostEqual(plain.trades.iloc[0].exit_px, 94.0)
        # The armed variant survives bar 1 (profit 3 < 5), then on bar 2 the
        # best reaches 108 (profit 8 >= 5): the trail arms at level 103 and the
        # bar-2 low 103 exits -- later, and at a better price, than the plain
        # trail.  This is the trailing-take-profit behavior.
        self.assertEqual(len(armed.trades), 1)
        self.assertEqual(armed.trades.iloc[0].exit_reason, "trailing_stop")
        self.assertAlmostEqual(armed.trades.iloc[0].exit_px, 103.0)
        self.assertEqual(int(armed.trades.iloc[0].bars_held), 1)

    def test_armed_trail_exits_at_adverse_extreme(self):
        bars = [(100, 100, 100, 100),
                (100, 106, 100, 106),      # profit 6 >= 5: armed, level 101, low 100
                (106, 106, 106, 106)]
        result = _run(bars, [1, 1, 0], trailing_stop_atr=1.0, trail_activate_atr=1.0)
        self.assertEqual(result.trades.iloc[0].exit_reason, "trailing_stop")
        self.assertAlmostEqual(result.trades.iloc[0].exit_px, 100.0)


class BreakevenTest(unittest.TestCase):
    def test_breakeven_fills_at_entry(self):
        # Long entry 100; bar 1 rallies to 106 (arms at 105) and dips to 99 ->
        # breakeven stop fires at exactly the entry price.
        bars = [(100, 100, 100, 100),
                (100, 106, 99, 106),
                (106, 106, 106, 106)]
        result = _run(bars, [1, 1, 0], breakeven_activate_atr=1.0)
        trade = result.trades.iloc[0]
        self.assertEqual(trade.exit_reason, "breakeven")
        self.assertAlmostEqual(trade.exit_px, 100.0)
        self.assertAlmostEqual(trade.net_pnl, -0.16)  # flat PnL, round-trip cost only

    def test_not_armed_no_breakeven_exit(self):
        # Best only reaches 103 (profit 3 < 5): no breakeven, no stop configured,
        # so the position is closed by the flat target at the next open.
        bars = [(100, 100, 100, 100),
                (100, 103, 99, 103),
                (103, 103, 103, 103),
                (103, 103, 103, 103)]
        result = _run(bars, [1, 1, 0, 0], breakeven_activate_atr=1.0)
        self.assertEqual(len(result.trades), 1)
        self.assertEqual(result.trades.iloc[0].exit_reason, "signal")
        self.assertAlmostEqual(result.trades.iloc[0].exit_px, 103.0)


class PriorityTest(unittest.TestCase):
    def test_stop_beats_trail_and_breakeven(self):
        # Same bar arms everything: high 106 (BE/trail armed), low 89 hits the
        # 1xATR stop at 95.  The stop is the worst fill and wins the priority.
        bars = [(100, 100, 100, 100),
                (100, 106, 89, 100),
                (100, 100, 100, 100)]
        result = _run(bars, [1, 1, 0],
                      stop_loss_atr=1.0, trailing_stop_atr=1.0,
                      breakeven_activate_atr=1.0)
        trade = result.trades.iloc[0]
        self.assertEqual(trade.exit_reason, "stop_loss")
        self.assertAlmostEqual(trade.exit_px, 89.0)

    def test_trail_beats_breakeven(self):
        # Trail armed (always) with level best-5; low touches entry too.  The
        # trail fill (adverse extreme) is worse than the entry fill, so it wins.
        bars = [(100, 100, 100, 100),
                (100, 106, 99, 106),
                (106, 106, 106, 106)]
        result = _run(bars, [1, 1, 0],
                      trailing_stop_atr=1.0, breakeven_activate_atr=1.0)
        trade = result.trades.iloc[0]
        self.assertEqual(trade.exit_reason, "trailing_stop")
        self.assertAlmostEqual(trade.exit_px, 99.0)


if __name__ == "__main__":
    unittest.main()
