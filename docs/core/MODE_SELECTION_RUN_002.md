# Mode Selection Run 002

## Purpose

Record the second operator-facing cost-reduction run, this time on the weak low-risk path.

This document exists so cost-aware pre-contour steering is not left as a single demoted-hybrid example.

## Scenario

- run id: `MODE_SELECTION_RUN_002`
- scenario class: `low_risk_honesty_restoration`
- task class: `honesty_restoration_guard`

## Artifacts

The canonical artifacts now live under:

- `fixtures/mode_selection_run_002/recommendation.json`
- `fixtures/mode_selection_run_002/receipt.json`

## What happened

### 1. Recommendation

The selector recommended:

- `LIGHTWEIGHT_BASELINE`

That is exactly what current economics should imply on this path.

### 2. Selection

The operator followed the recommendation.

Observed result:

- `selected_mode = LIGHTWEIGHT_BASELINE`
- `followed_recommendation = true`
- `heavier_contour_entered = false`

### 3. Estimated avoided cost

The receipt now records that this choice likely avoided about:

- `20` operator minutes
- `3` extra interventions
- `22` extra closure-latency minutes

## Why this run matters

This run shows the selector is not only useful around the demoted hybrid lane.

It also keeps clearly non-winning low-risk work out of the heavier governed contour.

## Current reading

The shortest honest reading is:

- the weak path now also has a selection receipt
- the operator follows the cheaper honest path before heavy control starts
- `Synrail` can now avoid some of its own unnecessary weight on both:
  - demoted-hybrid work
  - clearly weak low-risk work
