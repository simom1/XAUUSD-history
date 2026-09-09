#!/usr/bin/env python3
"""
Quantitative analysis for XAUUSD CFD kline data (CSV files in data/).

Generates an interactive HTML report (plotly) with:
  - headline risk/return metrics
  - price overview, return distribution, QQ plot
  - rolling volatility & drawdown
  - autocorrelation of returns / |returns|
  - intraday & weekday seasonality (requires 1d data present)
  - technical indicators (MA / Bollinger / RSI) when >= 250 bars

Usage:
    python analysis/quant_analysis.py [--data-dir data] [--out report/quant_analysis_report.html]
"""
import argparse
import glob
import os

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from scipy import stats

TF_ORDER = ["1m", "5m", "15m", "30m", "1h", "4h", "1d"]
# approximate bars per year for CFD gold (23h/day, 5d/week)
PPY = {"1d": 252.0, "1h": 5796.0, "4h": 1449.0, "30m": 11592.0,
       "15m": 23184.0, "5m": 69552.0, "1m": 347760.0}


# ----------------------------------------------------------------- data ----
def load_data(data_dir):
    files = sorted(glob.glob(os.path.join(data_dir, "*.csv")))
    if not files:
        raise SystemExit(f"No CSV files found in {data_dir}")
    data = {}
    for f in files:
        tf = os.path.splitext(os.path.basename(f))[0].split("_")[-1]
        df = pd.read_csv(f)
        if "datetime_utc" in df.columns:
            df["dt"] = pd.to_datetime(df["datetime_utc"])
        else:
            df["dt"] = pd.to_datetime(df["timestamp"], unit="s")
        df = df.sort_values("timestamp").reset_index(drop=True)
        data[tf] = df
    ordered = {tf: data[tf] for tf in TF_ORDER if tf in data}
    return ordered


# ------------------------------------------------------------ statistics ----
def hurst_exponent(series, max_lag=100):
    """Hurst via rescaled range on log price path (cumulative log returns)."""
    lp = np.log(series.values)
    x = np.diff(lp).cumsum()
    lags = range(2, min(max_lag, len(x) // 4))
    tau = [np.std(x[lag:] - x[:-lag]) for lag in lags]
    tau = np.array([t for t in tau if t > 0])
    if len(tau) < 5:
        return np.nan
    return float(np.polyfit(np.log(list(lags)[:len(tau)]), np.log(tau), 1)[0])


def risk_metrics(ret, ann_factor):
    r = ret.dropna()
    mean, std = r.mean(), r.std()
    downside = r[r < 0].std()
    sharpe = mean / std * np.sqrt(ann_factor) if std > 0 else np.nan
    sortino = mean / downside * np.sqrt(ann_factor) if downside and downside > 0 else np.nan
    cum = (1 + r).cumprod()
    peak = cum.cummax()
    dd = (cum / peak - 1).min()
    var95 = np.percentile(r, 5)
    cvar95 = r[r <= var95].mean()
    var99 = np.percentile(r, 1)
    cvar99 = r[r <= var99].mean()
    ann_ret = (cum.iloc[-1]) ** (ann_factor / len(r)) - 1
    return {"annual_return": ann_ret, "annual_vol": std * np.sqrt(ann_factor),
            "sharpe": sharpe, "sortino": sortino, "max_dd": dd,
            "var95": var95, "cvar95": cvar95, "var99": var99, "cvar99": cvar99}


def rsi(series, period=14):
    delta = series.diff()
    gain = delta.clip(lower=0).ewm(alpha=1 / period, adjust=False).mean()
    loss = (-delta.clip(upper=0)).ewm(alpha=1 / period, adjust=False).mean()
    rs = gain / loss
    return 100 - 100 / (1 + rs)


# --------------------------------------------------------------- figures ----
DARK = "#0e1117"

def style_fig(fig, title):
    fig.update_layout(template="plotly_dark", title=title,
                      paper_bgcolor=DARK, plot_bgcolor=DARK,
                      height=460, margin=dict(l=40, r=30, t=60, b=40),
                      hovermode="x unified")
    return fig


def fig_price(df, tf):
    fig = go.Figure()
    if len(df) <= 5000:
        fig.add_trace(go.Candlestick(
            x=df["dt"], open=df["open"], high=df["high"],
            low=df["low"], close=df["close"], name=tf,
            increasing_line_color="#26a69a", decreasing_line_color="#ef5350"))
        fig.update_layout(xaxis_rangeslider_visible=False)
    else:
        fig.add_trace(go.Scatter(x=df["dt"], y=df["close"], name="close",
                                 line=dict(color="#f7b733", width=1)))
    return style_fig(fig, f"XAUUSD price overview — {tf} ({df['dt'].iloc[0]:%Y-%m-%d} → {df['dt'].iloc[-1]:%Y-%m-%d})")


def fig_distribution(ret, tf):
    fig = make_subplots(rows=1, cols=2, subplot_titles=("Return distribution vs normal", "QQ plot"))
    r = ret.dropna()
    fig.add_trace(go.Histogram(x=r, nbinsx=120, histnorm="probability density",
                               name="actual", marker_color="#4c78a8"), row=1, col=1)
    xs = np.linspace(r.min(), r.max(), 300)
    fig.add_trace(go.Scatter(x=xs, y=stats.norm.pdf(xs, r.mean(), r.std()),
                             name="normal", line=dict(color="#ef5350", width=2)), row=1, col=1)
    qs = np.linspace(0.01, 0.99, 200)
    fig.add_trace(go.Scatter(x=stats.norm.ppf(qs, r.mean(), r.std()),
                             y=np.percentile(r, qs * 100), mode="markers",
                             marker=dict(size=4, color="#f7b733"), name="QQ"), row=1, col=2)
    fig.add_trace(go.Scatter(x=[r.min(), r.max()], y=[r.min(), r.max()],
                             mode="lines", line=dict(color="#666", dash="dash"),
                             showlegend=False), row=1, col=2)
    fig.update_layout(template="plotly_dark", height=420,
                      paper_bgcolor=DARK, plot_bgcolor=DARK,
                      title=f"Return distribution — {tf}")
    return fig


def fig_risk(df, ret, tf, span=120):
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    price = df["close"].reset_index(drop=True)
    roll_vol = ret.rolling(span).std() * np.sqrt(PPY[tf]) * 100
    fig.add_trace(go.Scatter(x=df["dt"], y=price, name="price",
                             line=dict(color="#8884d8", width=1)), secondary_y=False)
    fig.add_trace(go.Scatter(x=df["dt"], y=roll_vol, name=f"rolling vol ({span}-bar, ann. %)",
                             line=dict(color="#ef5350", width=1), opacity=0.8), secondary_y=True)
    fig.update_yaxes(title_text="price", secondary_y=False)
    fig.update_yaxes(title_text="annualized vol %", secondary_y=True)
    return style_fig(fig, f"Price & rolling volatility — {tf}")


def fig_drawdown(df, ret, tf):
    r = ret.dropna().reset_index(drop=True)
    cum = (1 + r).cumprod()
    dd = cum / cum.cummax() - 1
    fig = go.Figure(go.Scatter(x=df["dt"].iloc[-len(dd):], y=dd * 100,
                               fill="tozeroy", name="drawdown %",
                               line=dict(color="#ef5350", width=1)))
    return style_fig(fig, f"Drawdown from running peak — {tf}")


def fig_autocorr(ret, tf, nlags=40):
    r = (ret.dropna() - ret.mean()).reset_index(drop=True)
    def acf(x, k):
        x = np.asarray(x, dtype=float)
        return np.array([1.0] + [np.corrcoef(x[:-i], x[i:])[0, 1] for i in range(1, k)])
    ks = np.arange(nlags)
    fig = make_subplots(rows=1, cols=2, subplot_titles=("ACF of returns", "ACF of |returns| (vol clustering)"))
    fig.add_trace(go.Bar(x=ks, y=acf(r, nlags), marker_color="#4c78a8", name="returns"), 1, 1)
    fig.add_trace(go.Bar(x=ks, y=acf(np.abs(r), nlags), marker_color="#f7b733", name="|returns|"), 1, 2)
    ci = 1.96 / np.sqrt(len(r))
    for c in (1, 2):
        fig.add_hline(y=ci, line=dict(color="#ef5350", dash="dash", width=1), row=1, col=c)
        fig.add_hline(y=-ci, line=dict(color="#ef5350", dash="dash", width=1), row=1, col=c)
    fig.update_layout(template="plotly_dark", height=420,
                      paper_bgcolor=DARK, plot_bgcolor=DARK,
                      title=f"Autocorrelation — {tf}")
    return fig


def fig_seasonality(data):
    if "1d" not in data:
        return None
    df1d = data["1d"].copy()
    df1d["ret"] = df1d["close"].pct_change()
    df1d["weekday"] = df1d["dt"].dt.dayofweek
    wd = df1d.groupby("weekday")["ret"].std() * np.sqrt(252) * 100
    wd_names = ["Mon", "Tue", "Wed", "Thu", "Fri"]
    # intraday hourly vol from the finest available intraday frame
    intraday_tf = next((t for t in ["1h", "30m", "15m", "5m", "1m"] if t in data), None)
    fig = make_subplots(rows=1, cols=2, subplot_titles=("Annualized volatility by weekday", "Mean |return| by UTC hour"))
    fig.add_trace(go.Bar(x=wd_names[:len(wd)], y=wd.values, marker_color="#4c78a8"), 1, 1)
    if intraday_tf:
        d = data[intraday_tf].copy()
        d["ret"] = d["close"].pct_change()
        d["hour"] = d["dt"].dt.hour
        hv = d.groupby("hour")["ret"].apply(lambda s: np.abs(s).mean()) * 100
        fig.add_trace(go.Bar(x=hv.index, y=hv.values, marker_color="#f7b733"), 1, 2)
    fig.update_layout(template="plotly_dark", height=420,
                      paper_bgcolor=DARK, plot_bgcolor=DARK,
                      title="Seasonality")
    return fig


def fig_indicators(df, tf):
    if len(df) < 250:
        return None
    d = df.copy()
    d["ma50"] = d["close"].rolling(50).mean()
    d["ma200"] = d["close"].rolling(200).mean()
    d["bb_mid"] = d["close"].rolling(20).mean()
    sd = d["close"].rolling(20).std()
    d["bb_up"], d["bb_lo"] = d["bb_mid"] + 2 * sd, d["bb_mid"] - 2 * sd
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.7, 0.3],
                        vertical_spacing=0.03)
    fig.add_trace(go.Scatter(x=d["dt"], y=d["close"], name="close", line=dict(color="#8884d8", width=1)), 1, 1)
    fig.add_trace(go.Scatter(x=d["dt"], y=d["ma50"], name="MA50", line=dict(color="#f7b733", width=1)), 1, 1)
    fig.add_trace(go.Scatter(x=d["dt"], y=d["ma200"], name="MA200", line=dict(color="#ef5350", width=1)), 1, 1)
    fig.add_trace(go.Scatter(x=d["dt"], y=d["bb_up"], name="BB upper", line=dict(color="#3d9970", width=1, dash="dot")), 1, 1)
    fig.add_trace(go.Scatter(x=d["dt"], y=d["bb_lo"], name="BB lower", line=dict(color="#3d9970", width=1, dash="dot")), 1, 1)
    fig.add_trace(go.Scatter(x=d["dt"], y=rsi(d["close"]), name="RSI(14)", line=dict(color="#f7b733", width=1)), 2, 1)
    fig.add_hline(y=70, line=dict(color="#ef5350", dash="dash", width=1), row=2, col=1)
    fig.add_hline(y=30, line=dict(color="#3d9970", dash="dash", width=1), row=2, col=1)
    fig.update_layout(template="plotly_dark", height=620,
                      paper_bgcolor=DARK, plot_bgcolor=DARK,
                      title=f"Technical indicators — {tf}",
                      margin=dict(l=40, r=30, t=60, b=40))
    return fig


# ------------------------------------------------------------------ main ----
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", default=os.path.join("data"))
    ap.add_argument("--out", default=os.path.join("report", "quant_analysis_report.html"))
    args = ap.parse_args()

    data = load_data(args.data_dir)
    head_tf = next(t for t in reversed(TF_ORDER) if t in data)  # coarsest
    df = data[head_tf]
    ret = df["close"].pct_change()

    m = risk_metrics(ret, PPY[head_tf])
    r = ret.dropna()
    jb = stats.jarque_bera(r)
    hurst = hurst_exponent(df["close"])

    cards = [
        ("Annualized return", f"{m['annual_return']*100:+.2f}%"),
        ("Annualized volatility", f"{m['annual_vol']*100:.2f}%"),
        ("Sharpe ratio", f"{m['sharpe']:.3f}"),
        ("Sortino ratio", f"{m['sortino']:.3f}"),
        ("Max drawdown", f"{m['max_dd']*100:.2f}%"),
        ("VaR 95% / CVaR 95%", f"{m['var95']*100:.2f}% / {m['cvar95']*100:.2f}%"),
        ("VaR 99% / CVaR 99%", f"{m['var99']*100:.2f}% / {m['cvar99']*100:.2f}%"),
        ("Hurst exponent", f"{hurst:.4f}"),
        ("Skewness", f"{r.skew():.4f}"),
        ("Excess kurtosis", f"{r.kurt():.4f}"),
        ("Jarque-Bera p-value", f"{jb.pvalue:.2e}"),
        ("Bars", f"{len(df):,}"),
    ]
    card_html = "".join(
        f"<div class='card'><div class='k'>{k}</div><div class='v'>{v}</div></div>"
        for k, v in cards)

    figs = [fig_price(df, head_tf),
            fig_distribution(ret, head_tf),
            fig_risk(df, ret, head_tf),
            fig_drawdown(df, ret, head_tf),
            fig_autocorr(ret, head_tf)]
    extra = [f for f in (fig_seasonality(data), fig_indicators(df, head_tf)) if f]
    figs += extra

    body = "".join(
        f"<div class='panel'>{f.to_html(full_html=False, include_plotlyjs=(i == 0))}</div>"
        for i, f in enumerate(figs))

    tf_table = "".join(
        f"<tr><td>{tf}</td><td>{len(d):,}</td>"
        f"<td>{d['dt'].iloc[0]:%Y-%m-%d}</td><td>{d['dt'].iloc[-1]:%Y-%m-%d}</td></tr>"
        for tf, d in data.items())

    html = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<title>XAUUSD Quantitative Analysis Report</title>
<style>
  body {{ font-family: 'Segoe UI', Arial, sans-serif; background:{DARK}; color:#e6e6e6; margin:0; padding:0; }}
  .wrap {{ max-width: 1200px; margin: 0 auto; padding: 24px; }}
  h1 {{ font-weight: 600; letter-spacing: .5px; }}
  .sub {{ color:#9aa0a6; margin-bottom: 24px; }}
  .cards {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(210px, 1fr)); gap: 12px; margin-bottom: 24px; }}
  .card {{ background:#161b22; border:1px solid #2d333b; border-radius:10px; padding:14px 16px; }}
  .card .k {{ font-size: 12px; color:#9aa0a6; text-transform: uppercase; letter-spacing: .5px; }}
  .card .v {{ font-size: 22px; font-weight: 600; margin-top: 6px; color:#f7b733; }}
  .panel {{ background:#161b22; border:1px solid #2d333b; border-radius:10px; padding:8px; margin-bottom:20px; }}
  table {{ border-collapse: collapse; width: 100%; }}
  td, th {{ padding: 6px 12px; border-bottom: 1px solid #2d333b; text-align: left; font-size: 14px; }}
  .note {{ color:#9aa0a6; font-size: 13px; }}
</style></head><body><div class="wrap">
<h1>🥇 XAUUSD Quantitative Analysis Report</h1>
<div class="sub">Gold vs USD (CFD) — headline metrics computed on the <b>{head_tf}</b> timeframe · annualization: {PPY[head_tf]:.0f} bars/year · for research &amp; education only, not investment advice</div>
<div class="cards">{card_html}</div>
<h3>Datasets loaded</h3>
<table><tr><th>timeframe</th><th>bars</th><th>from</th><th>to</th></tr>{tf_table}</table>
{body}
<div class="note">Generated by analysis/quant_analysis.py — regenerate anytime with <code>python analysis/quant_analysis.py</code>.</div>
</div></body></html>"""

    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"[OK] report written -> {args.out}")
    print(f"     {head_tf}: {len(df):,} bars | ann.ret {m['annual_return']*100:+.2f}% | "
          f"vol {m['annual_vol']*100:.2f}% | Sharpe {m['sharpe']:.2f} | maxDD {m['max_dd']*100:.2f}%")


if __name__ == "__main__":
    main()
