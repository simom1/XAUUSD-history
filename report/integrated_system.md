# Integrated Long-Short System — single-account revision

- data: 2023-09-13 -> 2026-09-09 (211,242 5m bars)
- research period: 2023-09-13 -> 2026-03-09
- consumed development set: 2026-03-10 -> 2026-09-09; not a validation result.
- execution: one $100,000 account, max 100 oz, next-open fills, $0.16/oz round-trip cost.
- exits: entry ATR(14) fixed stop 2.5×; all protective exits fill at the adverse bar extreme.
- metric: annualized 5-minute USD PnL Sharpe (sqrt(288×252)); margin, financing and liquidation are not modeled.

## Locked development specification

- long: `single|plus_di_14|long|W6048|T1.5|H120`, gates `trend_up,adx_strong`
- short: `single|close_vs_ema200|short|W6048|T1.5|H120`, gates `trend_down,adx_strong`
- opposing signals reverse at the next open; simultaneous signals flatten the account.
- simultaneous signal conflicts observed: 0

## Results

| segment | PnL | 5m Sharpe | max drawdown |
|---|---:|---:|---:|
| research | $-143,747 | -1.41 | $-148,802 |
| consumed development set | $-5,184 | -0.15 | $-60,771 |
| full history | $-148,931 | -1.05 | -160.12% |

## Internal research folds

| fold | PnL | 5m Sharpe | max drawdown |
|---|---:|---:|---:|
| f1 | $-13,841 | -1.39 | $-20,496 |
| f2 | $-17,740 | -1.43 | $-29,102 |
| f3 | $-24,023 | -1.22 | $-37,294 |
| f4 | $-88,143 | -1.98 | $-103,880 |

## Status

This is a development candidate only. Do not tune from the consumed development set. After at least six new continuous months of data are available, freeze that new segment and run the pre-locked single-account specification once through the event engine.
