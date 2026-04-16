# Mode Selection Run 001

## Purpose

Record the first operator-facing cost-reduction run where `Synrail` deliberately does **not** enter a heavier contour after reading the current economics.

This document exists so the new selector is proven as behavior, not just as a helper.

## Scenario

- run id: `MODE_SELECTION_RUN_001`
- scenario class: `medium_risk_ambiguous_closure`
- task class: `medium_risk_reversible_artifact_fix`
- named ambiguity: `reversible artifact ambiguity`

## Artifacts

The canonical artifacts now live under:

- `fixtures/mode_selection_run_001/recommendation.json`
- `fixtures/mode_selection_run_001/receipt.json`

## What happened

### 1. Recommendation

The operator first ran the selector.

Observed result:

- `recommended_mode = LIGHTWEIGHT_BASELINE`
- `secondary_exception_mode = HYBRID_EXCEPTION`

That matters because this is exactly the kind of path that could easily drift into hybrid by habit.

### 2. Selection

The operator then followed the recommendation.

Observed result:

- `selected_mode = LIGHTWEIGHT_BASELINE`
- `followed_recommendation = true`
- `heavier_contour_entered = false`

### 3. Estimated avoided cost

The receipt now records that this choice likely avoided about:

- `9` operator minutes
- `1` extra intervention
- `11` extra closure-latency minutes

## Why this run matters

This is the first explicit proof that current economics are no longer only a retrospective reading.

They now participate in pre-contour steering.

That means `Synrail` can now help not only by:

- blocking
- degrading
- repairing

but also by:

- declining to enter its own heavier path when the current measured signal says that path is not paying off

## Current reading

The shortest honest reading is:

- the selector keeps the demoted-hybrid path on baseline by default
- the heavier contour is not entered automatically
- one named hybrid exception still remains available
- operator cost can now be reduced before the heavier runtime path even begins
