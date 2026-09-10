"""Interfaces for future point-in-time external features.

No provider downloads data in this revision.  Implementations must expose the
timestamp at which an observation became knowable, not merely its observation
period, before it can be aligned to 5-minute XAUUSD bars.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

import pandas as pd


@dataclass(frozen=True)
class ExternalFeatureSpec:
    name: str
    frequency: str
    publication_lag: str
    availability_column: str
    alignment: str
    missing_policy: str = "no_trade"


class ExternalFeatureProvider(Protocol):
    spec: ExternalFeatureSpec

    def load(self) -> pd.DataFrame:
        """Return values indexed by their actual availability timestamp."""

    def align_to_bars(self, bars: pd.DataFrame) -> pd.Series:
        """Backward-only align; must never forward-fill before availability."""


PLANNED_FEATURES = (
    ExternalFeatureSpec("dxy", "intraday/daily", "provider timestamp", "available_at", "backward_asof"),
    ExternalFeatureSpec("real_yield", "daily", "provider timestamp", "available_at", "backward_asof"),
    ExternalFeatureSpec("cot", "weekly", "release timestamp", "available_at", "backward_asof"),
    ExternalFeatureSpec("macro_event", "event", "scheduled release timestamp", "available_at", "event_window"),
)
