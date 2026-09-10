from __future__ import annotations

import unittest

import numpy as np

from backtest import BacktestConfig, BacktestEngine
from backtest.validate import _mk_df, prefix_consistency_check, synthetic_pnl_check
from scripts.run_integration import unified_targets


class _Causal:
    warmup_bars = 0

    def targets(self, df):
        return np.where(df["close"] > df["open"], 100.0, 0.0)


class _FutureReading:
    warmup_bars = 0

    def targets(self, df):
        return np.where(df["close"].shift(-1) > df["close"], 100.0, 0.0)


class BacktestEngineTest(unittest.TestCase):
    def test_synthetic_hand_checks(self):
        synthetic_pnl_check(verbose=False)

    def test_terminal_forced_close_updates_equity(self):
        df = _mk_df([(100, 100, 100, 100)] * 4)
        result = BacktestEngine(BacktestConfig(intraday_only=False)).run(
            df, np.full(len(df), 1.0)
        )
        self.assertAlmostEqual(result.equity[-1] - 10_000, result.trades.net_pnl.sum())
        self.assertAlmostEqual(result.trades.net_pnl.sum(), -0.16)

    def test_gap_stop_uses_adverse_extreme(self):
        df = _mk_df([(100, 100, 100, 100), (100, 100, 100, 100),
                     (90, 91, 89, 90), (90, 90, 90, 90)])
        result = BacktestEngine(BacktestConfig(intraday_only=False, stop_loss_usd=5)).run(
            df, np.array([100, 100, 0, 0], float)
        )
        self.assertEqual(result.trades.iloc[0].exit_reason, "stop_loss")
        self.assertEqual(result.trades.iloc[0].exit_px, 89.0)

    def test_atr_exit_priority_and_reentry_lock(self):
        df = _mk_df([(100, 100, 100, 100), (100, 100, 100, 100),
                     (100, 110, 90, 100), (100, 100, 100, 100),
                     (100, 100, 100, 100), (100, 100, 100, 100)])
        cfg = BacktestConfig(intraday_only=False, stop_loss_atr=1.0,
                             take_profit_atr=1.0, trailing_stop_atr=1.0)
        result = BacktestEngine(cfg).run(df, np.array([100, 100, 100, 100, 0, 0], float),
                                         atr=np.full(len(df), 5.0))
        self.assertEqual(len(result.trades), 1)
        self.assertEqual(result.trades.iloc[0].exit_reason, "stop_loss")
        self.assertEqual(result.trades.iloc[0].exit_px, 90.0)

    def test_atr_profit_target_and_trailing_stop(self):
        df = _mk_df([(100, 100, 100, 100), (100, 100, 100, 100),
                     (100, 110, 99, 100), (100, 100, 100, 100)])
        target = np.array([100, 100, 0, 0], float)
        tp = BacktestEngine(BacktestConfig(intraday_only=False, take_profit_atr=1)).run(
            df, target, atr=np.full(len(df), 5.0))
        self.assertEqual(tp.trades.iloc[0].exit_reason, "take_profit")
        self.assertEqual(tp.trades.iloc[0].exit_px, 99.0)

        trailing_df = _mk_df([(100, 100, 100, 100), (100, 100, 100, 100),
                               (100, 110, 106, 108), (108, 108, 108, 108)])
        trailing = BacktestEngine(BacktestConfig(intraday_only=False, trailing_stop_atr=1)).run(
            trailing_df, target, atr=np.full(len(trailing_df), 3.0))
        self.assertEqual(trailing.trades.iloc[0].exit_reason, "trailing_stop")
        self.assertEqual(trailing.trades.iloc[0].exit_px, 106.0)

    def test_atr_exit_requires_atr_series(self):
        df = _mk_df([(100, 100, 100, 100)] * 3)
        with self.assertRaisesRegex(ValueError, "requires an atr series"):
            BacktestEngine(BacktestConfig(intraday_only=False, stop_loss_atr=1)).run(
                df, np.zeros(len(df)))

    def test_single_account_reverse_and_conflict(self):
        target, conflicts = unified_targets(
            np.array([True, False, False, True]),
            np.array([False, False, True, True]), 4, 4,
        )
        np.testing.assert_array_equal(target, np.array([1.0, 1.0, -1.0, 0.0]))
        self.assertEqual(conflicts, 1)

    def test_micro_lot_accounting_defaults(self):
        df = _mk_df([(100, 100, 100, 100), (100, 100, 100, 100),
                     (101, 101, 101, 101), (101, 101, 101, 101)])
        result = BacktestEngine(BacktestConfig(intraday_only=False)).run(
            df, np.array([1, 1, 0, 0], float))
        trade = result.trades.iloc[0]
        self.assertAlmostEqual(trade["gross_pnl"], 1.0)
        self.assertAlmostEqual(trade["costs"], 0.16)
        self.assertAlmostEqual(trade["net_pnl"], 0.84)
        self.assertEqual(result.config.initial_capital, 10_000.0)
        self.assertEqual(result.config.max_position_oz, 1.0)

    def test_prefix_check_recomputes_targets(self):
        df = _mk_df([(100, 101, 99, 100 + i) for i in range(10)])
        engine = BacktestEngine(BacktestConfig(intraday_only=False))
        self.assertTrue(prefix_consistency_check(engine, df, _Causal(), verbose=False))
        self.assertFalse(prefix_consistency_check(engine, df, _FutureReading(), verbose=False))


if __name__ == "__main__":
    unittest.main()
