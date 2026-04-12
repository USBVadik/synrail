# Executable Loop Runtime Non Resumable Run 001

## Purpose

Record the first canonical runtime contour where named `resume` is rejected not because continuation inputs are missing, but because the current state is honestly outside the governed continuation family.

This document exists so the repo proves one more important boundary:

- not every blocked or non-green contour should be repaired through `resume`
- some contours should explicitly follow a lighter selected mode instead

## Scenario

- run id: `EXECUTABLE_LOOP_RUNTIME_NON_RESUMABLE_RUN_001`
- task class: `low_risk_followup_note`
- starting shape:
  - state already `INITIALIZED`
  - closure already says `MODE_SELECTION_NOT_GOVERNED`
  - selection receipt already chose `LIGHTWEIGHT_BASELINE`
  - heavier governed contour was intentionally not entered

## Artifacts

The canonical artifact set now lives at:

- `fixtures/executable_loop_runtime_non_resumable_run_001/`

Included artifacts:

- `starting_state.json`
- `state.json`
- `selection_receipt.json`
- `repair_handoff.json`
- `report.json`
- `orchestration.json`
- `run.json`

## Observed path

### 1. Starting truth

The contour starts from:

- `INITIALIZED`
- `CLAIMED_NOT_ACCEPTED`
- `MODE_SELECTION_NOT_GOVERNED`

The current selected mode already says:

- `selected_mode = LIGHTWEIGHT_BASELINE`
- `heavier_contour_entered = false`

### 2. Repair handoff reading

The emitted handoff now records:

- `resumability.status = NOT_RESUMABLE`
- `resumability.family = NOT_RESUMABLE_SELECTION_BLOCKED`
- `repair_policy.policy_type = NON_RESUMABLE_NEXT_STEP`
- `repair_policy.next_step_id = switch_to_lighter_mode`

Artifact-quality truth is also explicit:

- `artifact_id = mode_selection_receipt`
- `quality = NON_RESUMABLE`
- `still_stale_parts = ["selected_mode_policy"]`

### 3. Runtime result

When `resume` is attempted anyway, the runtime now blocks at:

- `BLOCKED | resume | STATE_NOT_RESUMABLE | INITIALIZED | CLAIMED_NOT_ACCEPTED`

Observed final reading:

- `resumability_status = NOT_RESUMABLE`
- `resumability_family = NOT_RESUMABLE_SELECTION_BLOCKED`
- `resumability_policy_next_step = switch_to_lighter_mode`

## Why this run matters

This is the first canonical proof that packet-first continuation now has one truly not-resumable family beyond terminal acceptance.

That matters because the runtime can now distinguish between:

- a repairable governed contour that should continue through `resume`
- and a lighter-mode selection block that should not be dragged back into governed execution

## Current reading

The shortest honest reading is:

- `Synrail` now has one canonical non-resumable continuation family for selection-blocked governed execution
- packet-first continuation is getting stricter not only about missing inputs, but also about when continuation should not happen at all
