# Executable Loop Degraded Reentry Run 001

## Purpose

Record the first canonical degraded-to-accepted re-entry contour for the current executable `Synrail` stack.

This document exists so the repo can point to one concrete run that starts from a degraded post-refresh state and returns to accepted closure after recovery reverification is completed.

## Scenario

- run id: `EXECUTABLE_LOOP_DEGRADED_REENTRY_RUN_001`
- task class: `bounded_router_trigger_fix`
- starting shape:
  - proof bundle already complete
  - closure previously `CLAIMED_NOT_ACCEPTED`
  - recovery previously `PENDING`
  - reverification previously incomplete
  - state previously held at `RECOVERY_PENDING`

## Artifacts

The degraded re-entry run artifacts now live under:

- `fixtures/executable_loop_degraded_reentry_run_001/`

Included artifacts:

- `starting_state.json`
- `state.json`
- `doctor.json`
- `bundle.json`
- `closure.json`
- `refresh.json`
- `report.json`
- `orchestration.json`
- `run.json`
- `final_result.json`
- `readback.txt`
- `scenario.txt`

## What was executed

This run starts from the degraded post-refresh surface and then repairs the missing recovery truth.

The run used the current executable stack:

1. `synrail_cli_v0.py orchestrate`

The contour supplied:

- complete proof inputs
- a refresh event with:
  - `recovery_status = COMPLETE`
  - `reverification_complete = true`

That matters because this fixture is specifically about honest recovery completion, not only about replaying a green happy path.

## Observed path

### 1. Starting degraded reading

The starting state is not fresh and not only partially proven.

It starts from:

- `RECOVERY_PENDING`
- `CLAIMED_NOT_ACCEPTED`
- `RECOVERY_REVERIFICATION_INCOMPLETE`

That makes this a:

- degraded-post-refresh
- repaired-reverification
- accepted-reentry

example.

### 2. Re-entry path

After recovery reverification was completed, the bounded contour progressed through:

- green doctor
- complete proof bundle
- refresh reconciliation

Observed final reading:

- `OK | refresh | NONE | CLOSURE_ACCEPTED | ACCEPTED`

This is the most important behavior in the fixture.

The contour does not keep a degraded recovery state frozen once:

- the lower-level recovery truth is repaired
- reverification is complete
- no stronger invalidation remains

### 3. Primary artifact path

This degraded re-entry run now has the same primary machine-readable entrypoint shape as the other canonical runs:

- `fixtures/executable_loop_degraded_reentry_run_001/run.json`

It also has:

- `fixtures/executable_loop_degraded_reentry_run_001/orchestration.json`

as the worked-envelope layer.

That means recovery completion no longer lives only as:

- an operator intention
- a hoped-for next step
- a narrative claim that the system is green again

It now lives as a canonical repo artifact.

## Why this run matters

This fixture strengthens the kernel in a useful way:

- degraded recovery is not modeled as terminal non-acceptance
- the refresh layer can now reconcile a repaired recovery surface back into accepted closure
- the repaired edge is machine-readable on the same primary artifact surface as the other canonical runs

That is materially better than having refresh only invalidate and never canonically restore.

## What this does not prove

It does not prove:

- that every degraded contour is equally easy to repair
- that all future recovery families should reconcile the same way
- that hybrid degraded paths are already equally mature
- that the current refresh semantics are production-complete

It only proves that the current stack can now hold one honest, canonical degraded-to-accepted re-entry contour inside the repo itself.
