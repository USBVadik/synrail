# Executable Loop Runtime Non Resumable Run 004

## Purpose

Record the first canonical runtime contour where named `resume` is rejected because the run is still on the forward governed path rather than in one honest continuation family.

This document exists so the repo proves that packet-first continuation now distinguishes:

- repairable non-green continuation
- terminal non-resumable continuation
- and one fresh forward-orchestration state where the operator should not call `resume` at all

## Scenario

- run id: `EXECUTABLE_LOOP_RUNTIME_NON_RESUMABLE_RUN_004`
- task class: `proof_sensitive_fresh_orchestration_case`
- starting shape:
  - state already `READY`
  - target surface already attested
  - doctor already green
  - proof execution has not started yet

## Artifacts

The canonical artifact set now lives at:

- `fixtures/executable_loop_runtime_non_resumable_run_004/`

Included artifacts:

- `starting_state.json`
- `state.json`
- `repair_handoff.json`
- `repair_packet.json`
- `repair_receipt.json`
- `report.json`
- `orchestration.json`
- `run.json`

## Observed path

### 1. Starting truth

The contour starts from:

- `READY`
- `CLAIMED_NOT_ACCEPTED`
- one forward governed contour that has not yet crossed into repairable continuation

### 2. Repair packet reading

The emitted packet now records:

- `resumability.status = NOT_RESUMABLE`
- `resumability.family = NOT_RESUMABLE_FRESH_ORCHESTRATION`
- `repair_policy.next_step_id = continue_forward_orchestration`

Artifact-quality truth is also explicit:

- `artifact_id = runtime_entrypoint_state`
- `still_stale_parts = ["forward_orchestration_entrypoint"]`
- non-resumable sub-surface:
  - `forward_orchestration_entrypoint`

### 3. Runtime result

When `resume` is attempted anyway, the runtime now blocks at:

- `BLOCKED | resume | STATE_NOT_RESUMABLE | READY | CLAIMED_NOT_ACCEPTED`

Observed final reading:

- `resumability_status = NOT_RESUMABLE`
- `resumability_family = NOT_RESUMABLE_FRESH_ORCHESTRATION`
- `resumability_policy_next_step = continue_forward_orchestration`

## Why this run matters

This is the first canonical proof that packet-first continuation now has one truly not-resumable boundary that is not:

- lighter-mode selection blocked
- accepted terminal closure
- rejected terminal closure

That matters because the runtime can now say:

- this contour is not broken
- this contour is simply not yet a continuation contour

## Current reading

The shortest honest reading is:

- `resume` is no longer treated as a vague generic re-entry verb
- forward governed progress is now one explicit non-resumable family of its own
- packet-first runtime is getting stricter about which entrypoint is valid for which state
