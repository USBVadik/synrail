# Repeatable Everyday Benchmark 001

## Purpose

Define the first bounded everyday benchmark class for the cheapened local contour.

This slice exists so the repo can pressure-test current economics on trivial and additive work
without inventing a broad benchmark platform or faking live external wins.

## Primary artifacts

The initial pack lives at:

- `fixtures/repeatable_everyday_benchmark_pack_001.json`
- `fixtures/cost_of_control_everyday_001.json`
- `tests/test_everyday_benchmark_pack.py`

## What this pack is

The pack is intentionally small and repeatable:

- `5` local-only trivial or additive tasks
- same scenario class: `repeatable_everyday_local`
- same comparison shape: one baseline path vs one cheapened `Synrail` path
- one machine-readable economics reading

This is not an external alpha benchmark.
It is an internal executable benchmark class.

## Current measured reading

The current aggregate reading is:

- `1` scenario: `SYNRAIL_BETTER`
- `4` scenarios: `BASELINE_GOOD_ENOUGH`
- `0` scenarios: `UNCLEAR`

The shortest honest reading is:

- the cheapened contour is materially lighter than before
- checks per accepted closure are now tracked machine-readably without adding a new runtime input surface
- the default non-green path now keeps `repair-step` off the everyday default contour unless a standalone bounded prompt is actually needed
- one repeatable low-drag winner now exists
- the remaining everyday paths now read as baseline-sufficient rather than unresolved
- but the everyday class is still not won overall

## Current economics summary

Across the current five-scenario pack, `Synrail` currently adds on average:

- `1` operator minute
- `0` checks per accepted closure
- `1` mandatory mental step
- `1` trust-bearing artifact
- `0` required visible surfaces
- `0` skippable visible surfaces
- `1` operator-visible action
- `0` got-lost moments
- `2` fixed control-mass units
- `1` behavioral control-tax unit
- `3` total control-burden units

It currently gains on average:

- `29` points of artifact completeness

That is a useful internal signal, but not yet a broad product win.

## Why this matters

This pack turns the next roadmap question into something falsifiable:

- can the cheapened path become genuinely everyday-cheap
- without hidden prose babysitting
- and without pretending a near-baseline contour is already a win

## Current decision rule

The right next moves should now improve one of these:

1. reduce fixed control mass or behavioral control tax on the `BASELINE_GOOD_ENOUGH` everyday paths
2. turn one baseline-sufficient path into a repeatable near-zero-drag everyday contour
3. keep runtime-backed trust carrying acceptance without reintroducing optional prose by habit

If a change does not improve one of those, it is probably not the best next step for this benchmark class.
