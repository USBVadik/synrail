# Mode Selection Run 004

## Purpose

Record the first operator-facing strong-path selection run where the selector explicitly says to enter the prepared governed contour.

This document exists so the governed-path cost win now affects pre-contour operator steering, not only post-hoc reading.

## Scenario

- run id: `MODE_SELECTION_RUN_004`
- scenario class: `expensive_wrong_closure`
- task class: `bounded_router_trigger_fix`

## Artifacts

The canonical artifacts now live under:

- `fixtures/mode_selection_run_004/recommendation.json`
- `fixtures/mode_selection_run_004/receipt.json`

## What happened

### 1. Recommendation

The selector still recommended:

- `FULL_GOVERNED_PATH`

But it now also recorded:

- `governed_preparation_recommended = true`

Observed next safe step:

- `run the full governed path with preparation`

### 2. Selection

The operator followed the recommendation and committed to the prepared governed contour.

Observed result:

- `selected_mode = FULL_GOVERNED_PATH`
- `selected_with_preparation = true`
- `followed_recommendation = true`
- `heavier_contour_entered = true`

## Why this run matters

This is the first proof that the selection layer now reads two different truths at once:

- the strong wedge still deserves the governed contour
- the governed contour itself should now start in its prepared variant

That matters because the selector is no longer only answering:

- baseline or governed?

It can now also answer:

- which governed variant should we enter first?

## Current reading

The shortest honest reading is:

- the strong path no longer only enters the governed contour
- it now enters the prepared governed contour by default when the bounded cost signal justifies it
