# Executable Loop Prepared Run 001

## Purpose

Record the first canonical prepared governed-path contour for the current executable `Synrail` stack.

This document exists so the new preparation slice is proven as part of the spine-owned runtime path, not only as a side helper.

## Scenario

- run id: `EXECUTABLE_LOOP_PREPARED_RUN_001`
- task class: `proof_sensitive_fix`
- contour shape:
  - target surface attested
  - doctor green
  - exact-task identity present
  - governed-path proof plan emitted before bundle assembly
  - preparation receipt confirms first-pass closure readiness
  - closure accepted

## Artifacts

The prepared run artifacts now live under:

- `fixtures/executable_loop_prepared_run_001/`

Included artifacts:

- `run.json`
- `state.json`
- `doctor.json`
- `plan.json`
- `preparation_receipt.json`
- `bundle.json`
- `closure.json`
- `report.json`
- `orchestration.json`
- `final_result.json`
- `readback.txt`
- `scenario.txt`

## What was executed

The run used the current executable stack:

1. `synrail_cli_v0.py init`
2. `synrail_cli_v0.py orchestrate`

Unlike the earlier clean accepted contour, this run explicitly adds:

- `plan-output`
- `preparation-receipt-output`

That is the key difference.

This fixture proves the governed-path preparation slice is now part of the same bounded runtime contour.

## Observed path

### 1. Doctor path

Before proof assembly, the run emitted:

- verdict = `ACCEPTABLE_FOR_CORE_RUN`

### 2. Preparation path

The runtime contour then emitted a governed-path proof plan and a preparation receipt.

Observed result:

- `preparation_applied = true`
- `preparation_ready_for_closure = true`

The preparation receipt recorded:

- `planned_required_sections_count = 7`
- `planned_required_sections_present_count = 7`
- `complete_on_first_bundle_pass = true`

### 3. Bundle and closure path

The prepared bundle then stayed:

- `bundle_status = COMPLETE`

And closure still ended at:

- `closure_status = ACCEPTED`
- `resulting_state = CLOSURE_ACCEPTED`

## Why this run matters

This is the first proof that preparation is no longer only an upstream helper.

It now lives inside the same bounded runtime contour that already holds:

- doctor
- bundle
- closure

That matters because governed-path cost reduction should happen inside the winning contour too, not only by steering weaker paths away from it.

## Current reading

The shortest honest reading is:

- `Synrail` now has one canonical prepared governed-path run
- the spine-owned contour can emit preparation-aware artifacts before closure
- the repo now has one concrete example where planned proof readiness stayed complete on the first bundle pass
