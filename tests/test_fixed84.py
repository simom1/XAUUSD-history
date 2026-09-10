import unittest
import numpy as np
import pandas as pd
from strategies.xauusd_fixed84 import simulate, signals


class Fixed84Tests(unittest.TestCase):
    def frame(self, n=110, start='2024-01-02 07:00'):
        ts = pd.date_range(start, periods=n, freq='5min', tz='UTC').as_unit('ns').asi8 // 10**9
        return pd.DataFrame(dict(timestamp=ts, open=np.arange(n)+2000., close=np.arange(n)+2000.5))

    def test_expiry_and_no_renewal(self):
        df = self.frame()
        ld, sd = np.zeros(110,bool), np.zeros(110,bool)
        ld[[0,10,50]] = True
        eq,t = simulate(df,ld,sd)
        self.assertEqual(len(t),1)
        self.assertEqual(t.iloc[0].bars_held,84)
        self.assertAlmostEqual(eq[-1]-10000,83.84)

    def test_resume_original_expiry(self):
        a = self.frame(12,'2024-01-02 20:00')
        b = self.frame(100,'2024-01-03 00:00')
        df = pd.concat([a,b],ignore_index=True)
        ld,sd = np.zeros(112,bool),np.zeros(112,bool)
        ld[0]=True
        _,t=simulate(df,ld,sd)
        self.assertEqual(len(t),2)
        self.assertEqual(t.iloc[0].exit_reason,'session')
        self.assertEqual(t.iloc[1].entry_time,int(b.timestamp.iloc[1]))
        self.assertEqual(t.iloc[1].signal_expiry_i,84)

    def test_conflict_blocks_remaining_day(self):
        df=self.frame()
        ld,sd=np.zeros(110,bool),np.zeros(110,bool)
        ld[[0,2,3]]=True
        sd[2]=True
        _,t=simulate(df,ld,sd)
        self.assertEqual(len(t),1)
        self.assertEqual(t.iloc[0].bars_held,2)

    def test_gap_closes_at_returning_close(self):
        df=self.frame().drop(index=[2,3]).reset_index(drop=True)
        ld,sd=np.zeros(len(df),bool),np.zeros(len(df),bool)
        ld[0]=True
        _,t=simulate(df,ld,sd)
        self.assertEqual(t.iloc[0].exit_reason,'data_gap')
        self.assertEqual(t.iloc[0].exit_time,int(df.timestamp.iloc[2]+300))

    def test_full_window_warmup(self):
        df=self.frame(6100)
        df['plus_di_14']=np.arange(len(df),dtype=float)
        df['aroon_up_25']=np.arange(len(df),dtype=float)
        ld,sd=signals(df)
        self.assertFalse(ld[:6048].any())
        self.assertFalse(sd[:6048].any())

    def test_reversal_and_costs(self):
        df=self.frame()
        ld,sd=np.zeros(110,bool),np.zeros(110,bool)
        ld[0],sd[10]=True,True
        eq,t=simulate(df,ld,sd)
        self.assertEqual(t.side.tolist(),[1,-1])
        self.assertEqual(t.iloc[0].exit_time,t.iloc[1].entry_time)
        self.assertAlmostEqual(t.costs.sum(),.32)
        self.assertAlmostEqual(eq[-1]-10000,t.net_pnl.sum())

    def test_friday_cutoff(self):
        df=self.frame(24,'2024-01-05 20:00')
        ld,sd=np.zeros(24,bool),np.zeros(24,bool)
        ld[0]=True
        _,t=simulate(df,ld,sd)
        self.assertEqual(pd.to_datetime(t.iloc[0].exit_time,unit='s',utc=True).strftime('%H:%M'),'20:45')

    def test_prefix_equity(self):
        df=self.frame()
        ld,sd=np.zeros(110,bool),np.zeros(110,bool)
        ld[0],sd[50]=True,True
        full,_=simulate(df,ld,sd)
        prefix,_=simulate(df.iloc[:70],ld[:70],sd[:70])
        np.testing.assert_array_equal(full[:69],prefix[:69])


if __name__=='__main__':
    unittest.main()
