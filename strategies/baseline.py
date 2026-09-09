"""Baseline strategies (smoke tests for the engine + reference points).

A strategy returns a SIGNED target position in OUNCES per bar, decided with
data up to that bar's close only (engine fills at next bar's open).
"""

from __future__ import annotations

import numpy as np
import pandas as pd

OZ_PER_UNIT = 100.0   # 1 unit of signal = 100 oz (~1 standard lot)


class BaseStrategy:
    name: str = "base"
    warmup_bars: int = 300

    def targets(self, df: pd.DataFrame) -> np.ndarray:
        raise NotImplementedError

    def run(self, engine, df: pd.DataFrame):
        return engine.run(df, self.targets(df), warmup_bars=self.warmup_bars,
                          meta={"strategy": self.name})


class EmaCrossStrategy(BaseStrategy):
    """Always-in-market EMA cross: long when ema_fast > ema_slow, else short."""

    def __init__(self, fast: int = 9, slow: int = 21, oz: float = OZ_PER_UNIT):
        self.fast, self.slow, self.oz = fast, slow, oz
        self.name = f"ema_cross_{fast}_{slow}"
        self.warmup_bars = max(slow * 3, 300)

    def targets(self, df: pd.DataFrame) -> np.ndarray:
        sig = (df[f"ema_{self.fast}"] > df[f"ema_{self.slow}"]).astype(float) * 2 - 1
        return sig.to_numpy() * self.oz


class DonchianBreakoutStrategy(BaseStrategy):
    """Classic 20-bar Donchian breakout with persistent state."""

    def __init__(self, n: int = 20, oz: float = OZ_PER_UNIT):
        self.n, self.oz = n, oz
        self.name = f"donchian_breakout_{n}"
        self.warmup_bars = max(n * 3, 300)

    def targets(self, df: pd.DataFrame) -> np.ndarray:
        up = df[f"donchian_up_{self.n}"].shift(1)   # prior channel only
        lo = df[f"donchian_low_{self.n}"].shift(1)
        raw = np.where(df["close"] > up, 1.0, np.where(df["close"] < lo, -1.0, 0.0))
        state = pd.Series(raw, index=df.index).replace(0.0, np.nan).ffill().fillna(0.0)
        return state.to_numpy() * self.oz


REGISTRY = {
    "ema_cross_9_21": lambda: EmaCrossStrategy(9, 21),
    "ema_cross_12_26": lambda: EmaCrossStrategy(12, 26),
    "donchian_breakout_20": lambda: DonchianBreakoutStrategy(20),
}


def make_strategy(name: str) -> BaseStrategy:
    if name not in REGISTRY:
        raise KeyError(f"unknown strategy '{name}', options: {list(REGISTRY)}")
    return REGISTRY[name]()
