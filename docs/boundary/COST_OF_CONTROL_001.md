# Cost Of Control 001

## Purpose

State the first machine-readable reading of what `Synrail` currently costs relative to the simpler baseline across the economics-aware comparison set.

This document exists so the repo can talk not only about:

- truth discipline
- closure safety
- repaired re-entry

but also about:

- what that extra control currently costs
- where that cost looks justified
- where it does not yet look justified

## Primary artifact

The first aggregate cost-of-control artifact now lives at:

- `fixtures/cost_of_control_001.json`

It is built from these four economics-aware comparison records:

- `fixtures/executable_loop_run_001/comparison_economics.json`
- `fixtures/executable_loop_run_002/comparison_economics.json`
- `fixtures/executable_loop_run_003/comparison_economics.json`
- `fixtures/executable_loop_compound_run_001/comparison_economics.json`

## Current measured reading

Across the current four-scenario set, `Synrail` currently adds on average:

- `21` operator minutes
- `2` extra interventions
- `1` extra repair cycle
- `1` extra invalidation
- `26` extra minutes of closure latency

Across that same set, `Synrail` currently gains on average:

- `2` units of false-green exposure reduction
- `45` points of artifact completeness

This is the shortest honest current cost reading in the repo.

## Verdict distribution

The current verdict mix is:

- `2` scenarios: `SYNRAIL_BETTER`
- `1` scenario: `BASELINE_GOOD_ENOUGH`
- `1` scenario: `UNCLEAR`

That matters because the cost artifact is not telling a universal success story.

It is telling a bounded economic story.

## Current buckets

The current buckets are:

- justified cost paths:
  - `SCENARIO_STRONG_001`
  - `SCENARIO_COMPOUND_001`
- baseline-sufficient path:
  - `SCENARIO_WEAK_001`
- under-proven path:
  - `SCENARIO_HYBRID_001`

That is the cleanest current product reading of where `Synrail` seems worth paying for.

## Current hotspots

The current highest-cost path is:

- `SCENARIO_COMPOUND_001`

It is also currently the path with the highest observed:

- false-green exposure reduction
- artifact completeness gain

That matters because the most expensive path is not automatically the weakest path.

The current clearest overhead-heavy path is:

- `SCENARIO_WEAK_001`

That matters because it shows the kernel can be both:

- justified
- and too expensive

depending on the scenario class.

## Current strategic reading

The current shortest strategic reading is:

- `Synrail` already earns its cost on the strong and compound proof-sensitive paths
- the weak low-risk path still looks too expensive for the gain
- the hybrid path is still not measured strongly enough to deserve active middle-mode status, so it should remain secondary for now

This is exactly the kind of reading the repo needed.

It turns cost from a vague worry into one bounded machine-readable surface.

## What this changes

The next product pressure should now go first to:

1. reducing unnecessary control cost on non-winning paths
2. proving the hybrid mode further or continuing to keep it secondary
3. keeping compound-path wins honest without pretending the whole system is cheap

It should not go first to:

- more explanation layers
- more policy framing for hybrid without new evidence
- broader runtime surface just because the current kernel already looks serious

## Decision rule

The next strongest work should improve one of these:

1. reduce cost on paths that are not current winners
2. improve the economics reading of hybrid
3. preserve strong or compound truth gains while reducing operator tax

If a change does not improve one of those, it is probably not the best next move for the current stage.
