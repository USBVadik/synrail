# Executable Loop Accepted Run 001

## Purpose

Record the first canonical accepted contour for the current executable `Synrail` stack.

This document exists so the repo has one stable accepted reference surface inside the repository itself, not only in transient sanity runs.

## Scenario

- run id: `EXECUTABLE_LOOP_ACCEPTED_RUN_001`
- task class: `proof_sensitive_fix`
- contour shape:
  - target surface attested
  - doctor green
  - exact-task identity present
  - complete proof bundle
  - no post-closure refresh degradation

## Artifacts

The accepted run artifacts now live under:

- `fixtures/executable_loop_accepted_run_001/`

Included artifacts:

- `run.json`
- `state.json`
- `doctor.json`
- `bundle.json`
- `closure.json`
- `report.json`
- `orchestration.json`
- `final_result.json`
- `readback.txt`
- `scenario.txt`

## What was executed

The run used the current executable stack:

1. `synrail_cli_v0.py init`
2. `synrail_cli_v0.py orchestrate`

Unlike the stronger comparative run in `EXECUTABLE_LOOP_RUN_001`, this fixture does not add:

- refresh degradation
- baseline comparison

Its role is narrower:

- show one clean accepted contour
- preserve one canonical accepted output surface

## Observed path

### 1. Doctor path

Before proof assembly, the run emitted:

- verdict = `ACCEPTABLE_FOR_CORE_RUN`

This fixture therefore begins from a real green readiness state rather than from a simplified “assume ready” shortcut.

### 2. Bundle path

The run then assembled a complete proof bundle with:

- machine-readable final result
- readback present
- scenario proof present
- artifact identity present
- cleanup status present

Observed result:

- proof bundle status = `COMPLETE`

### 3. Closure path

The closure engine then emitted:

- closure status = `ACCEPTED`
- blocking reason = `""`
- next safe step = `NONE`
- resulting state = `CLOSURE_ACCEPTED`

This is the core value of the fixture:

- one accepted contour
- one stable accepted run artifact
- one proof-complete reference surface

### 4. Primary artifact path

This run now has the primary machine-readable accepted entrypoint:

- `fixtures/executable_loop_accepted_run_001/run.json`

And the lower-layer worked envelope:

- `fixtures/executable_loop_accepted_run_001/orchestration.json`

That makes the accepted contour readable through the same artifact family as:

- the strong comparative run
- the weak partial run
- the hybrid run
- the blocked run

## Why this run matters

This fixture closes an important repo gap.

Before it, the repo had:

- strong comparative reading
- weak partial reading
- hybrid reading
- canonical blocked reading

But it did not yet have one clean canonical accepted contour that stayed inside the repository as a stable artifact set.

Now it does.

## What this does not prove

It does not prove:

- broad runtime superiority
- post-recovery stability
- production-grade orchestration

It only proves that the current executable stack can emit one clean, canonical, accepted run surface entirely inside the repo.
