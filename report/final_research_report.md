# XAUUSD research status — validation revision

## Current conclusion

No strategy is approved for deployment.  The former 2026-03-10 to 2026-09-09
"holdout" has been consumed by the original factor-selection workflow and is
now a development diagnostic set only.  It cannot provide an independent
final verdict.

The single-account system is reported in `integrated_system.md`.  It executes
one signed position with at most 100 oz, reverses at the next open, charges
$0.16/oz round-trip cost, and uses conservative bar-extreme fills for
protective exits.  Its results supersede the former sum-of-independent-legs
presentation.

## Methodology now in force

- All headline Sharpes use 5-minute USD PnL annualized by `sqrt(288 * 252)`.
- The engine recomputes final-bar equity after forced liquidation and logs
  costs that reconcile to account equity.
- ATR fixed stops, trailing stops, and profit targets use the ATR known on
  entry; an OHLC bar with a protective trigger exits at its adverse extreme.
- A strategy must pass recomputed-prefix causality validation.  Replaying a
  precomputed target sequence is insufficient.
- 2026-03-10 to 2026-09-09 may be inspected for diagnosis but may not select
  parameters or support a pass/fail claim.

## Exit-design findings (2026-09-10)

- Nested walk-forward on the research slice
  (`single_account_walkforward.md`): no static candidate. Each of the 4 folds
  picked a different long/short component pair; the hold-expiry exit (`none`)
  won 3 of 4 folds, consistent with the attribution that fixed ATR stops
  destroy the edge.
- Catastrophic-stop ladder (`catastrophic_stop_study.md`, top-3x3 pairs,
  research slice only): 2.5-8x ATR stops trigger in 11-40% of trades -- they
  are regular exits, not insurance -- and cut the no-exit edge by 19-91%.
  12-16x ATR triggers only 1.6-3.4% of trades and retains 93-96% of the PnL:
  a genuine disaster cap at a modest, measured cost. Without any stop the
  worst single trade is -$64 to -$121 at 1 oz, already bounded by the
  hold-based expiry and the daily session flat.
- Volatility-targeted sizing (`vol_target_sizing.md`, legacy attribution
  signals, pre-specified rule, research slice only): freezing
  oz = clip(median(ATR_14, 2016)/ATR_14, 0.25, 2.0) at each episode's
  entry/reversal bar keeps the trade stream identical to fixed 1 oz
  (1,240 trades) but lifts research Sharpe 0.83 -> 1.14 and cuts maxDD
  -$902 -> -$547 at 0.87 oz average exposure. Robust across the reported
  floor/cap grid; nothing is selected from it. This is a sizing layer for
  the final-judgment spec, not a new signal candidate.

## Cross-timeframe check (2026-09-10)

- The same study was run at 15 minutes (`final_research_report_15m.md`):
  independent nested walk-forward mining found no candidate (4 folds, 4
  different picks), and the locked 5-minute specification transferred to
  15-minute bars with a positive but weaker edge (research Sharpe +1.20,
  350 trades, win rate 55.7%, zero same-bar conflicts) and failed the
  diagnostic segment (Sharpe -0.89) exactly as at 5 minutes. The failure
  is regime dependent, not timeframe dependent. This strengthens, and does
  not change, the conclusion above. Two earlier transfer runs are
  superseded (inverted short-leg direction, then a 5m annualization
  constant that inflated Sharpe by sqrt(3)); see the audit note in the 15m
  report.

## Next independent validation

Accumulate at least six continuous months of new data after 2026-09-09.  Then
freeze that new segment, lock the single-account specification before running
it, and evaluate it exactly once with `BacktestEngine`.  Any subsequent rule
change requires a new, later validation segment.

Pre-revision results are preserved under `archive/pre-validation-revision/`
for audit history and are not comparable with this revision.
