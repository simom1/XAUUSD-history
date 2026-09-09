# -*- coding: utf-8 -*-
"""Data quality audit for the XAUUSD 5m indicator dataset.

Checks:
  A. schema / shape
  B. timestamp grid: monotonicity, duplicates, 5m alignment, gap census
  C. OHLC consistency
  D. zero-range (dead-flat) candles
  E. NaN audit per indicator column (warm-up vs mid-series)
  F. bounded-range violations for oscillator-type indicators
  G. extreme 5m returns / price outliers
  H. yearly coverage summary

Usage:
  python analysis/data_quality.py
Output: console summary + report/data_quality_5m.md
"""
from __future__ import annotations

import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import numpy as np
import pandas as pd

from analysis.indicators_library import INDICATOR_COLUMNS

DATA = ROOT / "data" / "xauusd_5m_indicators.csv.gz"
OUT = ROOT / "report" / "data_quality_5m.md"

L: list[str] = []


def sec(title: str) -> None:
    L.append(f"\n## {title}\n")
    print(f"\n=== {title} ===")


def main() -> None:
    df = pd.read_csv(DATA)
    n = len(df)
    ts = pd.to_datetime(df["timestamp"], unit="s")
    o, h, lo, c = (df[k].to_numpy(float) for k in ("open", "high", "low", "close"))

    # ---------------- A. schema ----------------
    sec("A. Schema")
    L.append(f"- rows: **{n:,}**, columns: {df.shape[1]} "
             f"(6 price/time + {len(INDICATOR_COLUMNS)} indicators)")
    L.append(f"- time range: **{ts.iloc[0]} -> {ts.iloc[-1]}** "
             f"({(ts.iloc[-1] - ts.iloc[0]).days} calendar days)")
    missing_cols = [c_ for c_ in INDICATOR_COLUMNS if c_ not in df.columns]
    L.append(f"- indicator columns missing: {missing_cols or 'none'}")

    # ---------------- B. timestamp grid ----------------
    sec("B. Timestamp grid")
    mono = bool(ts.is_monotonic_increasing)
    dup = int(ts.duplicated().sum())
    aligned = int((df["timestamp"].to_numpy() % 300 != 0).sum())
    L.append(f"- strictly increasing: {mono}; duplicate timestamps: {dup}; "
             f"not 5m-aligned: {aligned}")

    dsec = ts.diff().dt.total_seconds()
    gap = dsec.iloc[1:]  # first is NaN
    normal = int((gap == 300).sum())
    L.append(f"- consecutive 5m steps: {normal:,} / {len(gap):,} "
             f"({normal / len(gap):.2%})")

    # classify non-300 gaps
    prev_t = ts.iloc[:-1].reset_index(drop=True)
    cur_t = ts.iloc[1:].reset_index(drop=True)
    g = pd.DataFrame({"prev": prev_t, "cur": cur_t, "gap_h": gap.to_numpy() / 3600.0})
    nz = g[g["gap_h"] > 5 / 60].copy()
    nz["wd_prev"] = nz["prev"].dt.weekday
    nz["wd_cur"] = nz["cur"].dt.weekday
    weekend = nz[(nz["wd_prev"] == 4) & (nz["wd_cur"].isin([6, 0]))]
    daily = nz[(nz["wd_prev"] != 4) | (~nz["wd_cur"].isin([6, 0]))]
    daily = daily[(daily["prev"].dt.date != daily["cur"].dt.date) &
                  (~daily.index.isin(weekend.index))]
    intraday = nz[~nz.index.isin(weekend.index.union(daily.index))]
    L.append(f"- non-5m gaps total: {len(nz)} -> intraday breaks: {len(intraday)}, "
             f"daily closes: {len(daily)}, weekend: {len(weekend)}")
    if len(intraday):
        L.append("\nIntraday breaks (same-day gaps > 5m):")
        L.append(intraday.head(10).to_string(index=False)
                 if len(intraday) <= 10 else
                 intraday.assign(bucket=nz["gap_h"].round(2))
                 .groupby("gap_h").size().rename("count").to_frame().T.to_string())
    # daily close pattern
    if len(daily):
        pat = daily.groupby([daily["prev"].dt.strftime("%H:%M"),
                             daily["cur"].dt.strftime("%H:%M")]).size()
        L.append("\nDaily close pattern (prev_close_time -> next_open_time):")
        L.append(pat.rename("count").to_string())
        L.append(f"- min/median/max daily-closure gap: "
                 f"{daily['gap_h'].min():.2f} / {daily['gap_h'].median():.2f} / "
                 f"{daily['gap_h'].max():.2f} h")
    if len(weekend):
        L.append(f"\nWeekend gaps: {len(weekend)} "
                 f"(min {weekend['gap_h'].min():.1f}h, max {weekend['gap_h'].max():.1f}h, "
                 f"median {weekend['gap_h'].median():.1f}h)")
        big = weekend[weekend["gap_h"] > weekend["gap_h"].median() + 12]
        if len(big):
            L.append("\nLong weekends / holiday closures:")
            L.append(big[["prev", "cur", "gap_h"]].to_string(index=False))

    # ---------------- C. OHLC consistency ----------------
    sec("C. OHLC consistency")
    bad_hl = int((h < lo).sum())
    bad_h = int(((h < o) | (h < c)).sum())
    bad_l = int(((lo > o) | (lo > c)).sum())
    nonpos = int((o <= 0).sum() + (c <= 0).sum())
    L.append(f"- high < low: {bad_hl}; high < max(open,close): {bad_h}; "
             f"low > min(open,close): {bad_l}; non-positive prices: {nonpos}")
    L.append(f"- price range: low min **{lo.min():.2f}**, high max **{h.max():.2f}**; "
             f"first close {c[0]:.2f}, last close {c[-1]:.2f}")

    # ---------------- D. zero-range candles ----------------
    sec("D. Zero-range candles")
    zr = (h == lo)
    flat_ohlc = zr & (o == c)
    L.append(f"- high == low: {int(zr.sum())} bars, of which open == close (fully flat): "
             f"{int(flat_ohlc.sum())}")
    if zr.any():
        zt = ts[zr]
        L.append(f"- zero-range dates: "
                 f"{sorted(set(zt.dt.date.astype(str)))[:25]}")
        L.append("- note: these make range-denominated indicators undefined "
                 "(clv, candle anatomy, zscore if sd==0) -> structural NaNs, not data loss")

    # ---------------- E. NaN audit ----------------
    sec("E. NaN audit per indicator column")
    rows = []
    for col in INDICATOR_COLUMNS:
        s = df[col]
        total = int(s.isna().sum())
        fv = s.first_valid_index()
        head_nan = fv if fv is not None else n
        mid = int(s.iloc[fv:].isna().sum()) if fv is not None else 0
        rows.append((col, total, head_nan, mid))
    nan_df = pd.DataFrame(rows, columns=["column", "nan_total", "warmup_bars", "mid_series_nan"])
    hot = nan_df[nan_df["mid_series_nan"] > 0]
    L.append(f"- columns with mid-series NaN (beyond warm-up): **{len(hot)}**")
    if len(hot):
        locs = {}
        for col in hot["column"]:
            s = df[col]
            fv = s.first_valid_index()
            idx = np.flatnonzero(s.iloc[fv:].isna().to_numpy()) + fv
            locs[col] = idx
        all_idx = np.unique(np.concatenate(list(locs.values())))
        L.append(f"- distinct bars affected: {len(all_idx)}")
        L.append(f"- timestamps: {ts.iloc[all_idx].dt.strftime('%Y-%m-%d %H:%M').tolist()}")
        L.append("\n| column | total NaN | warm-up bars | mid-series NaN |")
        L.append("|---|---:|---:|---:|")
        for _, r in hot.iterrows():
            L.append(f"| {r.column} | {r.nan_total} | {r.warmup_bars} | {r.mid_series_nan} |")
    warm = nan_df[nan_df["mid_series_nan"] == 0]
    L.append(f"\n- clean columns (only warm-up NaN): {len(warm)} / {len(nan_df)}; "
             f"max warm-up length: {int(warm['warmup_bars'].max())} bars "
             f"(ema_200/adx-family ~expected)")
    L.append(f"- total NaN cells: {int(nan_df['nan_total'].sum()):,} "
             f"of {n * len(INDICATOR_COLUMNS):,} indicator cells "
             f"({nan_df['nan_total'].sum() / (n * len(INDICATOR_COLUMNS)):.3%})")
    L.append("- volume column: NOT present (Gate.io TradFi klines provide no volume); "
             "volume-type indicators are out of scope by design")

    # ---------------- F. bounded ranges ----------------
    sec("F. Bounded-range checks")
    bounds = {
        "rsi_6": (0, 100), "rsi_14": (0, 100), "rsi_24": (0, 100),
        "stoch_k_14": (0, 100), "stoch_d_14": (0, 100),
        "stochrsi_k": (0, 100), "stochrsi_d": (0, 100),
        "kdj_k": (0, 100), "kdj_d": (0, 100),
        "williams_r_14": (-100, 0), "adx_14": (0, 100),
        "plus_di_14": (0, 500), "minus_di_14": (0, 500),
        "aroon_up_25": (0, 100), "aroon_down_25": (0, 100),
        "clv": (-1, 1), "bb_pct_b": (-1, 2), "choppiness_14": (0, 100),
    }
    viol = []
    for col, (b0, b1) in bounds.items():
        s = df[col].dropna()
        out = int(((s < b0) | (s > b1)).sum())
        if out:
            viol.append((col, out, float(s.min()), float(s.max())))
    L.append(f"- violations of theoretical bounds: {viol or 'none'}")

    # ---------------- G. extreme moves ----------------
    sec("G. Extreme 5m moves")
    ret = c[1:] / c[:-1] - 1.0
    k = 10
    top = np.argsort(np.abs(ret))[::-1][:k]
    L.append("| time | 5m return % | close |")
    L.append("|---|---:|---:|")
    for i in top:
        L.append(f"| {ts.iloc[i + 1]} | {ret[i] * 100:+.3f} | {c[i + 1]:.2f} |")
    L.append(f"- |ret| > 1%: {int((np.abs(ret) > 0.01).sum())} bars; "
             f"> 0.5%: {int((np.abs(ret) > 0.005).sum())} bars")

    # ---------------- H. yearly coverage ----------------
    sec("H. Yearly coverage")
    yr = ts.dt.year
    rows = []
    for y, gdf in df.groupby(yr):
        rows.append((int(y), len(gdf), ts[yr == y].iloc[0].strftime("%Y-%m-%d"),
                     ts[yr == y].iloc[-1].strftime("%Y-%m-%d"),
                     float(lo[yr == y].min()), float(h[yr == y].max())))
    L.append("| year | bars | from | to | min low | max high |")
    L.append("|---|---:|---|---|---:|---:|")
    for r in rows:
        L.append(f"| {r[0]} | {r[1]:,} | {r[2]} | {r[3]} | {r[4]:.2f} | {r[5]:.2f} |")
    L.append(f"- avg bars/day: {n / (ts.iloc[-1] - ts.iloc[0]).days:.1f} "
             f"(5m grid would be 288 if 24h continuous)")

    OUT.write_text("# XAUUSD 5m indicator dataset - data quality report\n"
                   + "\n".join(L) + "\n", encoding="utf-8")
    print(f"\nsaved: {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
