"""Single-account attribution: where does the integrated system's loss come from?

Decomposes the locked integrated specification (long plus_di_14 / short
close_vs_ema200, regime-gated) along four axes, without touching the consumed
development segment for any selection:

  1. leg x exit-rule x accounting: each leg alone through the fast path
     (protective exits marked at bar CLOSE) vs the event engine (protective
     exits fill at the adverse bar EXTREME + re-entry lock);
  2. sum-of-legs vs one unified account (reversal / hold-refresh effect);
  3. realized-trade decomposition of the combined stop system by exit reason,
     direction, UTC session and regime, plus the exact stop-fill gap vs close;
  4. beta benchmarks: buy-and-hold and gate-conditioned always-long under the
     identical cost model.

All numbers are USD at 1 oz (0.01 lot); cost model $0.16/oz round trip.
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

from analysis.combo_screening import (SHORT_FAMILY_EXT, SURVIVORS, build_gates,
                                      build_path_stopped, holdout_split,
                                      masks_from_spec, md_table, parse_spec)
from analysis.factor_screening import (ANN, OZ, Session, build_factors,
                                       build_path, config_metrics,
                                       pnl_from_path, rolling_z)
from backtest import BacktestConfig, BacktestEngine
from scripts.run_integration import LONG_GATE, LONG_SPEC, SHORT_GATE, SHORT_SPEC, unified_targets

DATA = ROOT / "data" / "xauusd_5m_indicators.csv.gz"
REPORT = ROOT / "report" / "attribution.md"
STOP_ATR = 2.5
SESSIONS = [("asia", 0, 7), ("london", 7, 13), ("ny", 13, 21), ("late", 21, 24)]


def seg_bar_metrics(res, lo: int, hi: int) -> dict:
    pnl = np.diff(np.r_[res.config.initial_capital, res.equity])[lo:hi]
    curve = np.cumsum(pnl)
    dd = float((curve - np.maximum.accumulate(curve)).min()) if len(curve) else 0.0
    sh = float(pnl.mean() / pnl.std() * ANN) if len(pnl) > 2 and pnl.std() else 0.0
    tr = res.trades
    tr = tr[(tr["entry_i"] >= lo) & (tr["entry_i"] < hi)] if not tr.empty else tr
    return {"pnl": float(pnl.sum()), "sharpe": sh, "maxdd": dd,
            "trades": int(len(tr)), "costs": float(tr["costs"].sum()) if len(tr) else 0.0,
            "avg": float(tr["net_pnl"].mean()) if len(tr) else float("nan")}


def seg_trades(trades: pd.DataFrame, lo: int, hi: int) -> pd.DataFrame:
    if trades.empty:
        return trades
    return trades[(trades["entry_i"] >= lo) & (trades["entry_i"] < hi)].reset_index(drop=True)


def leg_target(ld: np.ndarray, sd: np.ndarray, h_long: int, h_short: int) -> np.ndarray:
    tgt, _ = unified_targets(ld, sd, h_long, h_short)
    return tgt


def fast_metrics(ld: np.ndarray, sd: np.ndarray, hold_l: int, hold_s: int,
                 ses: Session, o: np.ndarray, c: np.ndarray, n: int,
                 atr: np.ndarray | None, h_idx: int,
                 stop_atr: float | None) -> tuple[dict, dict]:
    """Fast-path (mark-to-close protective exits) segment metrics."""
    if stop_atr is None:
        pos, corr, trades = build_path(ld, sd, hold_l, ses, o, c, n)
    else:
        pos, corr, trades = build_path_stopped(ld, sd, hold_l, ses, o, c, n, atr,
                                               stop_atr=stop_atr)
    B = pnl_from_path(pos, o, c, ses.flat, corr)
    res = config_metrics(B, trades, 0, h_idx)
    dev = config_metrics(B, trades, h_idx, n)
    for m in (res, dev):
        m["costs"] = round(2 * 0.08 * m["trades"], 0)
        m["avg"] = m.pop("avg_usd")
    return res, dev


def row(label: str, m: dict) -> dict:
    return {"run": label, "pnl": round(m["pnl"], 0), "sharpe": round(m["sharpe"], 2),
            "maxdd": round(m["maxdd"], 0), "trades": m["trades"],
            "avg": round(m["avg"], 2) if np.isfinite(m["avg"]) else float("nan"),
            "costs": round(m["costs"], 0)}


def main() -> None:
    df = pd.read_csv(DATA)
    ts = pd.to_datetime(df["timestamp"], unit="s")
    n = len(df)
    h_idx, dev_start = holdout_split(df["timestamp"].to_numpy(np.int64), 183)
    factors, gates = build_factors(df), build_gates(df)
    atr_arr = df["atr_14"].to_numpy(float)
    o = df["open"].to_numpy(float)
    c = df["close"].to_numpy(float)
    ses = Session(df["timestamp"].to_numpy(np.int64))

    def gate(names: str) -> np.ndarray:
        out = np.ones(n, dtype=bool)
        for nm in names.split(","):
            out &= gates[nm.strip()]
        return out

    def zget(name, window):
        return rolling_z(factors[name], window)

    long_cfg, short_cfg = parse_spec(LONG_SPEC), parse_spec(SHORT_SPEC)
    ld, _ = masks_from_spec(long_cfg, zget, SURVIVORS, gate(LONG_GATE), None)
    _, sd = masks_from_spec(short_cfg, zget, SHORT_FAMILY_EXT, None, gate(SHORT_GATE))
    tgt_comb = leg_target(ld, sd, long_cfg["hold"], short_cfg["hold"])
    tgt_long = leg_target(ld, np.zeros(n, bool), long_cfg["hold"], short_cfg["hold"])
    tgt_short = leg_target(np.zeros(n, bool), sd, long_cfg["hold"], short_cfg["hold"])
    reversals = int(((np.diff(tgt_comb) * tgt_comb[:-1]) < 0).sum())

    eng_plain = BacktestEngine(BacktestConfig())
    eng_stop = BacktestEngine(BacktestConfig(stop_loss_atr=STOP_ATR))

    runs: list[dict] = []

    def add(label: str, engine, tgt: np.ndarray) -> tuple[dict, dict]:
        res = engine.run(df, tgt, atr=atr_arr if engine is eng_stop else None,
                         meta={"strategy": label})
        r, d = seg_bar_metrics(res, 0, h_idx), seg_bar_metrics(res, h_idx, n)
        runs.append({"run": label, "seg": "research", **row(label, r)})
        runs.append({"run": label, "seg": "dev", **row(label, d)})
        return r, d

    fast_rows: list[dict] = []
    for label, ldm, sdm, hl, hs in (
        ("long_gated", ld, np.zeros(n, bool), long_cfg["hold"], short_cfg["hold"]),
        ("short_gated", np.zeros(n, bool), sd, long_cfg["hold"], short_cfg["hold"]),
    ):
        for exit_lbl, stop in (("none", None), ("stop2.5", STOP_ATR)):
            r, d = fast_metrics(ldm, sdm, hl, hs, ses, o, c, n, atr_arr, h_idx, stop)
            for seg, m in (("research", r), ("dev", d)):
                rr = row(label, m)
                rr["run"] = f"{label}|fast(close-fill)|{exit_lbl}"
                rr["seg"] = seg
                fast_rows.append(rr)

    leg_pairs = {
        "long_gated": (tgt_long, ld, np.zeros(n, bool)),
        "short_gated": (tgt_short, np.zeros(n, bool), sd),
    }
    eng_metrics: dict[str, dict] = {}
    for label, (tgt, ldm, sdm) in leg_pairs.items():
        for exit_lbl, eng in (("none", eng_plain), ("stop2.5", eng_stop)):
            r, d = add(f"{label}|engine(extreme-fill)|{exit_lbl}", eng, tgt)
            eng_metrics[(label, exit_lbl)] = (r, d)

    comb_metrics = {}
    for exit_lbl, eng in (("none", eng_plain), ("stop2.5", eng_stop)):
        r, d = add(f"combined|engine(extreme-fill)|{exit_lbl}", eng, tgt_comb)
        comb_metrics[exit_lbl] = (r, d)

    # ---- benchmarks (same cost model, same sizing) ----
    bh = eng_plain.run(df, np.ones(n) * OZ, meta={"strategy": "buy_hold"})
    r, d = seg_bar_metrics(bh, 0, h_idx), seg_bar_metrics(bh, h_idx, n)
    for seg, m in (("research", r), ("dev", d)):
        rr = row("bh", m)
        rr["run"], rr["seg"] = "buy_hold_long(overnight)", seg
        runs.append(rr)
    gate_long_tgt = np.where(gate("trend_up"), OZ, 0.0)
    gl = eng_plain.run(df, gate_long_tgt, meta={"strategy": "gated_always_long"})
    r, d = seg_bar_metrics(gl, 0, h_idx), seg_bar_metrics(gl, h_idx, n)
    for seg, m in (("research", r), ("dev", d)):
        rr = row("gl", m)
        rr["run"], rr["seg"] = "always_long@trend_up(intraday)", seg
        runs.append(rr)

    # ---- realized-trade decomposition of the combined stop system ----
    res_c = eng_stop.run(df, tgt_comb, atr=atr_arr, meta={"strategy": "combined_stop"})
    trades = res_c.trades
    trades = seg_trades(trades, 0, n)

    by_reason = (trades.groupby(["side", "exit_reason"])
                 .agg(trades=("net_pnl", "size"), pnl=("net_pnl", "sum"),
                      avg=("net_pnl", "mean"), costs=("costs", "sum"))
                 .reset_index())
    by_reason["side"] = by_reason["side"].map({1: "long", -1: "short"})
    for col in ("pnl", "avg", "costs"):
        by_reason[col] = by_reason[col].round(2)
    by_reason["avg"] = by_reason["avg"].round(2)

    hours = pd.to_datetime(trades["entry_time"], unit="s").dt.hour
    bucket = pd.Series(np.select(
        [hours < 7, hours < 13, hours < 21], ["asia", "london", "ny"], "late"),
        index=trades.index)
    by_sess = (trades.assign(session=bucket)
               .groupby("session")
               .agg(trades=("net_pnl", "size"), pnl=("net_pnl", "sum"), avg=("net_pnl", "mean"))
               .reindex([s for s, _, _ in SESSIONS]).reset_index().round(2))

    trend_up = gates["trend_up"][trades["entry_i"].to_numpy()]
    adx = gates["adx_strong"][trades["entry_i"].to_numpy()]
    regime = np.select([trend_up & adx, trend_up, ~trend_up & adx],
                       ["trend_up+adx", "trend_up", "trend_down+adx"], "trend_down")
    by_reg = (trades.assign(regime=regime)
              .groupby("regime")
              .agg(trades=("net_pnl", "size"), pnl=("net_pnl", "sum"), avg=("net_pnl", "mean"))
              .reset_index().round(2))

    # exact stop-fill gap: engine exit at adverse extreme vs the trigger bar close
    stop_tr = trades[trades["exit_reason"] == "stop_loss"]
    close_px = c[stop_tr["exit_i"].to_numpy()]
    gap = ((close_px - stop_tr["exit_px"]) * stop_tr["side"] * stop_tr["oz"]).sum()

    # hold-expiry ('signal') exits that were NOT reversals
    sig = trades[trades["exit_reason"] == "signal"].copy()
    is_rev = []
    nxt = trades["entry_i"].to_numpy()
    for _, t in sig.iterrows():
        same_bar = np.flatnonzero(nxt == t["exit_i"])
        is_rev.append(bool(len(same_bar) and trades.iloc[same_bar[0]]["side"] == -t["side"]))
    sig["reversal"] = is_rev

    # ---- derived deltas ----
    def delta(a: dict, b: dict) -> float:
        return round(a["pnl"] - b["pnl"], 0)

    lr, ld_ = eng_metrics[("long_gated", "stop2.5")]
    sr, sd_ = eng_metrics[("short_gated", "stop2.5")]
    cr, cd = comb_metrics["stop2.5"]
    lr0, _ = eng_metrics[("long_gated", "none")]
    sr0, _ = eng_metrics[("short_gated", "none")]
    cr0, _ = comb_metrics["none"]

    lines = [
        "# Single-Account Attribution — integrated long/short system",
        "",
        f"- data: {ts.iloc[0]:%Y-%m-%d} -> {ts.iloc[-1]:%Y-%m-%d} ({n:,} bars); research [0, {h_idx}), dev [{h_idx}, {n})",
        "- sizing: 1 oz (0.01 lot); cost $0.16/oz round trip all-in; all PnL in USD.",
        f"- long `{LONG_SPEC}` gate `{LONG_GATE}`; short `{SHORT_SPEC}` gate `{SHORT_GATE}`",
        f"- unified account: opposing signals reverse at next open; same-bar dual signals flatten ({reversals} reversals observed).",
        "- 'fast(close-fill)' = research fast path, protective exits marked at bar CLOSE, exits at next open, immediate re-entry allowed.",
        "- 'engine(extreme-fill)' = BacktestEngine, protective exits fill at the adverse bar EXTREME, position locked flat until the target goes flat or opposing.",
        "",
        "## 1. Leg x exit x accounting (research / dev, USD @ 1 oz)",
        "",
        "| run | seg | pnl | sharpe | maxdd | trades | avg | costs |",
        "|---|---|---:|---:|---:|---:|---:|---:|",
    ]
    order = ["long_gated|fast(close-fill)|none", "long_gated|fast(close-fill)|stop2.5",
             "long_gated|engine(extreme-fill)|none", "long_gated|engine(extreme-fill)|stop2.5",
             "short_gated|fast(close-fill)|none", "short_gated|fast(close-fill)|stop2.5",
             "short_gated|engine(extreme-fill)|none", "short_gated|engine(extreme-fill)|stop2.5",
             "combined|engine(extreme-fill)|none", "combined|engine(extreme-fill)|stop2.5",
             "buy_hold_long(overnight)", "always_long@trend_up(intraday)"]
    for name in order:
        for seg in ("research", "dev"):
            rr = next((x for x in runs + fast_rows if x["run"] == name and x["seg"] == seg), None)
            if rr:
                lines.append(f"| {name} | {seg} | {rr['pnl']:+,.0f} | {rr['sharpe']:.2f} | "
                             f"{rr['maxdd']:+,.0f} | {rr['trades']} | {rr['avg']:+.2f} | {rr['costs']:+,.0f} |")

    lines += [
        "",
        "## 2. Deltas (research period, USD @ 1 oz)",
        "",
        "| comparison | long leg | short leg | combined |",
        "|---|---:|---:|---:|",
        f"| engine none -> engine stop2.5 (exit-rule cost) | {delta(lr0, lr):+,.0f} | {delta(sr0, sr):+,.0f} | {delta(cr0, cr):+,.0f} |",
        f"| sum-of-legs -> single account (both stop2.5) | - | - | {cr['pnl'] - (lr['pnl'] + sr['pnl']):+,.0f} |",
        f"| sum-of-legs -> single account (no exits) | - | - | {cr0['pnl'] - (lr0['pnl'] + sr0['pnl']):+,.0f} |",
        "",
        "## 3. Realized trades of the combined stop2.5 system (full history)",
        "",
        "### by side x exit reason",
        "",
        md_table(by_reason.rename(columns={"pnl": "net_pnl"})),
        "",
        "### by entry session (UTC)",
        "",
        md_table(by_sess),
        "",
        "### by regime at entry",
        "",
        md_table(by_reg),
        "",
        f"- stop-loss exits filling at the adverse bar extreme instead of the trigger-bar close cost an exact **${gap:,.2f}** extra on {len(stop_tr)} stop trades (pure fill-model gap vs close, same trades).",
        f"- 'signal' exits: {int(sig['reversal'].sum())} were reversals (PnL {sig.loc[sig['reversal'], 'net_pnl'].sum():+,.2f}), "
        f"{int((~sig['reversal']).sum())} were hold expiries (PnL {sig.loc[~sig['reversal'], 'net_pnl'].sum():+,.2f}).",
        "",
        "## Conclusions",
        "",
    ]

    # auto-written conclusions from the numbers (no dev-set tuning: dev only displayed)
    stop_cost_leg = delta(lr0, lr)
    lines += [
        f"1. **Exit rule, not direction, is the largest controllable loss.** Moving the long leg from no-exit to a 2.5xATR fixed stop costs "
        f"${delta(lr0, lr):+,.0f} of research PnL on the engine (fill-at-extreme + re-entry lock); the short leg changes by ${delta(sr0, sr):+,.0f}.",
        f"2. **Sum-of-legs vs one account:** with stop2.5 the legs sum to ${lr['pnl'] + sr['pnl']:+,.0f} while the unified account makes ${cr['pnl']:+,.0f} "
        f"(interaction ${delta(cr, {'pnl': lr['pnl'] + sr['pnl']}):+,.0f}); without exits the legs sum to ${lr0['pnl'] + sr0['pnl']:+,.0f} vs unified ${cr0['pnl']:+,.0f}.",
        f"3. **Fill model:** {len(stop_tr)} stop exits filled at the bar extreme cost ${gap:,.2f} more than the same exits at the trigger-bar close "
        f"(${gap / max(len(stop_tr), 1):.2f}/trade) - the fast path's mark-to-close convention materially overstated stop-system performance.",
        f"4. **Beta check:** buy-and-hold makes ${next(x['pnl'] for x in runs if x['run'] == 'buy_hold_long(overnight)' and x['seg'] == 'research'):+,.0f} research / "
        f"${next(x['pnl'] for x in runs if x['run'] == 'buy_hold_long(overnight)' and x['seg'] == 'dev'):+,.0f} dev under identical costs; "
        f"the gate-conditioned always-long makes ${next(x['pnl'] for x in runs if x['run'] == 'always_long@trend_up(intraday)' and x['seg'] == 'research'):+,.0f} research. "
        "Any candidate must beat these passive references to claim factor alpha.",
        "5. Dev columns are diagnosis only; nothing here selects parameters.",
    ]

    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    pd.DataFrame(runs + fast_rows).to_csv(ROOT / "report" / "attribution_runs.csv", index=False)
    print(f"saved {REPORT.relative_to(ROOT)}")
    print("\n".join(lines[lines.index("## Conclusions") + 2:]))


if __name__ == "__main__":
    main()
