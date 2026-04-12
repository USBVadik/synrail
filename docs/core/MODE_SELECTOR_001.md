# Mode Selector 001

## Purpose

Define the first cost-aware mode-selection slice for `Synrail`.

This document exists so cost reduction on non-winning paths can happen before the operator enters a heavier contour.

## Artifacts

The selector now lives at:

- `tools/reference/synrail_mode_selector_v0.py`
- `schemas/mode_recommendation_v0.schema.json`

The first three machine-readable recommendation artifacts now live at:

- `fixtures/mode_recommendation_strong_001.json`
- `fixtures/mode_recommendation_weak_001.json`
- `fixtures/mode_recommendation_hybrid_001.json`

The first operator-facing selection receipt now lives at:

- `fixtures/mode_selection_run_001/receipt.json`
- `fixtures/mode_selection_run_002/receipt.json`
- `fixtures/mode_selection_run_003/receipt.json`
- `fixtures/mode_selection_run_004/receipt.json`

## What it does

The selector takes:

- current aggregate cost record
- current hybrid status
- scenario-class inputs
- simple risk signals

and returns:

- recommended mode
- optional hybrid exception mode
- class-level measured evidence summary
- one short reason
- one narrow next safe step
- one separate selection receipt when the operator follows or overrides the recommendation

## Current behavior

### 1. Strong path

Recommendation:

- `FULL_GOVERNED_PATH`

Why:

- wrong closure is still expensive here
- measured class evidence still says `SYNRAIL_BETTER`

Observed selection receipt:

- `selected_mode = FULL_GOVERNED_PATH`
- `heavier_contour_entered = true`

Observed prepared-strong receipt:

- `governed_preparation_recommended = true`
- `selected_with_preparation = true`
- next safe step = `run the full governed path with preparation`

### 2. Weak path

Recommendation:

- `LIGHTWEIGHT_BASELINE`

Why:

- measured class evidence already says `BASELINE_GOOD_ENOUGH`
- current selector reading says baseline likely avoids about:
  - `20` added operator minutes
  - `3` extra interventions
  - `22` extra closure-latency minutes

### 3. Demoted hybrid path

Recommendation:

- `LIGHTWEIGHT_BASELINE`
- secondary exception mode = `HYBRID_EXCEPTION`

Why:

- hybrid class is now demoted
- class-level evidence contains `BASELINE_GOOD_ENOUGH`
- baseline likely avoids about:
  - `9` added operator minutes
  - `1` extra intervention
  - `11` extra closure-latency minutes

That means the selector now helps reduce cost before the operator drifts into a heavier lane by habit.

## Current reading

The shortest honest reading is:

- `Synrail` now has one small executable policy surface that can steer obvious non-winning paths back to baseline
- it now also has operator-facing receipts that prove:
  - a heavier contour was deliberately skipped on demoted-hybrid and weak paths
  - a heavier contour was deliberately entered on the strong path
  - a prepared governed contour can now be deliberately entered on the strong path when bounded governed-path cost evidence supports it
- the selector does not replace the kernel
- it reduces unnecessary kernel use where the measured signal already says the extra control is not paying off
- it also records when the measured signal still says the heavier kernel path is worth entering
- it now also nudges the strong path toward the cheaper prepared governed variant when that bounded signal exists
- it can now also hand that prepared strong-path decision directly into the runtime contour instead of stopping at a receipt

The first canonical proof of that handoff now lives at:

- `fixtures/executable_loop_selected_prepared_run_001/run.json`

The governed runtime path now also blocks at `selection` if a receipt says:

- `LIGHTWEIGHT_BASELINE`
- or `HYBRID_EXCEPTION`

instead of silently entering the heavier contour anyway.

The first canonical proof of that selection-side block now lives at:

- `fixtures/executable_loop_selection_blocked_run_001/run.json`
