"""Event-consistent backtest engine.

Loop per bar i:
  1. OPEN     : fill the order decided at close of bar i-1 (cross spread)
  2. INTRABAR : check SL/TP against high/low (stop priority when both hit)
  3. CLOSE    : session-flat rule (intraday cutoff / Friday early close)
  4. mark equity at close
  5. read target_oz[i] -> queued as the order filled at open of bar i+1

Targets are SIGNED OUNCES decided using information up to close of bar i only.
The engine never looks ahead; strategies must not either (see validate.py).

Accounting: fills are at raw mid prices; the all-in round-trip cost
(spread+slippage+commission, USD/oz) is charged as explicit cash costs split
half per side, so `gross_pnl` (mid-to-mid) and `costs` in the trade log
decompose exactly.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from .config import BacktestConfig


@dataclass
class BacktestResult:
    config: BacktestConfig
    equity: np.ndarray                 # mark-to-market at each bar close
    timestamps: np.ndarray             # unix seconds per bar
    trades: pd.DataFrame               # closed-trade log
    runtime_sec: float = 0.0
    meta: dict = field(default_factory=dict)


def _hhmm_to_td(s: str) -> pd.Timedelta:
    """'20:55' or '20:55:00' -> Timedelta."""
    parts = s.split(":")
    if len(parts) == 2:
        s += ":00"
    return pd.Timedelta(s)


class BacktestEngine:
    def __init__(self, config: BacktestConfig | None = None):
        self.cfg = config or BacktestConfig()

    # ------------------------------------------------------------------ #
    def run(
        self,
        df: pd.DataFrame,
        target_oz: np.ndarray | pd.Series,
        warmup_bars: int = 0,
        meta: dict | None = None,
    ) -> BacktestResult:
        """Run the backtest.

        df must contain: timestamp, open, high, low, close (5m bars, UTC).
        target_oz[i]: desired signed position in oz decided at close of bar i.
        Values before `warmup_bars` are forced to 0.
        """
        cfg = self.cfg
        t0 = time.perf_counter()

        ts = df["timestamp"].to_numpy(dtype=np.int64)
        o = df["open"].to_numpy(dtype=float)
        h = df["high"].to_numpy(dtype=float)
        l = df["low"].to_numpy(dtype=float)
        c = df["close"].to_numpy(dtype=float)
        n = len(df)

        tgt = np.asarray(target_oz, dtype=float)
        if len(tgt) != n:
            raise ValueError(f"target_oz length {len(tgt)} != bars {n}")
        tgt = np.where(np.isfinite(tgt), tgt, 0.0)
        tgt[:warmup_bars] = 0.0
        tgt = np.clip(tgt, -cfg.max_position_oz, cfg.max_position_oz)

        flat, blocked = self._session_masks(ts, cfg.intraday_only)
        side_cost = cfg.side_cost_usd          # USD/oz per side (half of round-trip cost)
        comm_rate = cfg.commission_bps / 1e4   # of notional, per side
        has_protective = bool(cfg.stop_loss_usd or cfg.take_profit_usd)
        sl_usd = cfg.stop_loss_usd or 0.0
        tp_usd = cfg.take_profit_usd or 0.0

        cash = cfg.initial_capital
        pos = 0.0                    # signed oz currently held
        entry_px = 0.0               # raw mid fill price of the open position
        pending_tgt = 0.0            # decided at close of i-1, filled at open i
        equity = np.empty(n)
        trades: list[dict] = []
        cur: dict | None = None

        def _cost(raw_px: float, oz: float) -> float:
            return oz * side_cost + oz * raw_px * comm_rate

        def _open_trade(i: int, raw_px: float, signed_oz: float, reason: str) -> None:
            nonlocal cash, pos, cur, entry_px
            oz = abs(signed_oz)
            if signed_oz > 0:                      # buy: debit
                cash -= oz * raw_px
            else:                                  # sell short: proceeds in
                cash += oz * raw_px
            ecost = _cost(raw_px, oz)
            cash -= ecost
            pos = signed_oz
            entry_px = raw_px
            cur = {
                "entry_i": i,
                "entry_time": int(ts[i]),
                "side": 1 if signed_oz > 0 else -1,
                "oz": oz,
                "entry_px": raw_px,
                "entry_reason": reason,
                "entry_cost": ecost,
            }

        def _close_trade(i: int, raw_px: float, reason: str) -> None:
            nonlocal cash, pos, cur, entry_px
            oz, side, epx = cur["oz"], cur["side"], cur["entry_px"]
            if side > 0:                           # long: sell now
                cash += oz * raw_px
                gross = (raw_px - epx) * oz
            else:                                  # short: buy back now
                cash -= oz * raw_px
                gross = (epx - raw_px) * oz
            xcost = _cost(raw_px, oz)
            cash -= xcost
            trades.append({
                **cur,
                "exit_i": i,
                "exit_time": int(ts[i]),
                "exit_px": raw_px,
                "gross_pnl": gross,
                "costs": cur["entry_cost"] + xcost,
                "net_pnl": gross - cur["entry_cost"] - xcost,
                "bars_held": i - cur["entry_i"],
                "exit_reason": reason,
            })
            pos, cur, entry_px = 0.0, None, 0.0

        for i in range(n):
            # ---- 1) fill pending order at the OPEN of bar i ----
            if abs(pending_tgt - pos) > 1e-9:
                if pos != 0.0:
                    _close_trade(i, o[i], "signal")
                if pending_tgt != 0.0:
                    _open_trade(i, o[i], pending_tgt, "signal")
                pending_tgt = pos

            # ---- 2) protective exits, intrabar via high/low ----
            if pos != 0.0 and has_protective:
                sgn = 1.0 if pos > 0 else -1.0
                stop_hit = tp_hit = False
                if pos > 0:
                    if sl_usd and l[i] <= entry_px - sl_usd:
                        stop_hit = True
                    elif tp_usd and h[i] >= entry_px + tp_usd:
                        tp_hit = True
                else:
                    if sl_usd and h[i] >= entry_px + sl_usd:
                        stop_hit = True
                    elif tp_usd and l[i] <= entry_px - tp_usd:
                        tp_hit = True
                if stop_hit:
                    _close_trade(i, entry_px - sgn * sl_usd, "stop_loss")
                elif tp_hit:
                    _close_trade(i, entry_px + sgn * tp_usd, "take_profit")

            # ---- 3) session flat at the CLOSE of bar i ----
            if flat[i] and pos != 0.0:
                _close_trade(i, c[i], "session")

            # ---- 4) mark equity ----
            equity[i] = cash + pos * c[i]

            # ---- 5) decision at close of bar i -> fill at open of i+1 ----
            tgt_i = tgt[i]
            if blocked[i]:
                tgt_i = 0.0
            pending_tgt = tgt_i

        if pos != 0.0:   # safety net (should not happen in intraday mode)
            _close_trade(n - 1, c[-1], "session")

        trades_df = pd.DataFrame(trades)
        if not trades_df.empty:
            trades_df = trades_df.sort_values("entry_i").reset_index(drop=True)

        return BacktestResult(
            config=cfg,
            equity=equity,
            timestamps=ts,
            trades=trades_df,
            runtime_sec=time.perf_counter() - t0,
            meta=meta or {},
        )

    # ------------------------------------------------------------------ #
    def _session_masks(self, ts: np.ndarray, intraday_only: bool) -> tuple[np.ndarray, np.ndarray]:
        """Per-bar (is_flat_bar, entry_blocked) from UTC bar-start timestamps.

        A bar "decides" at its CLOSE (start + 5m). The first bar whose close
        time reaches the daily cutoff flattens the book; entries are blocked
        once the close time falls inside the pre-cutoff buffer.
        """
        cfg = self.cfg
        dt = pd.to_datetime(ts, unit="s")              # naive UTC bar starts
        close_dt = pd.to_datetime(ts + 300, unit="s")  # bar close times
        day0 = dt.normalize()

        cutoff = day0 + _hhmm_to_td(cfg.eod_flat_utc)
        fri_cut = day0 + _hhmm_to_td(cfg.friday_flat_utc)
        cutoff = cutoff.where(dt.weekday != 4, fri_cut)

        if not intraday_only:
            z = np.zeros(len(ts), dtype=bool)
            return z, z

        flat = close_dt >= cutoff
        blocked = (close_dt > cutoff - pd.Timedelta(minutes=cfg.entry_block_minutes)) | flat
        return np.asarray(flat), np.asarray(blocked)
