# Executable Loop Runtime Resume Run 001

## Purpose

Record the first canonical operator-facing runtime continuation contour for the current executable `Synrail` stack.

This document exists so the repo proves one concrete product step:

- a non-green run can now be resumed through a named runtime entrypoint
- and not only reconstructed through ad hoc orchestration calls

## Scenario

- run id: `EXECUTABLE_LOOP_RUNTIME_RESUME_RUN_001`
- task class: `honesty_restoration_guard`
- starting shape:
  - state already `PROOF_BUNDLE_PARTIAL`
  - doctor already green
  - execution already completed
  - missing proof sections previously:
    - `readback`
    - `scenario_proof`

## Artifacts

The runtime-resume artifacts now live under:

- `fixtures/executable_loop_runtime_resume_run_001/`

Included artifacts:

- `starting_state.json`
- `state.json`
- `doctor.json`
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

1. `synrail_cli_v0.py resume`

That is the important difference.

This contour did not rely on:

- a fresh `init`
- a manually narrated re-entry

It resumed directly from the supplied non-green state.

## Observed path

### 1. Resume starting point

The contour started from:

- `PROOF_BUNDLE_PARTIAL`
- `CLAIMED_NOT_ACCEPTED`
- `MISSING_PROOF_SECTIONS`

The runtime report now records that truth explicitly:

- `resume_applied = true`
- `resume_from_state = PROOF_BUNDLE_PARTIAL`

### 2. Runtime continuation path

After supplying the missing proof inputs, the runtime path progressed through:

- green doctor
- complete proof bundle
- accepted closure

Observed final reading:

- `OK | accepted | NONE | CLOSURE_ACCEPTED | ACCEPTED`

## Why this run matters

This is the first proof that re-entry is no longer only:

- a canonical repaired fixture family
- or an implicit use of the generic orchestration path

It is now also:

- one named runtime continuation entrypoint
- on the same primary machine-readable artifact surface as the other kernel runs

That is a better product shape because the operator now has a clearer continuation path from a non-green state.

## Current reading

The shortest honest reading is:

- `Synrail` now has one first-class runtime resume path from a partial proof lane back to accepted closure
- continuation is starting to become product behavior, not only repo evidence
