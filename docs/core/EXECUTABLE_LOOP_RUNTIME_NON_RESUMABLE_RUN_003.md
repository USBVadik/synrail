# Executable Loop Runtime Non Resumable Run 003

## Purpose

Record the first canonical runtime contour where named `resume` is rejected because the run is already in a rejected terminal state.

This document exists so the repo proves that terminal rejection is also now one explicit non-resumable continuation family.

## Scenario

- run id: `EXECUTABLE_LOOP_RUNTIME_NON_RESUMABLE_RUN_003`
- task class: `proof_sensitive_reject_case`
- starting shape:
  - state already `CLOSURE_REJECTED`
  - proof bundle already `COMPLETE`
  - closure already `REJECTED`

## Artifacts

The canonical artifact set now lives at:

- `fixtures/executable_loop_runtime_non_resumable_run_003/`

Included artifacts:

- `starting_state.json`
- `state.json`
- `repair_handoff.json`
- `repair_packet.json`
- `report.json`
- `orchestration.json`
- `run.json`

## Observed path

### 1. Starting truth

The contour starts from:

- `CLOSURE_REJECTED`
- `REJECTED`
- `OPERATOR_REJECTED_RESULT`

### 2. Repair packet reading

The emitted packet now records:

- `resumability.status = NOT_RESUMABLE`
- `resumability.family = NOT_RESUMABLE_TERMINAL_REJECTED`
- `repair_policy.next_step_id = start_new_run`

Artifact-quality truth is also explicit:

- `artifact_id = terminal_run_state`
- `still_stale_parts = ["rejected_terminal_state"]`
- stale sub-surface:
  - `rejected_terminal_state`

### 3. Runtime result

When `resume` is attempted anyway, the runtime now blocks at:

- `BLOCKED | resume | TERMINAL_STATE_NOT_RESUMABLE | CLOSURE_REJECTED | REJECTED`

Observed final reading:

- `resumability_status = NOT_RESUMABLE`
- `resumability_family = NOT_RESUMABLE_TERMINAL_REJECTED`
- `resumability_requires_new_run = true`

## Why this run matters

This is the first canonical proof that rejected closure is now expressed as one explicit not-resumable continuation family instead of living only as one generic terminal stop.

That matters because the runtime can now distinguish between:

- repairable blocked or degraded contours
- accepted terminal finish
- rejected terminal finish

on separate machine-readable continuation families.

## Current reading

The shortest honest reading is:

- packet-first continuation now has one explicit non-resumable rejected-terminal family
- rejected closure now also tells the operator to start a new run instead of attempting governed continuation again
