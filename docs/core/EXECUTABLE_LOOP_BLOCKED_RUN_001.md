# Executable Loop Blocked Run 001

## Purpose

Record the first canonical blocked contour for the current executable `Synrail` stack.

This document exists so the repo can point to one concrete blocked run that is represented through the same primary artifact shape as successful runs.

## Scenario

- run id: `EXECUTABLE_LOOP_BLOCKED_RUN_001`
- task class: `proof_sensitive_fix`
- block shape:
  - target surface attested
  - doctor green
  - exact-task identity intentionally missing
  - run blocked before bundle or closure progression

## Artifacts

The blocked run artifacts now live under:

- `fixtures/executable_loop_blocked_run_001/`

Included artifacts:

- `run.json`
- `state.json`
- `doctor.json`
- `report.json`
- `orchestration.json`
- `final_result.json`

## What was executed

The run used the current executable stack:

1. `synrail_cli_v0.py init`
2. `synrail_cli_v0.py orchestrate`

The contour intentionally omitted:

- `prompt_identity`
- `task_identity`

so the spine would have to block the run at the readiness transition.

## Observed path

### 1. Doctor path

Before the block, the run emitted a green doctor record:

- verdict = `ACCEPTABLE_FOR_CORE_RUN`

That matters because this fixture is not a doctor-fail example.

It is specifically a:

- green-doctor
- failed-integrity
- blocked-readiness

example.

### 2. Blocking path

The spine blocked the run at:

- `ready_transition`

Observed blocked reading:

- dominant blocker = `EXACT_TASK_IDENTITY_NOT_CONFIRMED`
- resulting state = `TARGET_SURFACE_ATTESTED`
- closure status = `CLAIMED_NOT_ACCEPTED`
- next safe step = `restore exact prompt and task identity`

This is the most important behavior in the fixture.

The contour does not pretend that:

- a green doctor alone is enough
- bounded execution may start anyway
- the run is “basically ready”

### 3. Primary artifact path

This blocked run now has the same primary machine-readable entrypoint shape as the green runs:

- `fixtures/executable_loop_blocked_run_001/run.json`

It also has:

- `fixtures/executable_loop_blocked_run_001/orchestration.json`

as the lower-layer worked envelope.

That means blocked contours no longer live only as:

- ad hoc reports
- terminal output
- prose descriptions

They now live on the same canonical artifact surface as accepted or partial runs.

## Why this run matters

This fixture strengthens the kernel in a useful way:

- blocked progression is first-class
- blocked output is machine-readable
- blocked runs use the same primary artifact shape as non-blocked runs

That is a better product surface than having rich artifacts only for the greener paths.

## What this does not prove

It does not prove:

- that every blocked contour is already modeled
- that blocked-state economics are fully benchmarked
- that the current readiness layer is production-complete

It only proves that the current stack can now emit one canonical blocked run reading without dropping onto a second-class output path.
