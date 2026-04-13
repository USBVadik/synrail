# OPERATOR_BRIEF_001

## Purpose

Define the first broader operator-layer slice that compresses current runtime truth into one actionable operator brief.

This slice exists to do one bounded thing:

- reduce continuation-reading tax without hiding the underlying runtime truth

## Artifacts

The operator brief slice now lives at:

- `tools/reference/synrail_operator_brief_v0.py`
- `schemas/operator_brief_record_v0.schema.json`
- `fixtures/operator_brief_run_001/operator_brief.json`

## What it does

The brief compresses current runtime truth into one operator-facing record with:

- current result and stopping stage
- dominant blocker and doctor verdict
- resumability family and active pressures
- current repair step and required inputs
- stale artifact and sub-surface ids
- primary operator action
- one suggested CLI handoff when another `resume` still makes sense

This is intentionally not a new source of truth.

It is a runtime-owned summary surface built from:

- `state`
- `report`
- `repair_packet`
- optional `doctor`

## First canonical reading

The first canonical operator brief is built from one uglier repeated-doctor contour.

Observed result:

- `result = BLOCKED`
- `stopping_stage = doctor`
- `reason = DOCTOR_NOT_GREEN`
- `primary_action = STOP_AND_START_NEW_RUN`
- `termination_reason = MAX_REPAIR_ATTEMPTS`

And the brief still preserves the most useful continuation truth:

- `current_step_id = restore_readiness_truth`
- `next_step_required_inputs = [target_identity_file]`
- `next_step_subsurface_ids = [target_identity_record]`
- `stale_subsurface_ids` still include:
  - `target_identity_record`
  - `readback_record`
  - `scenario_proof_record`
  - `recovery_status_record`
  - `reverification_completion_record`

## Why this matters

This is the first operator-layer move we made only after the harsher kernel pressure slices.

That matters because the brief is now grounded in:

- convergence truth
- repeated doctor pressure
- packet-first continuation
- explicit stop conditions

rather than being only a nicer shell around an under-pressured runtime.

## Current reading

The shortest honest reading is:

- the first broader operator-layer slice now exists
- it compresses runtime truth into one operator brief without replacing the underlying packet and report surfaces
- and on one ugly repeated-doctor contour it correctly tells the operator to stop replaying the same contour and start a new run instead
