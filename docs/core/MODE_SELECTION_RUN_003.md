# Mode Selection Run 003

## Purpose

Record the first operator-facing strong-path selection run where the selector explicitly says to enter the governed contour.

This document exists so the selection layer is not only a cost-avoidance surface for non-winning paths.

## Scenario

- run id: `MODE_SELECTION_RUN_003`
- scenario class: `expensive_wrong_closure`
- task class: `bounded_router_trigger_fix`

## Artifacts

The canonical artifacts now live under:

- `fixtures/mode_selection_run_003/recommendation.json`
- `fixtures/mode_selection_run_003/receipt.json`

## What happened

### 1. Recommendation

The selector recommended:

- `FULL_GOVERNED_PATH`

That is the expected strong-path reading because measured class evidence still says `SYNRAIL_BETTER` and the wrong-closure risk remains expensive.

### 2. Selection

The operator followed the recommendation.

Observed result:

- `selected_mode = FULL_GOVERNED_PATH`
- `followed_recommendation = true`
- `heavier_contour_entered = true`

### 3. Estimated avoided cost

This receipt correctly records no avoided heavier-path cost:

- `0` operator minutes
- `0` extra interventions
- `0` extra closure-latency minutes

That is the honest result here because the stronger contour is the intended contour.

## Why this run matters

This run completes the first selection triad:

- strong path enters the governed contour
- weak path stays on baseline
- demoted-hybrid path stays on baseline by default

That matters because the selector is now proven as:

- a cost-reduction surface on non-winning paths
- and a cost-justification surface on the real wedge

## Current reading

The shortest honest reading is:

- the selector now has a complete strong/weak/demoted-hybrid triad
- `Synrail` does not only skip its heavier contour
- it also records when entering that contour is the measured right call
