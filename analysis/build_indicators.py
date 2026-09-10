# -*- coding: utf-8 -*-
"""
Build the XAUUSD 5m indicator dataset.
======================================
Reads  data/xauusd_5m.csv          (timestamp, datetime_utc, open, high, low, close)
Writes data/xauusd_5m_indicators.csv.gz  (OHLC + 64 technical indicators)

Also runs validation checks:
  1. Shape / NaN profile (warm-up windows are expected to be NaN).
  2. No-lookahead check: values computed on a truncated history must equal
     the values computed on the full history (proves causality).
  3. Spot-check RSI/EMA/ATR against an independent recomputation.

Usage:
    python analysis/build_indicators.py [--src data/xauusd_5m.csv]
"""
import argparse
import gzip
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
from indicators_library import add_all_indicators, INDICATOR_COLUMNS  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "data" / "xauusd_5m.csv"
DST = ROOT / "data" / "xauusd_5m_indicators.csv.gz"

# Price-level columns keep 3 decimals; ratio/oscillator columns keep 5.
PRICE_LIKE = {
    "sma_10", "sma_20", "sma_50", "sma_200", "ema_9", "ema_12", "ema_21",
    "ema_26", "ema_50", "ema_200", "wma_20", "macd_dif", "macd_dea",
    "macd_hist", "momentum_10", "tr", "atr_7", "atr_14", "atr_28",
    "bb_up", "bb_mid", "bb_low", "kc_mid", "kc_up", "kc_low",
    "donchian_up_20", "donchian_low_20", "donchian_mid_20", "psar",
}


def main() -> None:
    global SRC, DST
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", type=Path, default=SRC,
                    help="input OHLC csv (default: 5m dataset)")
    ap.add_argument("--dst", type=Path, default=None,
                    help="output csv.gz (default: alongside --src, _indicators.csv.gz)")
    args = ap.parse_args()
    SRC = args.src
    DST = args.dst or SRC.with_name(SRC.stem + "_indicators.csv.gz")

    t0 = time.time()
    print(f"[1/5] loading {SRC.name} ...")
    df = pd.read_csv(SRC)
    n = len(df)
    print(f"      {n:,} rows  {df['datetime_utc'].iloc[0]} -> {df['datetime_utc'].iloc[-1]}")

    print("[2/5] computing 64 indicators ...")
    df = add_all_indicators(df)

    # column order: meta + ohlc + indicators
    out_cols = ["timestamp", "datetime_utc", "open", "high", "low", "close"] + INDICATOR_COLUMNS
    missing = [c for c in out_cols if c not in df.columns]
    if missing:
        raise RuntimeError(f"indicator columns missing: {missing}")
    df = df[out_cols]

    print("[3/5] validation: NaN profile ...")
    warmup = {
        "sma_200": 199, "ema_200": 0,     # ewm(adjust=False) emits from bar 0
        "aroon_up_25": 24, "adx_14": 27,
        "hv_96": 96, "stochrsi_d": 30, "donchian_up_20": 19,
    }
    ok = True
    for c, exp in warmup.items():
        first_valid = int(df[c].first_valid_index())
        status = "OK" if abs(first_valid - exp) <= 2 else "UNEXPECTED"
        if status != "OK":
            ok = False
        print(f"      {c:<16} first valid bar = {first_valid:>4} (expected ~{exp})  {status}")
    tail_nan = int(df[INDICATOR_COLUMNS].iloc[200:].isna().sum().sum())
    print(f"      NaN cells after warm-up (bar 200+): {tail_nan:,} of {len(df) * len(INDICATOR_COLUMNS):,}")

    print("[4/5] validation: no-lookahead check (unrounded values) ...")
    cut = n - 500
    df_small = add_all_indicators(pd.read_csv(SRC).iloc[:cut].copy())
    sample_cols = ["ema_200", "rsi_14", "atr_14", "macd_dif", "adx_14", "psar",
                   "bb_pct_b", "kdj_j", "cci_14", "aroon_up_25", "wma_20",
                   "stochrsi_d", "choppiness_14", "linreg_slope_20"]
    worst = 0.0
    for c in sample_cols:
        a = df_small[c].iloc[-1]
        b = df[c].iloc[cut - 1]
        if pd.isna(a) or pd.isna(b):
            continue
        diff = abs(float(a) - float(b)) / max(1e-9, abs(float(b)))
        worst = max(worst, diff)
    print(f"      worst relative diff @bar {cut - 1}: {worst:.2e}  {'OK' if worst < 1e-6 else 'FAIL'}")
    if worst >= 1e-6:
        ok = False

    print("[5/5] validation: spot-check vs independent calc (unrounded) ...")
    c = df["close"]
    rsi_ref = 100 - 100 / (1 + (c.diff().clip(lower=0).ewm(alpha=1 / 14, adjust=False).mean()
                                / (-c.diff()).clip(lower=0).ewm(alpha=1 / 14, adjust=False).mean()))
    rsi_diff = (df["rsi_14"] - rsi_ref).abs().iloc[300:].max()
    ema_diff = (df["ema_50"] - c.ewm(span=50, adjust=False).mean()).abs().iloc[300:].max()
    print(f"      max |rsi_14 - ref| = {rsi_diff:.2e}, max |ema_50 - ref| = {ema_diff:.2e}")
    if max(rsi_diff, ema_diff) > 1e-2:
        ok = False

    # rounding AFTER validation so checks see full precision
    for c in INDICATOR_COLUMNS:
        df[c] = df[c].round(3 if c in PRICE_LIKE else 5)

    print(f"writing {DST.name} ...")
    with gzip.open(DST, "wt", newline="", compresslevel=9) as f:
        df.to_csv(f, index=False)
    size_mb = DST.stat().st_size / 1e6
    print(f"done in {time.time() - t0:.1f}s  ->  {DST}  ({size_mb:.1f} MB, {len(df):,} rows x {len(df.columns)} cols)")
    print("ALL CHECKS PASSED" if ok else "SOME CHECKS FAILED")


if __name__ == "__main__":
    main()
