# Executable Loop Selected Prepared Run 001

## Purpose

Record the first canonical contour where a preparation-aware strong-path selection receipt is consumed directly by the runtime path.

This document exists so the repo proves one thing clearly:

- the strong-path selection layer is no longer only a policy trace
- it can now hand off directly into the prepared governed contour

## Scenario

- run id: `EXECUTABLE_LOOP_SELECTED_PREPARED_RUN_001`
- task class: `bounded_router_trigger_fix`
- contour shape:
  - preparation-aware strong recommendation emitted
  - strong selection receipt chooses `FULL_GOVERNED_PATH`
  - the same receipt requests prepared governed execution
  - orchestration consumes that receipt directly
  - preparation artifacts are emitted without separately naming them on the CLI
  - closure is accepted

## Artifacts

The selected-prepared run artifacts now live under:

- `fixtures/executable_loop_selected_prepared_run_001/`

Included artifacts:

- `recommendation.json`
- `selection_receipt.json`
- `state.json`
- `doctor.json`
- `plan.json`
- `preparation_receipt.json`
- `bundle.json`
- `closure.json`
- `report.json`
- `orchestration.json`
- `run.json`
- `final_result.json`
- `readback.txt`
- `scenario.txt`

## What was executed

The run used the current executable stack:

1. `synrail_cli_v0.py select-mode`
2. `synrail_cli_v0.py init`
3. `synrail_cli_v0.py orchestrate --mode-selection-receipt ...`

The important part is the third step.

The orchestration command did **not** receive:

- `plan-output`
- `preparation-receipt-output`

Those outputs were derived from the selection receipt because the selected mode was:

- `FULL_GOVERNED_PATH`
- `selected_with_preparation = true`

## Observed path

### 1. Selection path

The selection receipt recorded:

- `selected_mode = FULL_GOVERNED_PATH`
- `selected_with_preparation = true`
- next safe step = `run the full governed path with preparation`

### 2. Runtime handoff

The runtime contour then carried that receipt into the orchestration report and worked artifacts.

Observed result:

- `selection_applied = true`
- `selected_mode = FULL_GOVERNED_PATH`
- `selected_with_preparation = true`
- `preparation_applied = true`

### 3. Prepared closure path

The emitted preparation receipt then confirmed:

- `planned_required_sections_count = 7`
- `planned_required_sections_present_count = 7`
- `complete_on_first_bundle_pass = true`
- `ready_for_closure = true`

The final run stayed:

- `bundle_status = COMPLETE`
- `closure_status = ACCEPTED`
- `resulting_state = CLOSURE_ACCEPTED`

## Why this run matters

This is the first proof that the strong-path selection layer can now do more than say:

- enter the governed contour
- and prefer preparation

It can now actually hand that decision into the runtime path without extra manual stitching.

That is a better product shape because:

- the selector becomes operational instead of merely advisory
- the prepared governed contour becomes easier to enter correctly
- the resulting canonical run artifact keeps both truths on one surface:
  - why the mode was chosen
  - what the runtime actually did with that choice

## Current reading

The shortest honest reading is:

- `Synrail` now has one canonical run where strong selection and prepared governed execution live inside the same artifact family
- the selection layer can now steer the runtime directly instead of stopping at a receipt
