# Executable Loop Partial Reentry Run 001

## Purpose

Record the first canonical partial-proof re-entry contour for the current executable `Synrail` stack.

This document exists so the repo can point to one concrete run that starts from a partial proof lane and returns to accepted closure after the missing proof sections are completed.

## Scenario

- run id: `EXECUTABLE_LOOP_PARTIAL_REENTRY_RUN_001`
- task class: `honesty_restoration_guard`
- starting shape:
  - doctor already green
  - execution already completed
  - proof bundle previously `PARTIAL`
  - closure previously `CLAIMED_NOT_ACCEPTED`
  - missing proof sections previously:
    - `readback`
    - `scenario_proof`

## Artifacts

The partial re-entry run artifacts now live under:

- `fixtures/executable_loop_partial_reentry_run_001/`

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

This run starts from the partial proof surface and then repairs the missing proof inputs.

The run used the current executable stack:

1. `synrail_cli_v0.py orchestrate`

The contour supplied the previously missing sections:

- `readback.txt`
- `scenario.txt`

and emitted a complete proof basis:

- `final_result.json`
- `bundle.json`
- `closure.json`

## Observed path

### 1. Starting partial reading

The starting state is not a fresh happy path.

It starts from:

- `PROOF_BUNDLE_PARTIAL`
- `CLAIMED_NOT_ACCEPTED`
- `MISSING_PROOF_SECTIONS`

That matters because this fixture is specifically a:

- partial-proof
- repaired-evidence
- accepted-reentry

example.

### 2. Re-entry path

After supplying the missing proof sections, the bounded contour progressed through:

- green doctor
- complete proof bundle
- accepted closure

Observed final reading:

- `OK | accepted | NONE | CLOSURE_ACCEPTED | ACCEPTED`

This is the most important behavior in the fixture.

The contour does not treat a partial-proof lane as a permanent non-acceptance bucket if the missing evidence is actually completed.

### 3. Primary artifact path

This partial re-entry run now has the same primary machine-readable entrypoint shape as the other canonical runs:

- `fixtures/executable_loop_partial_reentry_run_001/run.json`

It also has:

- `fixtures/executable_loop_partial_reentry_run_001/orchestration.json`

as the worked-envelope layer.

That means proof completion no longer lives only as:

- an implied possible next step
- a narrative claim
- a hypothetical future run

It now lives as a canonical repo artifact.

## Why this run matters

This fixture strengthens the kernel in a useful way:

- partial proof is not modeled as terminal non-acceptance
- the kernel can return from a proof-completion lane to accepted closure
- the repaired edge is machine-readable on the same primary artifact surface as other canonical runs

That is materially better than treating proof completion only as a recommendation without a canonical repaired contour.

## What this does not prove

It does not prove:

- that every partial lane is equally easy to repair
- that degraded-to-accepted re-entry is equally mature
- that all hybrid partial cases should become accepted after one proof repair
- that the current proof requirements are production-complete

It only proves that the current stack can now hold one honest, canonical partial-to-accepted re-entry contour inside the repo itself.
