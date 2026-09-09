# -*- coding: utf-8 -*-
"""
XAUUSD 5m Technical Indicator Library
=====================================
Pure pandas/numpy implementation of ~60 classic technical indicators,
designed for the 3-year XAUUSD 5-minute dataset (211k bars).

Guarantees:
- NO lookahead bias: every indicator uses only current & past bars.
- No external TA dependency (no TA-Lib / pandas-ta needed).

Categories:
  1. Trend / Moving Averages   (11)
  2. MACD family                (3)
  3. Momentum oscillators       (15)
  4. Volatility / Bands         (14)
  5. Trend strength             (6)
  6. Statistical / micro        (14)

Usage:
    from indicators_library import add_all_indicators
    df = add_all_indicators(df)   # df needs: open, high, low, close
"""
import numpy as np
import pandas as pd

# Annualization for 5-minute bars: 288 bars/day * 252 trading days
ANNUAL_ROOT_5M = np.sqrt(288 * 252.0)


def _wilder(series: pd.Series, period: int) -> pd.Series:
    """Wilder's smoothing (RMA), alpha = 1/period, matching TA-Lib behaviour."""
    return series.ewm(alpha=1.0 / period, adjust=False, min_periods=period).mean()


# ----------------------------------------------------------------------
# 1. Trend / Moving Averages (11)
# ----------------------------------------------------------------------
def add_moving_averages(df: pd.DataFrame) -> pd.DataFrame:
    c = df["close"]
    for p in (10, 20, 50, 200):
        df[f"sma_{p}"] = c.rolling(p).mean()
    for p in (9, 12, 21, 26, 50, 200):
        df[f"ema_{p}"] = c.ewm(span=p, adjust=False).mean()

    def _wma(x):
        w = np.arange(1, len(x) + 1, dtype=float)
        return np.dot(w, x) / w.sum()

    df["wma_20"] = c.rolling(20).apply(_wma, raw=True)
    return df


# ----------------------------------------------------------------------
# 2. MACD family (3)
# ----------------------------------------------------------------------
def add_macd(df: pd.DataFrame, fast: int = 12, slow: int = 26, signal: int = 9) -> pd.DataFrame:
    c = df["close"]
    ema_fast = c.ewm(span=fast, adjust=False).mean()
    ema_slow = c.ewm(span=slow, adjust=False).mean()
    df["macd_dif"] = ema_fast - ema_slow
    df["macd_dea"] = df["macd_dif"].ewm(span=signal, adjust=False).mean()
    df["macd_hist"] = df["macd_dif"] - df["macd_dea"]
    return df


# ----------------------------------------------------------------------
# 3. Momentum oscillators (15)
# ----------------------------------------------------------------------
def add_momentum(df: pd.DataFrame) -> pd.DataFrame:
    c, h, l = df["close"], df["high"], df["low"]

    # --- RSI (Wilder) x3 ---
    delta = c.diff()
    for p in (6, 14, 24):
        gain = delta.clip(lower=0.0)
        loss = (-delta).clip(lower=0.0)
        avg_gain = _wilder(gain, p)
        avg_loss = _wilder(loss, p)
        rs = avg_gain / avg_loss                     # NaN during warm-up
        rsi = 100.0 - 100.0 / (1.0 + rs)             # inf loss -> 100 naturally
        rsi = rsi.mask((avg_loss == 0) & avg_loss.notna(), 50.0)  # flat window -> 50
        df[f"rsi_{p}"] = rsi

    # --- Stochastic (14,3) ---
    ll14 = l.rolling(14).min()
    hh14 = h.rolling(14).max()
    df["stoch_k_14"] = (c - ll14) / (hh14 - ll14).replace(0.0, np.nan) * 100.0
    df["stoch_d_14"] = df["stoch_k_14"].rolling(3).mean()

    # --- Stochastic RSI (14,3,3) ---
    rsi14 = df["rsi_14"]
    rll = rsi14.rolling(14).min()
    rhh = rsi14.rolling(14).max()
    stoch_rsi = (rsi14 - rll) / (rhh - rll).replace(0.0, np.nan) * 100.0
    df["stochrsi_k"] = stoch_rsi.rolling(3).mean()
    df["stochrsi_d"] = df["stochrsi_k"].rolling(3).mean()

    # --- KDJ (9,3,3) ---
    ll9 = l.rolling(9).min()
    hh9 = h.rolling(9).max()
    rsv = (c - ll9) / (hh9 - ll9).replace(0.0, np.nan) * 100.0
    df["kdj_k"] = rsv.ewm(alpha=1.0 / 3, adjust=False).mean()
    df["kdj_d"] = df["kdj_k"].ewm(alpha=1.0 / 3, adjust=False).mean()
    df["kdj_j"] = 3.0 * df["kdj_k"] - 2.0 * df["kdj_d"]

    # --- CCI (14) ---
    tp = (h + l + c) / 3.0
    sma_tp = tp.rolling(14).mean()

    def _meandev(x):
        m = x.mean()
        return np.abs(x - m).mean()

    md = tp.rolling(14).apply(_meandev, raw=True)
    df["cci_14"] = (tp - sma_tp) / (0.015 * md.replace(0.0, np.nan))

    # --- Williams %R (14) ---
    df["williams_r_14"] = (hh14 - c) / (hh14 - ll14).replace(0.0, np.nan) * -100.0

    # --- Momentum (10) & ROC (12) ---
    df["momentum_10"] = c - c.shift(10)
    df["roc_12"] = (c / c.shift(12) - 1.0) * 100.0
    return df


# ----------------------------------------------------------------------
# 4. Volatility / Bands (14)
# ----------------------------------------------------------------------
def add_volatility(df: pd.DataFrame, bb_period: int = 20, bb_std: float = 2.0) -> pd.DataFrame:
    c, h, l = df["close"], df["high"], df["low"]

    # --- True Range & ATR (7/14/28) + NATR ---
    prev_c = c.shift(1)
    tr = pd.concat([h - l, (h - prev_c).abs(), (l - prev_c).abs()], axis=1).max(axis=1)
    df["tr"] = tr
    for p in (7, 14, 28):
        df[f"atr_{p}"] = _wilder(tr, p)
    df["natr_14"] = df["atr_14"] / c * 100.0

    # --- Bollinger Bands (20, 2) ---
    mid = c.rolling(bb_period).mean()
    sd = c.rolling(bb_period).std()
    up = mid + bb_std * sd
    low = mid - bb_std * sd
    df["bb_up"] = up
    df["bb_mid"] = mid
    df["bb_low"] = low
    df["bb_width"] = (up - low) / mid * 100.0
    span = up - low
    pct_b = (c - low) / span
    pct_b = pct_b.where(span.notna(), np.nan)     # keep warm-up NaN
    df["bb_pct_b"] = pct_b.mask(span == 0, 0.5)   # zero-width band -> 0.5

    # --- Keltner Channel (20 EMA of TP, 2 x ATR14) ---
    tp = (h + l + c) / 3.0
    kc_mid = tp.ewm(span=20, adjust=False).mean()
    df["kc_mid"] = kc_mid
    df["kc_up"] = kc_mid + 2.0 * df["atr_14"]
    df["kc_low"] = kc_mid - 2.0 * df["atr_14"]

    # --- Donchian Channel (20) ---
    df["donchian_up_20"] = h.rolling(20).max()
    df["donchian_low_20"] = l.rolling(20).min()
    df["donchian_mid_20"] = (df["donchian_up_20"] + df["donchian_low_20"]) / 2.0
    return df


# ----------------------------------------------------------------------
# 5. Trend strength (6)
# ----------------------------------------------------------------------
def add_trend_strength(df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
    h, l, c = df["high"], df["low"], df["close"]

    # --- ADX / +DI / -DI (Wilder) ---
    up_move = h.diff()
    down_move = -l.diff()
    plus_dm = pd.Series(np.where((up_move > down_move) & (up_move > 0), up_move, 0.0), index=df.index)
    minus_dm = pd.Series(np.where((down_move > up_move) & (down_move > 0), down_move, 0.0), index=df.index)
    atr = _wilder(df["tr"], period)
    plus_di = 100.0 * _wilder(plus_dm, period) / atr.replace(0.0, np.nan)
    minus_di = 100.0 * _wilder(minus_dm, period) / atr.replace(0.0, np.nan)
    df["plus_di_14"] = plus_di
    df["minus_di_14"] = minus_di
    dx = 100.0 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0.0, np.nan)
    df["adx_14"] = _wilder(dx, period)

    # --- Aroon (25) ---
    w = 25

    def _aroon_up(x):
        return 100.0 * (x.argmax() + 1.0) / w

    def _aroon_down(x):
        return 100.0 * (x.argmin() + 1.0) / w

    df["aroon_up_25"] = h.rolling(w).apply(_aroon_up, raw=True)
    df["aroon_down_25"] = l.rolling(w).apply(_aroon_down, raw=True)

    # --- Parabolic SAR (0.02, 0.2) ---
    df["psar"] = _parabolic_sar(h.values, l.values, c.values)
    return df


def _parabolic_sar(high: np.ndarray, low: np.ndarray, close: np.ndarray,
                   af_step: float = 0.02, af_max: float = 0.2) -> np.ndarray:
    """Causal Parabolic SAR. Value at bar i uses data up to bar i only."""
    n = len(high)
    sar = np.full(n, np.nan)
    bull = high[1] >= high[0]
    ep = high[1] if bull else low[1]
    sar[1] = low[0] if bull else high[0]
    af = af_step
    for i in range(2, n):
        prev = sar[i - 1]
        cur = prev + af * (ep - prev)
        if bull:
            cur = min(cur, high[i - 1], high[i - 2])
            if low[i] < cur:                      # reversal
                bull, cur, ep, af = False, ep, low[i], af_step
            elif high[i] > ep:
                ep, af = high[i], min(af + af_step, af_max)
        else:
            cur = max(cur, low[i - 1], low[i - 2])
            if high[i] > cur:                     # reversal
                bull, cur, ep, af = True, ep, high[i], af_step
            elif low[i] < ep:
                ep, af = low[i], min(af + af_step, af_max)
        sar[i] = cur
    return sar


# ----------------------------------------------------------------------
# 6. Statistical / micro-structure (14)
# ----------------------------------------------------------------------
def add_statistical(df: pd.DataFrame) -> pd.DataFrame:
    c, o, h, l = df["close"], df["open"], df["high"], df["low"]

    # --- Z-score (20) ---
    m20 = c.rolling(20).mean()
    s20 = c.rolling(20).std()
    df["zscore_20"] = (c - m20) / s20.replace(0.0, np.nan)

    # --- Linear regression slope (20), per-bar, normalized by price ---
    w = 20
    x = np.arange(w, dtype=float)

    def _slope(y):
        xm, ym = x.mean(), y.mean()
        denom = ((x - xm) ** 2).sum()
        if denom == 0:
            return np.nan
        return float(((x - xm) * (y - ym)).sum() / denom)

    df["linreg_slope_20"] = c.rolling(w).apply(_slope, raw=True) / c

    # --- Historical volatility (20 & 96 bars, annualized) + ratio ---
    logret = np.log(c / c.shift(1))
    df["hv_20"] = logret.rolling(20).std() * ANNUAL_ROOT_5M * 100.0
    df["hv_96"] = logret.rolling(96).std() * ANNUAL_ROOT_5M * 100.0
    df["hv_ratio"] = df["hv_20"] / df["hv_96"].replace(0.0, np.nan)

    # --- Choppiness Index (14) ---
    hi14 = h.rolling(14).max()
    lo14 = l.rolling(14).min()
    tr_sum = df["tr"].rolling(14).sum()
    rng = (hi14 - lo14).replace(0.0, np.nan)
    df["choppiness_14"] = 100.0 * np.log10(tr_sum / rng) / np.log10(14.0)

    # --- Candle anatomy ---
    rng_c = (h - l).replace(0.0, np.nan)
    body = c - o
    df["candle_body_pct"] = body / rng_c * 100.0
    df["upper_shadow_pct"] = (h - pd.concat([o, c], axis=1).max(axis=1)) / rng_c * 100.0
    df["lower_shadow_pct"] = (pd.concat([o, c], axis=1).min(axis=1) - l) / rng_c * 100.0
    df["hl_range_pct"] = (h - l) / o * 100.0

    # --- Gap & Close Location Value ---
    prev_c = c.shift(1)
    df["gap_pct"] = (o - prev_c) / prev_c * 100.0
    df["clv"] = ((c - l) - (h - c)) / rng_c

    # --- Distance to key MAs ---
    df["close_vs_ema200_pct"] = (c / df["ema_200"] - 1.0) * 100.0
    df["close_vs_sma20_pct"] = (c / df["sma_20"] - 1.0) * 100.0
    return df


# ----------------------------------------------------------------------
# Aggregate
# ----------------------------------------------------------------------
def add_all_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Apply all indicator groups. df needs columns: open, high, low, close."""
    df = add_volatility(df)        # tr/atr first (ADX & Keltner depend on it)
    df = add_moving_averages(df)
    df = add_macd(df)
    df = add_momentum(df)
    df = add_trend_strength(df)
    df = add_statistical(df)
    return df


INDICATOR_COLUMNS = [
    # 1. trend / MA (11)
    "sma_10", "sma_20", "sma_50", "sma_200", "ema_9", "ema_12", "ema_21",
    "ema_26", "ema_50", "ema_200", "wma_20",
    # 2. MACD (3)
    "macd_dif", "macd_dea", "macd_hist",
    # 3. momentum (14)
    "rsi_6", "rsi_14", "rsi_24", "stoch_k_14", "stoch_d_14", "stochrsi_k",
    "stochrsi_d", "kdj_k", "kdj_d", "kdj_j", "cci_14", "williams_r_14",
    "momentum_10", "roc_12",
    # 4. volatility (16)
    "tr", "atr_7", "atr_14", "atr_28", "natr_14", "bb_up", "bb_mid", "bb_low",
    "bb_width", "bb_pct_b", "kc_mid", "kc_up", "kc_low", "donchian_up_20",
    "donchian_low_20", "donchian_mid_20",
    # 5. trend strength (6)
    "adx_14", "plus_di_14", "minus_di_14", "aroon_up_25", "aroon_down_25", "psar",
    # 6. statistical (14)
    "zscore_20", "linreg_slope_20", "hv_20", "hv_96", "hv_ratio", "choppiness_14",
    "candle_body_pct", "upper_shadow_pct", "lower_shadow_pct", "hl_range_pct",
    "gap_pct", "clv", "close_vs_ema200_pct", "close_vs_sma20_pct",
]
# 11 + 3 + 14 + 16 + 6 + 14 = 64 indicators
