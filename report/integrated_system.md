# Integrated Long-Short System — single-account revision

- data: 2023-09-13 -> 2026-09-09 (211,242 5m bars)
- research period: 2023-09-13 -> 2026-03-09
- consumed development set: 2026-03-10 -> 2026-09-09; not a validation result.
- execution: one $10,000 account, max 1 oz (0.01 lot), next-open fills, $0.16/oz round-trip cost.
- exits: entry ATR(14) fixed stop 2.5×; all protective exits fill at the adverse bar extreme.
- metric: annualized 5-minute USD PnL Sharpe (sqrt(288×252)); margin, financing and liquidation are not modeled.

## Attribution specification (not a candidate)

- long: `single|plus_di_14|long|W6048|T1.5|H120`, gates `trend_up,adx_strong`
- short: `single|close_vs_ema200|short|W6048|T1.5|H120`, gates `trend_down,adx_strong`
- opposing signals reverse at the next open; simultaneous signals flatten the account.
- simultaneous signal conflicts observed: 0

## Results

| segment | PnL | 5m Sharpe | max drawdown |
|---|---:|---:|---:|
| research | $-1,437 | -1.41 | $-1,488 |
| consumed development set | $-52 | -0.15 | $-608 |
| full history | $-1,489 | -1.05 | -16.49% |

## Internal research folds

| fold | PnL | 5m Sharpe | max drawdown |
|---|---:|---:|---:|
| f1 | $-138 | -1.39 | $-205 |
| f2 | $-177 | -1.43 | $-291 |
| f3 | $-240 | -1.22 | $-373 |
| f4 | $-881 | -1.98 | $-1,039 |

## Status

The nested walk-forward research did not lock a candidate, so this legacy specification is presented only for attribution. Do not tune it from the consumed development set. After at least six new continuous months are available, repeat candidate selection on the research protocol before freezing any final judgment set.
