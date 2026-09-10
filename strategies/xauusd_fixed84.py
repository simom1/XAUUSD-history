"""Pinned user specification; close decisions, next available open fills.

Daily flatten is filled at the cutoff close. Unexpected missing bars cannot
be anticipated: an existing position is closed at the first returning close.
Signal age counts observed bars, including bars while exposure is flat.
"""
import numpy as np
import pandas as pd


def signals(df):
    z = {}
    for name in ('plus_di_14', 'aroon_up_25'):
        s = df[name]
        r = s.rolling(6048, min_periods=6048)
        z[name] = (s - r.mean()) / r.std(ddof=1).replace(0, np.nan)
        z[name].iloc[:6048] = np.nan
    minute = ((df.timestamp.to_numpy() + 300) % 86400) // 60
    return ((z['plus_di_14'].to_numpy() >= 2) & (minute >= 780) & (minute < 1260),
            (z['aroon_up_25'].to_numpy() <= -1.5) & (minute >= 420) & (minute < 1020))


def simulate(df, ld=None, sd=None):
    if ld is None:
        ld, sd = signals(df)
    ts = df.timestamp.to_numpy(dtype=np.int64)
    opens, closes = df.open.to_numpy(), df.close.to_numpy()
    dates = pd.to_datetime(ts + 300, unit='s', utc=True)
    side, expiry, pos, pending = 0, -1, 0, 0
    blocked_day, cash, current = None, 10000., None
    trades, equity = [], []

    def close(i, price, reason, at_close=False):
        nonlocal cash, pos, current
        gross = pos * (price - current['entry_px'])
        cash += gross - .08
        trades.append(dict(current, exit_time=int(ts[i] + (300 if at_close else 0)),
                           exit_px=float(price), gross_pnl=float(gross), costs=.16,
                           net_pnl=float(gross - .16), exit_reason=reason,
                           bars_held=i-current['entry_i']))
        pos, current = 0, None

    for i in range(len(df)):
        minute = int((ts[i] % 86400) // 60)
        day = dates[i].date()
        gap = i > 0 and ts[i] - ts[i-1] > 300
        # Discard stale entry orders across a gap; already-held exposure is
        # liquidated at the returning close, as explicitly requested.
        if not gap:
            if pending != pos:
                if pos:
                    close(i, opens[i], 'signal')
                if pending and minute < 1245 and dates[i].weekday() < 5:
                    pos = pending
                    cash -= .08
                    current = dict(entry_i=i, entry_time=int(ts[i]), side=pos, oz=1.,
                                   entry_px=float(opens[i]), signal_expiry_i=expiry)
        cutoff = 1245 if dates[i].weekday() == 4 else 1255
        cm = int(((ts[i]+300) % 86400)//60)
        if pos and (gap or cm >= cutoff or dates[i].weekday() >= 5):
            close(i, closes[i], 'data_gap' if gap else 'session', True)
        if side and i >= expiry:
            side = 0
        if ld[i] and sd[i]:
            side, blocked_day = 0, day
        elif day != blocked_day and cm < 1245 and dates[i].weekday() < 5:
            if ld[i] and side != 1:
                side, expiry = 1, i + 84
            elif sd[i] and side != -1:
                side, expiry = -1, i + 84
        pending = side
        if cm >= cutoff or dates[i].weekday() >= 5:
            pending = 0
        elif cm >= 1245:
            # The entry ban does not close an existing position early.
            pending = pos if side == pos else 0
        equity.append(cash + (pos * (closes[i]-current['entry_px']) if pos else 0))
    if pos:
        close(len(df)-1, closes[-1], 'end_of_data', True)
        equity[-1] = cash
    return np.asarray(equity), pd.DataFrame(trades)
