"""Backtest configuration (all prices in USD per ounce, XAUUSD CFD)."""

from dataclasses import dataclass


@dataclass
class BacktestConfig:
    # --- account ---
    initial_capital: float = 100_000.0

    # --- position sizing: targets are expressed in OUNCES (signed) ---
    max_position_oz: float = 100.0   # engine clips |target| to this

    # --- friction (all-in: spread + slippage + commission) ---
    round_trip_cost_usd: float = 0.16  # USD/oz paid per entry+exit round trip (Gate.io actual)
    commission_bps: float = 0.0        # EXTRA bps of notional per side (default none — 0.16 is all-in)

    # --- session rules (UTC; bar timestamps are bar-START times) ---
    intraday_only: bool = True       # force flat at the daily cutoff
    eod_flat_utc: str = "20:55"      # bar closing at/after this time is the last bar
    friday_flat_utc: str = "20:45"   # Friday: close earlier, avoid the weekend gap
    entry_block_minutes: int = 15    # no new entries within N minutes before cutoff

    # --- optional protective exits (USD per ounce from entry fill price) ---
    stop_loss_usd: float | None = None
    take_profit_usd: float | None = None

    @property
    def side_cost_usd(self) -> float:
        """Friction per ounce for ONE side (entry or exit)."""
        return self.round_trip_cost_usd / 2.0
