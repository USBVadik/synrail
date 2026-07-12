# False-Green Benchmark Starter

This is a curated local starter scaffold for public proof, not an external empirical benchmark.

The goal is to make the false-green problem concrete before external alpha reports accumulate.

## What it contains

- `cases.csv` — 17 starter cases across common false-green and bounded-acceptance shapes
- a compact table format for:
  - case family
  - agent claim
  - reality
  - Synrail result
  - manual effort
  - overhead notes

## How to use it

Use this starter pack in the cheapest honest order:

1. read the cases as a wedge explainer, not as an empirical leaderboard
2. copy or adapt a few cases into your own local agent workflow
3. note where Synrail blocks, accepts, or asks for bounded repair
4. only treat outside repeated runs as external signal after they are logged separately

## Case families included now

- tests claimed but not run (caught only via proof shape; a substituted valid read-only proof is a known accepted-gap until verification profiles land)
- wrong file changed
- weak proof / narrative-only proof
- diff/claim mismatch
- incomplete task closure
- stale proof / freshness mismatch
- bounded happy-path acceptance
- handoff or repair still unclear
- over-scoped cleanup or batch drift
- misleading output or partial catch contours

## How to read the result labels

- `blocked` means the claimed success did not earn acceptance on that contour
- `accepted` means the narrow happy path reached trustworthy closure
- `repair-needed` means the contour exposed useful signal, but the current public-alpha lane still needs clearer handling or explanation

These starter labels are for local discussion and tester preparation, not measured external rates.

## Why this exists

A public repo is not enough by itself.
This starter pack gives a simple evidence story for why false-green matters:

- tests claimed but not run
- wrong files changed
- weak proof
- diff/claim mismatch
- incomplete task closure

## Next step

For the bounded external-tester handoff around these cases, use the [first tester protocol](../../docs/review/FIRST_TESTER_PROTOCOL_001.md).

If a run exposes a concrete miss or confusing contour, report it through the GitHub issue templates:

- `Alpha feedback`
- `False-green case`
- `Confusing output`

## Important boundary

These are curated local examples.
They are useful for launch, prioritization, tester preparation, and discussion.
They are not empirical external measurements.
They should not be summarized as measured external false-green rates.
