# Executable Loop Reentry Run 001

## Purpose

Record the first canonical re-entry contour for the current executable `Synrail` stack.

This document exists so the repo can point to one concrete run that starts from a blocked readiness contour and returns to an accepted closure state through the same machine-readable kernel loop.

## Scenario

- run id: `EXECUTABLE_LOOP_REENTRY_RUN_001`
- task class: `proof_sensitive_fix`
- starting shape:
  - target surface already attested
  - doctor already green
  - exact-task identity previously missing
  - closure previously `CLAIMED_NOT_ACCEPTED`
  - state previously held at `TARGET_SURFACE_ATTESTED`

## Artifacts

The re-entry run artifacts now live under:

- `fixtures/executable_loop_reentry_run_001/`

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

This run starts from the blocked readiness surface and then repairs the missing identity inputs.

The run used the current executable stack:

1. `synrail_cli_v0.py orchestrate`

The contour restored:

- `prompt_identity`
- `task_identity`

and supplied complete proof inputs:

- `final_result.json`
- `readback.txt`
- `scenario.txt`

## Observed path

### 1. Starting blocked reading

The starting state is not a fresh green contour.

It starts from:

- `TARGET_SURFACE_ATTESTED`
- `CLAIMED_NOT_ACCEPTED`
- `EXACT_TASK_IDENTITY_NOT_CONFIRMED`

That matters because this fixture is specifically a:

- blocked-readiness
- repaired-identity
- accepted-reentry

example.

### 2. Re-entry path

After restoring exact-task identity, the bounded contour progressed through:

- green doctor
- exact-task integrity restored
- complete proof bundle
- accepted closure

Observed final reading:

- `OK | accepted | NONE | CLOSURE_ACCEPTED | ACCEPTED`

This is the most important behavior in the fixture.

The contour does not treat a blocked readiness state as terminal if the blocker is actually repaired.

### 3. Primary artifact path

This re-entry run now has the same primary machine-readable entrypoint shape as the other canonical runs:

- `fixtures/executable_loop_reentry_run_001/run.json`

It also has:

- `fixtures/executable_loop_reentry_run_001/orchestration.json`

as the worked-envelope layer.

That means repaired reverse edges no longer live only as:

- theory
- terminal notes
- implied behavior in the spine code

They now live as a canonical repo artifact.

## Why this run matters

This fixture strengthens the kernel in a useful way:

- blocked progression is not modeled as permanently terminal
- the kernel can return from a blocked readiness contour to accepted closure
- the reverse edge is machine-readable on the same primary artifact surface as other canonical runs

That is materially better than having a reject engine with no canonical repaired contour.

## What this does not prove

It does not prove:

- that every blocked family already has an equally strong repair path
- that degraded-to-accepted re-entry is equally mature
- that partial-to-accepted re-entry is already canonical
- that the current readiness graph is production-complete

It only proves that the current stack can now hold one honest, canonical blocked-to-accepted re-entry contour inside the repo itself.
