# -*- coding: utf-8 -*-
"""Resample the 5m OHLC dataset to a higher timeframe (default 15m).

Gate.io TradFi serves only ~84 days of native 15m klines, so the 2.5-year
15m series used for research is aggregated from the validated 5m dataset.

Bar convention is preserved: the output timestamp is the bar START, and a
15m bar's close is only known at start + 900s (no lookahead for consumers
that decide at bar close and fill at the next open).

Validation:
  1. accounting: every 5m bar maps into exactly one output bucket
  2. exact OHLC spot-check of random buckets against the raw 5m rows
  3. OHLC sanity (high >= max(o,c), low <= min(o,c)) on all buckets
  4. timestamp monotonicity / uniqueness
  5. gap report: bucket-size gaps vs daily-break / weekend gaps

Usage:
  python scripts/resample_timeframe.py [--tf 15m]
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
TF_SECONDS = {"5m": 300, "15m": 900, "30m": 1800, "1h": 3600}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tf", default="15m", choices=sorted(TF_SECONDS))
    ap.add_argument("--src", default=ROOT / "data" / "xauusd_5m.csv")
    args = ap.parse_args()
    src = Path(args.src)
    dst = ROOT / "data" / f"xauusd_{args.tf}.csv"
    step = TF_SECONDS[args.tf]

    t0 = time.time()
    print(f"loading {src.name} ...")
    raw = pd.read_csv(src)
    n_raw = len(raw)
    ts = raw["timestamp"].to_numpy(np.int64)
    assert np.all(np.diff(ts) > 0), "raw 5m timestamps not strictly increasing"

    bucket = pd.Series((ts // step) * step, name="timestamp")
    g = raw.groupby(bucket, sort=True)
    out = g.agg(open=("open", "first"), high=("high", "max"),
                low=("low", "min"), close=("close", "last")).reset_index()
    out["datetime_utc"] = pd.to_datetime(out["timestamp"], unit="s").dt.strftime(
        "%Y-%m-%d %H:%M:%S")
    out = out[["timestamp", "datetime_utc", "open", "high", "low", "close"]]
    n_out = len(out)

    ok = True
    print(f"\n[1/5] accounting: {n_raw:,} 5m bars -> {n_out:,} {args.tf} bars")
    counts = g.size().to_numpy()
    full = int((counts == step // 300).sum())
    partial = n_out - full
    print(f"      buckets with all {step // 300} 5m bars: {full:,}   partial (session edges/gaps): {partial:,}")
    if counts.sum() != n_raw:
        print("      FAIL: 5m bars lost in aggregation")
        ok = False

    print("[2/5] exact OHLC spot-check on 500 random buckets ...")
    rng = np.random.default_rng(7)
    sample = out["timestamp"].to_numpy(np.int64)[rng.choice(n_out, size=500, replace=False)]
    bmap = pd.DataFrame({"bucket": bucket, "ts": ts, "o": raw["open"], "h": raw["high"],
                         "l": raw["low"], "c": raw["close"]})
    worst = 0.0
    for b in sample:
        rows = bmap[bmap["bucket"] == b].sort_values("ts")
        r = out[out["timestamp"] == b].iloc[0]
        worst = max(worst,
                    abs(rows["o"].iloc[0] - r["open"]),
                    abs(rows["h"].max() - r["high"]),
                    abs(rows["l"].min() - r["low"]),
                    abs(rows["c"].iloc[-1] - r["close"]))
    print(f"      worst absolute OHLC diff: {worst:.2e}  {'OK' if worst == 0 else 'FAIL'}")
    ok &= worst == 0

    print("[3/5] OHLC sanity on all buckets ...")
    bad = int(((out["high"] < out[["open", "close"]].max(axis=1)) |
               (out["low"] > out[["open", "close"]].min(axis=1)) |
               (out["high"] < out["low"])).sum())
    print(f"      violated buckets: {bad}  {'OK' if bad == 0 else 'FAIL'}")
    ok &= bad == 0

    print("[4/5] timestamps ...")
    ots = out["timestamp"].to_numpy(np.int64)
    mono = bool(np.all(np.diff(ots) > 0))
    print(f"      strictly increasing: {mono}  {'OK' if mono else 'FAIL'}")
    ok &= mono

    print("[5/5] gap structure (bucket-start deltas) ...")
    d = np.diff(ots)
    intraday = int((d == step).sum())
    daily = int(((d > step) & (d <= 4 * 3600)).sum())
    weekend = int((d > 4 * 3600).sum())
    print(f"      contiguous {args.tf} steps: {intraday:,}   daily-break gaps: {daily:,}   "
          f"weekend/long gaps: {weekend:,}   max gap: {d.max() / 3600:.1f} h")

    print(f"\nwriting {dst.name} ...")
    out.to_csv(dst, index=False)
    print(f"done in {time.time() - t0:.1f}s -> {dst} ({dst.stat().st_size / 1e6:.1f} MB)")
    print("ALL CHECKS PASSED" if ok else "SOME CHECKS FAILED")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
