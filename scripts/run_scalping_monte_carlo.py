"""Monte Carlo robustness for the rank-aggregation scalping config.

Three perturbation tests on the best aggregation config selected on the
research period:

  1. Factor-family perturbation: drop 1-2 factors from the top-N family
     and re-evaluate.  Measures sensitivity to the specific factor set.
  2. Parameter perturbation: shift each aggregation parameter by +/-1 grid
     step and re-evaluate.  Measures sensitivity to parameter choice.
  3. Block bootstrap: resample per-bar returns in daily blocks (B=288 bars)
     with replacement, recompute Sharpe.  Builds a 95% CI for the Sharpe.

The config is frozen (selected on research, never re-selected).  All
perturbation evaluations use the full research period.
"""
from __future__ import annotations

import sys
from dataclasses import replace
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
import pandas as pd

from analysis.combo_screening import build_gates, holdout_split
from analysis.factor_screening import build_factors
from analysis.scalping_research import (
    AggregationConfig, build_grid, build_z_cache, fast_aggregation_score,
    run_aggregation_engine, select_aggregation_on_train,
    select_reversal_factors,
)
from analysis.system_research import bar_metrics

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "xauusd_5m_indicators.csv.gz"
REPORT = ROOT / "report" / "scalping_monte_carlo.md"

ANN_5M = float(np.sqrt(288 * 252))
FAST_WINDOW = 48
HORIZON = 12
MAX_N_FACTORS = 15
TOP_K_ENGINE = 20
N_BOOTSTRAP = 2000
BLOCK_BARS = 288          # 1 day of 5m bars
RNG_SEED = 20260911

# Grid (must match run_scalping_rank_aggregation.py)
METHODS = ("vote", "rank_avg", "z_composite")
N_FACTORS = (5, 7, 10)
WINDOWS = (288, 576)
THRESHOLDS = (1.5, 2.0)
VOTE_MINS = (2, 3, 4)
HOLDS = (6, 12, 24)
REGIMES = ("none", "trend", "trend_adx", "trend_not_choppy")
SESSIONS = ("all", "london", "new_york", "overlap")
EXITS = ("none", "stop1_5", "trail2")


def md_table(frame: pd.DataFrame, floatfmt: str = "{:.3f}") -> str:
    if frame is None or frame.empty:
        return "(none)"
    cols = list(frame.columns)
    lines = ["| " + " | ".join(str(c) for c in cols) + " |",
             "|" + "|".join("---:" for _ in cols) + "|"]
    for _, row in frame.iterrows():
        cells = []
        for col in cols:
            v = row[col]
            if isinstance(v, float):
                cells.append(floatfmt.format(v) if pd.notna(v) else "-")
            else:
                cells.append(str(v))
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


def trade_stats(t: pd.DataFrame) -> dict:
    if t is None or t.empty:
        return {"trades": 0, "wr": 0.0, "pf": 0.0, "avg_hold": 0.0}
    wins = float(t.loc[t.net_pnl > 0, "net_pnl"].sum())
    losses = float(-t.loc[t.net_pnl < 0, "net_pnl"].sum())
    return {"trades": int(len(t)),
            "wr": round(float((t.net_pnl > 0).mean() * 100), 1),
            "pf": round(wins / losses, 3) if losses > 0 else float("inf"),
            "avg_hold": round(float(t.bars_held.mean()), 1)}


def select_best_config(research: pd.DataFrame, n: int) -> dict:
    """Select the best aggregation config on the research period."""
    grid = build_grid(METHODS, N_FACTORS, WINDOWS, THRESHOLDS, VOTE_MINS,
                      HOLDS, REGIMES, SESSIONS, EXITS)
    sel = select_aggregation_on_train(research, grid, max_n_factors=MAX_N_FACTORS,
                                      horizon=HORIZON, fast_window=FAST_WINDOW,
                                      bar_seconds=300, ann=ANN_5M,
                                      min_trades=20, top_k_engine=TOP_K_ENGINE)
    return sel


def engine_eval(research: pd.DataFrame, factors: pd.DataFrame, gates: dict,
                cfg: AggregationConfig, factor_names: list[str]) -> dict:
    """Full engine evaluation, return metrics + per-bar PnL array."""
    result, _, m, _ = run_aggregation_engine(research, factors, factor_names, cfg,
                                              gates, bar_seconds=300, ann=ANN_5M)
    # per-bar PnL from equity curve
    pnl = np.diff(np.r_[result.config.initial_capital, result.equity])
    ts = trade_stats(result.trades)
    return {"sharpe": m["sharpe"], "pnl": m["pnl"], "maxdd": m["maxdd"],
            "trades": ts["trades"], "wr": ts["wr"], "pf": ts["pf"],
            "per_bar_pnl": pnl}


# ======================================================================
# Test 1: Factor-family perturbation
# ======================================================================
def test_factor_perturbation(lines: list, research: pd.DataFrame,
                             factors: pd.DataFrame, gates: dict,
                             cfg: AggregationConfig, family: list[str]) -> dict:
    lines += ["## Test 1 -- factor-family perturbation\n",
              f"Drop 1-2 factors from the top-{cfg.n_factors} set and re-evaluate. "
              f"This measures sensitivity to the specific factor choice.\n",
              f"- base family (top-{cfg.n_factors}): `{', '.join(family[:cfg.n_factors])}`\n"]

    base_fn = family[:cfg.n_factors]
    base_m = engine_eval(research, factors, gates, cfg, base_fn)
    base_sharpe = base_m["sharpe"]
    lines += [f"- base: Sharpe {base_sharpe:+.3f}, PnL ${base_m['pnl']:+,.2f}, "
              f"{base_m['trades']} trades\n"]

    # Drop 1 factor
    drop1_rows = []
    for i in range(len(base_fn)):
        perturbed = base_fn[:i] + base_fn[i + 1:]
        if len(perturbed) < 2:
            continue
        # Use n_factors = len(perturbed) via replace
        cfg_p = replace(cfg, n_factors=len(perturbed))
        m = engine_eval(research, factors, gates, cfg_p, perturbed)
        drop1_rows.append({
            "dropped": base_fn[i], "n": len(perturbed),
            "sharpe": round(m["sharpe"], 3), "pnl": round(m["pnl"], 2),
            "trades": m["trades"], "wr": m["wr"],
            "delta_sh": round(m["sharpe"] - base_sharpe, 3),
        })
        print(f"  drop {base_fn[i]:25s} sh={m['sharpe']:+.3f} "
              f"delta={m['sharpe'] - base_sharpe:+.3f}")

    drop1_df = pd.DataFrame(drop1_rows).sort_values("sharpe", ascending=False)
    lines += ["### Drop 1 factor\n",
              md_table(drop1_df[["dropped", "n", "sharpe", "pnl", "trades", "wr",
                                 "delta_sh"]]),
              "\n"]

    # Drop 2 factors (sample, not exhaustive)
    drop2_rows = []
    rng = np.random.default_rng(RNG_SEED)
    indices = list(range(len(base_fn)))
    pairs = [(i, j) for i in range(len(base_fn)) for j in range(i + 1, len(base_fn))]
    if len(pairs) > 15:
        pairs_idx = rng.choice(len(pairs), size=15, replace=False)
        pairs = [pairs[k] for k in pairs_idx]
    for i, j in pairs:
        perturbed = [f for k, f in enumerate(base_fn) if k not in (i, j)]
        if len(perturbed) < 2:
            continue
        cfg_p = replace(cfg, n_factors=len(perturbed))
        m = engine_eval(research, factors, gates, cfg_p, perturbed)
        drop2_rows.append({
            "dropped": f"{base_fn[i]}+{base_fn[j]}", "n": len(perturbed),
            "sharpe": round(m["sharpe"], 3), "pnl": round(m["pnl"], 2),
            "trades": m["trades"],
            "delta_sh": round(m["sharpe"] - base_sharpe, 3),
        })

    drop2_df = pd.DataFrame(drop2_rows).sort_values("sharpe", ascending=False)
    lines += ["### Drop 2 factors (sampled)\n",
              md_table(drop2_df[["dropped", "n", "sharpe", "pnl", "trades",
                                 "delta_sh"]]),
              "\n"]

    # Robustness summary
    all_deltas = drop1_df["delta_sh"].tolist() + drop2_df["delta_sh"].tolist()
    delta_arr = np.array(all_deltas)
    lines += [f"- drop-1 Sharpe range: [{drop1_df['sharpe'].min():+.3f}, "
              f"{drop1_df['sharpe'].max():+.3f}]",
              f"- drop-1 mean |delta Sharpe|: {drop1_df['delta_sh'].abs().mean():.3f}",
              f"- all perturbations: mean |delta Sharpe| = "
              f"{np.mean(np.abs(delta_arr)):.3f}",
              f"- all perturbations: max |delta Sharpe| = "
              f"{np.max(np.abs(delta_arr)):.3f}",
              f"- robustness: "
              f"{'HIGH' if np.max(np.abs(delta_arr)) < 0.5 else 'MODERATE' if np.max(np.abs(delta_arr)) < 1.0 else 'LOW'}\n"]

    return {"base_sharpe": base_sharpe,
            "drop1_mean_abs_delta": float(drop1_df["delta_sh"].abs().mean()),
            "max_abs_delta": float(np.max(np.abs(delta_arr)))}


# ======================================================================
# Test 2: Parameter perturbation
# ======================================================================
def test_param_perturbation(lines: list, research: pd.DataFrame,
                            factors: pd.DataFrame, gates: dict,
                            cfg: AggregationConfig, factor_names: list[str]) -> dict:
    lines += ["## Test 2 -- parameter perturbation\n",
              "Shift each aggregation parameter by +/-1 grid step and re-evaluate. "
              "Measures sensitivity to parameter choice.\n",
              f"- base config: `{cfg.key}`\n"]

    base_m = engine_eval(research, factors, gates, cfg, factor_names)
    base_sharpe = base_m["sharpe"]
    lines += [f"- base: Sharpe {base_sharpe:+.3f}, PnL ${base_m['pnl']:+,.2f}, "
              f"{base_m['trades']} trades\n"]

    # Build perturbation grid
    perturbs = []
    # window +/-1 step
    w_idx = WINDOWS.index(cfg.window)
    if w_idx > 0:
        perturbs.append(("window-", replace(cfg, window=WINDOWS[w_idx - 1])))
    if w_idx < len(WINDOWS) - 1:
        perturbs.append(("window+", replace(cfg, window=WINDOWS[w_idx + 1])))
    # threshold +/-1 step
    t_idx = THRESHOLDS.index(cfg.threshold)
    if t_idx > 0:
        perturbs.append(("thr-", replace(cfg, threshold=THRESHOLDS[t_idx - 1])))
    if t_idx < len(THRESHOLDS) - 1:
        perturbs.append(("thr+", replace(cfg, threshold=THRESHOLDS[t_idx + 1])))
    # hold +/-1 step
    h_idx = HOLDS.index(cfg.hold)
    if h_idx > 0:
        perturbs.append(("hold-", replace(cfg, hold=HOLDS[h_idx - 1])))
    if h_idx < len(HOLDS) - 1:
        perturbs.append(("hold+", replace(cfg, hold=HOLDS[h_idx + 1])))
    # vote_min +/-1 step (only for vote method)
    if cfg.method == "vote":
        v_idx = VOTE_MINS.index(cfg.vote_min)
        if v_idx > 0:
            perturbs.append(("vmin-", replace(cfg, vote_min=VOTE_MINS[v_idx - 1])))
        if v_idx < len(VOTE_MINS) - 1:
            perturbs.append(("vmin+", replace(cfg, vote_min=VOTE_MINS[v_idx + 1])))
    # n_factors +/-1 step
    nf_idx = N_FACTORS.index(cfg.n_factors)
    if nf_idx > 0:
        perturbs.append(("N-", replace(cfg, n_factors=N_FACTORS[nf_idx - 1])))
    if nf_idx < len(N_FACTORS) - 1:
        perturbs.append(("N+", replace(cfg, n_factors=N_FACTORS[nf_idx + 1])))

    rows = []
    for label, cfg_p in perturbs:
        fn = factor_names[:cfg_p.n_factors]
        m = engine_eval(research, factors, gates, cfg_p, fn)
        rows.append({
            "perturbation": label, "new_val": _perturb_value(label, cfg_p),
            "sharpe": round(m["sharpe"], 3), "pnl": round(m["pnl"], 2),
            "trades": m["trades"], "wr": m["wr"],
            "delta_sh": round(m["sharpe"] - base_sharpe, 3),
        })
        print(f"  {label:10s} sh={m['sharpe']:+.3f} delta={m['sharpe'] - base_sharpe:+.3f}")

    pdf = pd.DataFrame(rows).sort_values("sharpe", ascending=False)
    lines += ["### Parameter perturbations\n",
              md_table(pdf[["perturbation", "new_val", "sharpe", "pnl", "trades",
                            "wr", "delta_sh"]]),
              "\n"]

    max_delta = float(pdf["delta_sh"].abs().max())
    mean_delta = float(pdf["delta_sh"].abs().mean())
    lines += [f"- mean |delta Sharpe|: {mean_delta:.3f}",
              f"- max |delta Sharpe|: {max_delta:.3f}",
              f"- robustness: "
              f"{'HIGH' if max_delta < 0.5 else 'MODERATE' if max_delta < 1.0 else 'LOW'}\n"]

    return {"base_sharpe": base_sharpe, "mean_abs_delta": mean_delta,
            "max_abs_delta": max_delta}


def _perturb_value(label: str, cfg: AggregationConfig) -> str:
    if label.startswith("window"):
        return str(cfg.window)
    if label.startswith("thr"):
        return f"{cfg.threshold:g}"
    if label.startswith("hold"):
        return str(cfg.hold)
    if label.startswith("vmin"):
        return str(cfg.vote_min)
    if label.startswith("N"):
        return str(cfg.n_factors)
    return "?"


# ======================================================================
# Test 3: Block bootstrap
# ======================================================================
def test_block_bootstrap(lines: list, research: pd.DataFrame,
                         factors: pd.DataFrame, gates: dict,
                         cfg: AggregationConfig, factor_names: list[str]) -> dict:
    lines += ["## Test 3 -- block bootstrap (Sharpe CI)\n",
              f"Resample per-bar returns in blocks of B={BLOCK_BARS} bars "
              f"(1 day) with replacement, recompute Sharpe. "
              f"{N_BOOTSTRAP} bootstrap samples.\n"]

    base_m = engine_eval(research, factors, gates, cfg, factor_names)
    pnl = base_m["per_bar_pnl"]
    base_sharpe = base_m["sharpe"]
    n_bars = len(pnl)
    n_blocks = n_bars // BLOCK_BARS
    lines += [f"- base: Sharpe {base_sharpe:+.3f}, {n_bars} bars, "
              f"{n_blocks} blocks of {BLOCK_BARS}",
              f"- trades: {base_m['trades']}, WR {base_m['wr']}%\n"]

    # Trim to whole blocks
    pnl_trim = pnl[:n_blocks * BLOCK_BARS]
    blocks = pnl_trim.reshape(n_blocks, BLOCK_BARS)

    rng = np.random.default_rng(RNG_SEED)
    boot_sharpes = np.empty(N_BOOTSTRAP)
    for b in range(N_BOOTSTRAP):
        idx = rng.integers(0, n_blocks, size=n_blocks)
        sample = blocks[idx].ravel()
        std = sample.std()
        boot_sharpes[b] = float(sample.mean() / std * ANN_5M) if std else 0.0

    ci_lo = float(np.percentile(boot_sharpes, 2.5))
    ci_hi = float(np.percentile(boot_sharpes, 97.5))
    boot_mean = float(boot_sharpes.mean())
    boot_std = float(boot_sharpes.std())
    pct_positive = float((boot_sharpes > 0).mean() * 100)

    lines += [f"- bootstrap mean Sharpe: {boot_mean:+.3f}",
              f"- bootstrap std: {boot_std:.3f}",
              f"- 95% CI: [{ci_lo:+.3f}, {ci_hi:+.3f}]",
              f"- P(Sharpe > 0): {pct_positive:.1f}%",
              f"- base Sharpe {base_sharpe:+.3f} is "
              f"{'inside' if ci_lo <= base_sharpe <= ci_hi else 'outside'} the CI\n"]

    # Histogram (text)
    lines += ["### Bootstrap Sharpe distribution\n"]
    hist_bins = np.linspace(ci_lo - boot_std, ci_hi + boot_std, 21)
    hist_counts, _ = np.histogram(boot_sharpes, bins=hist_bins)
    max_count = max(hist_counts)
    for i in range(len(hist_counts)):
        bar = "#" * int(hist_counts[i] / max_count * 50) if max_count else ""
        lo_edge = hist_bins[i]
        lines.append(f"  [{lo_edge:+6.2f}] {bar} ({hist_counts[i]})")
    lines.append("")

    return {"base_sharpe": base_sharpe, "boot_mean": boot_mean,
            "boot_std": boot_std, "ci_lo": ci_lo, "ci_hi": ci_hi,
            "pct_positive": pct_positive}


# ======================================================================
# Main
# ======================================================================
def main():
    lines = ["# Monte Carlo robustness -- rank-aggregation scalping config (5m)\n"]

    full = pd.read_csv(DATA)
    h, dev_start = holdout_split(full.timestamp.to_numpy("int64"), 183)
    research = full.iloc[:h].reset_index(drop=True)
    n = len(research)

    lines += [f"- research: {research.datetime_utc.iloc[0]} -> {research.datetime_utc.iloc[-1]} ({n} bars)",
              f"- dev (excluded): {dev_start:%Y-%m-%d} -> {full.datetime_utc.iloc[-1]}",
              f"- bootstrap: {N_BOOTSTRAP} samples, block size {BLOCK_BARS} bars (1 day)",
              f"- RNG seed: {RNG_SEED}\n"]

    print("=== Selecting best aggregation config ===")
    sel = select_best_config(research, n)
    if sel is None:
        lines += ["## Error\n", "Config selection failed.\n"]
        REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
        print("FAILED: no config selected")
        return

    cfg = sel["config"]
    family = sel["all_reversal_factors"]
    factor_names = sel["factor_names"]
    lines += [f"- selected config: `{cfg.key}`",
              f"- factor family (top-{MAX_N_FACTORS}): `{', '.join(family)}`",
              f"- active factors (top-{cfg.n_factors}): `{', '.join(factor_names)}`",
              f"- train Sharpe: {sel['train_metrics']['sharpe']:+.3f}, "
              f"{sel['train_trades']} trades\n"]

    factors = build_factors(research, fast_window=FAST_WINDOW)
    gates = build_gates(research)

    print("=== Test 1: factor-family perturbation ===")
    t1 = test_factor_perturbation(lines, research, factors, gates, cfg, family)

    print("=== Test 2: parameter perturbation ===")
    t2 = test_param_perturbation(lines, research, factors, gates, cfg, factor_names)

    print("=== Test 3: block bootstrap ===")
    t3 = test_block_bootstrap(lines, research, factors, gates, cfg, factor_names)

    # Overall robustness verdict
    lines += ["## Overall robustness verdict\n"]
    lines += [f"- factor-family max |delta Sharpe|: {t1['max_abs_delta']:.3f}",
              f"- parameter max |delta Sharpe|: {t2['max_abs_delta']:.3f}",
              f"- bootstrap 95% CI: [{t3['ci_lo']:+.3f}, {t3['ci_hi']:+.3f}]",
              f"- P(Sharpe > 0): {t3['pct_positive']:.1f}%\n"]

    robust_count = 0
    if t1["max_abs_delta"] < 1.0:
        robust_count += 1
    if t2["max_abs_delta"] < 1.0:
        robust_count += 1
    if t3["ci_lo"] > 0:
        robust_count += 1

    if robust_count == 3:
        lines += ["**ROBUST**: the config passes all three robustness tests. "
                  "Factor-family and parameter perturbations cause < 1.0 Sharpe "
                  "change, and the bootstrap CI is entirely positive.\n"]
    elif robust_count >= 2:
        lines += [f"**MODERATELY ROBUST**: {robust_count}/3 tests pass. "
                  f"The config is moderately stable under perturbation.\n"]
    else:
        lines += [f"**FRAGILE**: {robust_count}/3 tests pass. "
                  f"The config is sensitive to perturbation and may overfit.\n"]

    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"\nsaved {REPORT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
