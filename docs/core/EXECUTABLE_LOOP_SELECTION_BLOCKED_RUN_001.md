# Executable Loop Selection Blocked Run 001

## Purpose

Record the first canonical contour where the governed runtime path blocks at `selection` because the operator already chose a lighter mode.

This document exists so the repo proves that the selection layer is now enforced, not only advisory.

## Scenario

- run id: `EXECUTABLE_LOOP_SELECTION_BLOCKED_RUN_001`
- task class: `honesty_restoration_guard`
- contour shape:
  - weak-path recommendation says `LIGHTWEIGHT_BASELINE`
  - selection receipt follows that recommendation
  - governed orchestration is still invoked
  - runtime blocks immediately at `selection`

## Artifacts

The selection-blocked artifacts now live under:

- `fixtures/executable_loop_selection_blocked_run_001/`

Included artifacts:

- `recommendation.json`
- `selection_receipt.json`
- `state.json`
- `report.json`
- `orchestration.json`
- `run.json`
- `final_result.json`

## What was executed

The run used the current executable stack:

1. `synrail_cli_v0.py select-mode`
2. `synrail_cli_v0.py init`
3. `synrail_cli_v0.py orchestrate --mode-selection-receipt ...`

The important point is that the operator still called the governed orchestration entrypoint after selecting:

- `LIGHTWEIGHT_BASELINE`

The runtime did not ignore that mismatch.

## Observed path

Observed result:

- `result = BLOCKED`
- `stopping_stage = selection`
- `reason = MODE_SELECTION_NOT_GOVERNED`
- `selected_mode = LIGHTWEIGHT_BASELINE`
- `next_safe_step = follow the selected lighter mode instead of entering governed orchestration`

No doctor, bundle, or closure execution was needed before the block.

## Why this run matters

This is the companion proof to the selected-prepared governed run.

Together they show:

- a strong prepared receipt can hand off into governed execution
- a lighter receipt now blocks governed execution

That is a much healthier product shape than a selector that only prints advice while the heavier contour still runs anyway.

## Current reading

The shortest honest reading is:

- the mode-selection layer now has a first canonical blocked contour on the same primary run surface as the rest of the kernel
- the governed path now respects lighter receipts instead of silently bypassing them
