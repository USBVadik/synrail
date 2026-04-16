# Executable Loop Runtime Non Resumable Run 002

## Purpose

Record the first canonical runtime contour where named `resume` is rejected because the run is already in an accepted terminal state.

This document exists so the repo proves one more strict continuation boundary:

- packet-first continuation should not keep running after honest acceptance
- accepted terminal state is now one explicit non-resumable family, not only one vague terminal fallback

## Scenario

- run id: `EXECUTABLE_LOOP_RUNTIME_NON_RESUMABLE_RUN_002`
- task class: `proof_sensitive_fix`
- starting shape:
  - state already `CLOSURE_ACCEPTED`
  - proof bundle already `COMPLETE`
  - closure already `ACCEPTED`

## Artifacts

The canonical artifact set now lives at:

- `fixtures/executable_loop_runtime_non_resumable_run_002/`

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

- `CLOSURE_ACCEPTED`
- `ACCEPTED`
- `NONE`

### 2. Repair packet reading

The emitted packet now records:

- `resumability.status = NOT_RESUMABLE`
- `resumability.family = NOT_RESUMABLE_TERMINAL_ACCEPTED`
- `repair_policy.next_step_id = start_new_run`

Artifact-quality truth is also explicit:

- `artifact_id = terminal_run_state`
- `still_stale_parts = ["accepted_terminal_state"]`
- stale sub-surface:
  - `accepted_terminal_state`

### 3. Runtime result

When `resume` is attempted anyway, the runtime now blocks at:

- `BLOCKED | resume | TERMINAL_STATE_NOT_RESUMABLE | CLOSURE_ACCEPTED | ACCEPTED`

Observed final reading:

- `resumability_status = NOT_RESUMABLE`
- `resumability_family = NOT_RESUMABLE_TERMINAL_ACCEPTED`
- `resumability_requires_new_run = true`

## Why this run matters

This is the first canonical proof that accepted closure is now expressed as one explicit not-resumable continuation family.

That matters because the runtime can now distinguish between:

- repairable non-green continuation
- and honest terminal accepted finish

without collapsing both into one looser generic terminal reading.

## Current reading

The shortest honest reading is:

- packet-first continuation now has one explicit non-resumable accepted-terminal family
- accepted closure now tells the operator to start a new run instead of pretending another `resume` attempt is meaningful
