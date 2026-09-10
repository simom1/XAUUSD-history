from __future__ import annotations

import unittest

import numpy as np
import pandas as pd

from backtest import BacktestConfig, BacktestEngine
from backtest.validate import _mk_df, prefix_consistency_check, synthetic_pnl_check
from analysis.system_research import Component, unified_targets, vol_scaled_target


class _Causal:
    warmup_bars = 0

    def targets(self, df):
        return np.where(df["close"] > df["open"], 1.0, 0.0)


class _FutureReading:
    warmup_bars = 0

    def targets(self, df):
        return np.where(df["close"].shift(-1) > df["close"], 1.0, 0.0)


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

    def test_single_leg_shapes_never_reverse_into_missing_leg(self):
        long_only, long_conflicts = unified_targets(np.array([True, False, True]),
                                                    np.zeros(3, dtype=bool), 2, 1)
        short_only, short_conflicts = unified_targets(np.zeros(3, dtype=bool),
                                                       np.array([True, False, True]), 1, 2)
        np.testing.assert_array_equal(long_only, np.array([1.0, 0.0, 1.0]))
        np.testing.assert_array_equal(short_only, np.array([-1.0, 0.0, -1.0]))
        self.assertEqual(long_conflicts + short_conflicts, 0)

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

    def test_lot_size_scales_pnl_and_cost(self):
        df = _mk_df([(100, 100, 100, 100), (100, 100, 100, 100),
                     (101, 101, 101, 101), (101, 101, 101, 101)])
        for oz, gross, cost in ((1.0, 1.0, 0.16), (5.0, 5.0, 0.80), (10.0, 10.0, 1.60)):
            result = BacktestEngine(BacktestConfig(intraday_only=False, max_position_oz=oz)).run(
                df, np.array([oz, oz, 0, 0], float))
            self.assertAlmostEqual(result.trades.iloc[0].gross_pnl, gross)
            self.assertAlmostEqual(result.trades.iloc[0].costs, cost)

    def test_prefix_check_recomputes_targets(self):
        df = _mk_df([(100, 101, 99, 100 + i) for i in range(10)])
        engine = BacktestEngine(BacktestConfig(intraday_only=False))
        self.assertTrue(prefix_consistency_check(engine, df, _Causal(), verbose=False))
        self.assertFalse(prefix_consistency_check(engine, df, _FutureReading(), verbose=False))

    def test_vol_scaled_target_forwards_bar_seconds(self):
        # One long signal on a bar starting 16:50 UTC: with 5m bars it closes
        # 16:55 (inside london), with 15m bars 17:05 (outside).  Constant atr
        # pins the size series at 1.0, so the target isolates session handling.
        t0 = int(pd.Timestamp("2024-01-03 16:50:00").timestamp())
        ts = [t0 - 300 * (9 - i) for i in range(10)]
        df = pd.DataFrame({"timestamp": ts, "open": 100.0, "high": 100.0,
                           "low": 100.0, "close": 100.0, "atr_14": 1.0})
        factors = pd.DataFrame({"plus_di_14": [0.0] * 9 + [400.0]})
        long = Component("long", "plus_di_14", "high", 6, 1.0, 10, "none", "london")
        kwargs = dict(med_window=6, min_periods=3, factors=factors)
        tgt_300, _ = vol_scaled_target(df, long, None, bar_seconds=300, **kwargs)
        tgt_900, _ = vol_scaled_target(df, long, None, bar_seconds=900, **kwargs)
        self.assertEqual(tgt_300[-1], 1.0)
        self.assertEqual(np.abs(tgt_900).max(), 0.0)


if __name__ == "__main__":
    unittest.main()
