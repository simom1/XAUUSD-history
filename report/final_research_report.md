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

## Next independent validation

Accumulate at least six continuous months of new data after 2026-09-09.  Then
freeze that new segment, lock the single-account specification before running
it, and evaluate it exactly once with `BacktestEngine`.  Any subsequent rule
change requires a new, later validation segment.

Pre-revision results are preserved under `archive/pre-validation-revision/`
for audit history and are not comparable with this revision.
