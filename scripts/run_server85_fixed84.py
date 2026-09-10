"""Reproduce pinned legacy rules and compare with the literal fixed-84 spec."""
import hashlib
import json
import platform
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from analysis.system_research import Component, run_engine
from strategies.xauusd_fixed84 import simulate


def main():
    path = ROOT / 'data/xauusd_5m_indicators.csv.gz'
    df = pd.read_csv(path)
    out = ROOT / 'report/server85_fixed84'
    out.mkdir(parents=True, exist_ok=True)
    long = Component('long', 'plus_di_14', 'high', 6048, 2., 84, 'none', 'new_york')
    short = Component('short', 'aroon_up_25', 'high', 6048, 1.5, 84, 'none', 'london')
    rows = []
    for period, frame in [('research', df[df.timestamp < 1773100800]), ('full', df)]:
        frame = frame.reset_index(drop=True)
        for version in ('legacy', 'fixed84'):
            if version == 'legacy':
                r, _, _, _ = run_engine(frame, long, short)
                eq, t = r.equity, r.trades
            else:
                eq, t = simulate(frame)
            assert np.isclose(eq[-1]-10000, t.net_pnl.sum(), atol=1e-7)
            assert (t.oz == 1).all() and np.allclose(t.costs, .16)
            curve = np.r_[10000., eq]
            row = dict(period=period, version=version, bars=len(frame), trades=len(t),
                       pnl=round(float(eq[-1]-10000), 2),
                       return_pct=round(float((eq[-1]/10000-1)*100), 3),
                       maxdd=round(float((curve-np.maximum.accumulate(curve)).min()), 2),
                       win_pct=round(float((t.net_pnl>0).mean()*100), 2),
                       profit_factor=round(float(t.loc[t.net_pnl>0,'net_pnl'].sum() /
                                                 -t.loc[t.net_pnl<0,'net_pnl'].sum()), 3),
                       avg_pnl=round(float(t.net_pnl.mean()), 3),
                       worst=round(float(t.net_pnl.min()), 2), costs=round(float(t.costs.sum()),2),
                       exit_reasons=t.exit_reason.value_counts().to_dict())
            rows.append(row)
            t.to_csv(out / f'{period}_{version}_trades.csv', index=False)
            pd.DataFrame({'timestamp':frame.timestamp,'equity':eq}).to_csv(
                out / f'{period}_{version}_equity.csv', index=False)
    payload = dict(host=platform.node(), python=sys.version, data_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                   start=str(pd.to_datetime(df.timestamp.iloc[0],unit='s',utc=True)),
                   end=str(pd.to_datetime(df.timestamp.iloc[-1],unit='s',utc=True)), results=rows)
    (out/'summary.json').write_text(json.dumps(payload, indent=2), encoding='utf-8')
    print(json.dumps(payload, indent=2))


if __name__ == '__main__':
    main()
