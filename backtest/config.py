"""Backtest configuration (all prices in USD per ounce, XAUUSD CFD)."""

from dataclasses import dataclass


@dataclass
class BacktestConfig:
    # --- account ---
    initial_capital: float = 10_000.0

    # --- position sizing: targets are expressed in OUNCES (signed) ---
    max_position_oz: float = 1.0     # 0.01 lot = 1 oz

    # --- friction (all-in: spread + slippage + commission) ---
    round_trip_cost_usd: float = 0.16  # USD/oz paid per entry+exit round trip (Gate.io actual)
    commission_bps: float = 0.0        # EXTRA bps of notional per side (default none — 0.16 is all-in)

    # --- session rules (UTC; bar timestamps are bar-START times) ---
    bar_seconds: int = 300           # bar duration (300 = 5m bars, 900 = 15m bars)
    intraday_only: bool = True       # force flat at the daily cutoff
    eod_flat_utc: str = "20:55"      # bar closing at/after this time is the last bar
    friday_flat_utc: str = "20:45"   # Friday: close earlier, avoid the weekend gap
    entry_block_minutes: int = 15    # no new entries within N minutes before cutoff

    # --- optional protective exits (USD per ounce from entry fill price) ---
    stop_loss_usd: float | None = None
    take_profit_usd: float | None = None

    # ATR exits use the ATR value available at the entry decision.  All three
    # use the deliberately conservative OHLC fill convention in the engine.
    stop_loss_atr: float | None = None
    take_profit_atr: float | None = None
    trailing_stop_atr: float | None = None

    @property
    def side_cost_usd(self) -> float:
        """Friction per ounce for ONE side (entry or exit)."""
        return self.round_trip_cost_usd / 2.0
