# Governed Path Preparation 001

## Purpose

Define the first governed-path preparation slice for `Synrail`.

This document exists so we can reduce operator tax inside winning governed paths by naming the required proof surface before bundle assembly starts.

## Artifacts

The first preparation slice now lives at:

- `tools/reference/synrail_proof_plan_v0.py`
- `tools/reference/synrail_preparation_receipt_v0.py`
- `schemas/proof_bundle_plan_v0.schema.json`
- `schemas/governed_path_preparation_receipt_v0.schema.json`

The first canonical governed-path preparation fixture now lives at:

- `fixtures/governed_path_plan_run_001/plan.json`
- `fixtures/governed_path_plan_run_001/bundle.json`
- `fixtures/governed_path_plan_run_001/preparation_receipt.json`

The first canonical runtime-integrated prepared contour now lives at:

- `fixtures/executable_loop_prepared_run_001/run.json`

## Scenario

- run id: `GOVERNED_PATH_PLAN_RUN_001`
- task class: `bounded_router_trigger_fix`
- contour role:
  - strong governed path
  - predeclare proof surface
  - assemble the bundle once the planned artifacts exist

## What happened

### 1. Proof planning

The planner emitted one machine-readable governed-path plan with:

- all seven required proof sections
- one named artifact path for:
  - final result
  - readback
  - scenario proof
  - bundle output
  - closure output
  - preparation receipt output

### 2. Bundle assembly

The planned artifact set was then assembled into one bundle.

Observed result:

- `bundle_status = COMPLETE`

### 3. Preparation receipt

The preparation receipt then recorded:

- `planned_required_sections_count = 7`
- `planned_required_sections_present_count = 7`
- `complete_on_first_bundle_pass = true`
- `ready_for_closure = true`

## Why this matters

This is not a new acceptance rule.

It is one small cost-reduction slice inside the governed path itself.

That matters because the current winning wedge still carries meaningful operator tax, and some of that tax comes from discovering missing proof sections too late.

## Current reading

The shortest honest reading is:

- `Synrail` can now predeclare the governed-path proof surface before bundle assembly
- it can now emit one receipt showing that a planned governed-path bundle reached `COMPLETE` on the first pass
- it can now also carry that preparation slice through the bounded `orchestrate` path
- this does not yet prove a broad cost reduction inside every strong path
- it does prove one bounded executable move away from post-run proof scrambling
