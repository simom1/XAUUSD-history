import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
import pandas as pd

from analysis.factor_screening import build_factors
from analysis.combo_screening import build_gates, holdout_split
from analysis.system_research import Component, run_engine, bar_metrics

# Catastrophic caps live in the stop-study ladder, not the shared 7-rule EXITS.
import analysis.system_research as sr
sr.EXITS = sr.EXITS + (("stop12", {"stop_loss_atr": 12.0}), ("stop16", {"stop_loss_atr": 16.0}))

# Catastrophic caps live in the stop-study ladder, not the shared 7-rule EXITS.
import analysis.system_research as sr
sr.EXITS = sr.EXITS + (("stop12", {"stop_loss_atr": 12.0}), ("stop16", {"stop_loss_atr": 16.0}))

ANN = float(np.sqrt(96 * 252))
full = pd.read_csv("data/xauusd_15m_indicators.csv.gz")
h, dev_start = holdout_split(full.timestamp.to_numpy("int64"), 183)
# 5m frozen spec rescaled to 15m: W6048->W2016 (~21d), H84->H28 (~7h),
# same factors / thresholds / sessions / exit philosophy.
L = Component("long", "plus_di_14", "high", 2016, 2.0, 28, "none", "new_york")
S = Component("short", "aroon_up_25", "low", 2016, 1.5, 28, "none", "london")
for name, sl in (("research", full.iloc[:h].reset_index(drop=True)),
                 ("dev(diagnostic)", full.iloc[h:].reset_index(drop=True))):
    f = build_factors(sl, fast_window=32)
    g = build_gates(sl)
    for ex in ("none", "stop12", "stop16"):
        r, t, m, cf = run_engine(sl, L, S, ex, f, g, bar_seconds=900)
        trades = r.trades
        wr = (trades.net_pnl > 0).mean() * 100 if len(trades) else 0.0
        print(f"{name:18s} exit={ex:6s} pnl={m['pnl']:+9.2f} sharpe={m['sharpe']:+.3f} "
              f"maxdd={m['maxdd']:+9.2f} trades={len(trades)} wr={wr:.1f}% conflicts={cf}")
