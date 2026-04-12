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

## Current behavior

### 1. Strong path

Recommendation:

- `FULL_GOVERNED_PATH`

Why:

- wrong closure is still expensive here
- measured class evidence still says `SYNRAIL_BETTER`

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
- the selector does not replace the kernel
- it reduces unnecessary kernel use where the measured signal already says the extra control is not paying off
