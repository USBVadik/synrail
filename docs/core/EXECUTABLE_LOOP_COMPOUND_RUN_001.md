# Executable Loop Compound Run 001

## Purpose

Record the first canonical ugly compound contour for the current executable `Synrail` stack.

This document exists so the repo can point to one concrete run that does not stay inside a single neat repair family.

It starts with a blocked readiness surface, moves through a partial proof plus degraded recovery surface, and only then returns to accepted closure.

## Scenario

- run id: `EXECUTABLE_LOOP_COMPOUND_RUN_001`
- task class: `bounded_router_trigger_fix`
- starting shape:
  - fresh initialized run state
  - exact-retry doctor required
  - exact prompt identity artifact initially missing
  - proof inputs initially incomplete
  - later recovery reverification intentionally left pending before final repair

## Artifacts

The compound run artifacts now live under:

- `fixtures/executable_loop_compound_run_001/`

Included artifacts:

- `starting_state.json`
- `stage1_state.json`
- `stage1_doctor.json`
- `stage1_report.json`
- `stage1_orchestration.json`
- `stage1_run.json`
- `stage2_state.json`
- `stage2_doctor.json`
- `stage2_bundle.json`
- `stage2_closure.json`
- `stage2_refresh.json`
- `stage2_report.json`
- `stage2_orchestration.json`
- `stage2_run.json`
- `state.json`
- `doctor.json`
- `bundle.json`
- `closure.json`
- `refresh.json`
- `report.json`
- `orchestration.json`
- `run.json`
- `comparison_economics.json`
- `final_result.json`
- `prompt_identity.txt`
- `readback.txt`
- `scenario.txt`

## What was executed

This run uses the current executable stack in three bounded passes over the same run id:

1. `synrail_cli_v0.py orchestrate`
   - with missing exact prompt identity evidence
2. `synrail_cli_v0.py orchestrate`
   - with repaired identity
   - with proof still partial
   - with refresh forcing `recovery_status = PENDING`
3. `synrail_cli_v0.py orchestrate`
   - with repaired proof sections
   - with refresh forcing `recovery_status = COMPLETE`
   - with `reverification_complete = true`
4. `synrail_cli_v0.py compare`
   - with compound comparison inputs under the economics-aware `v1` schema

## Observed path

### 1. Stage 1: blocked readiness

The first pass stops early and honestly.

Observed primary reading:

- `BLOCKED | doctor | DOCTOR_NOT_GREEN | DOCTOR_BLOCKED | CLAIMED_NOT_ACCEPTED`

Important detail:

- the doctor fail is not broad chaos
- it is one narrow exact-retry blocker:
  - missing exact prompt identity artifact

### 2. Stage 2: repaired readiness, then compound partial plus degraded surface

The second pass repairs readiness, but it still does not get to green closure.

Observed primary reading:

- `OK | refresh | MISSING_PROOF_SECTIONS | PROOF_BUNDLE_PARTIAL | CLAIMED_NOT_ACCEPTED`

This stage is the most important ugly middle in the fixture.

The refresh layer records competing invalidations:

- `closure_invalidated_by_partial_bundle`
- `closure_invalidated_by_recovery`

with dominant invalidation:

- `closure_invalidated_by_partial_bundle`

That matters because the kernel is now holding:

- repaired readiness
- partial proof
- pending recovery reverification

inside one compound surface instead of flattening everything into one vague red state.

### 3. Stage 3: repaired proof and repaired recovery

The final pass supplies the missing proof sections and closes the recovery gap.

Observed primary reading:

- `OK | refresh | NONE | CLOSURE_ACCEPTED | ACCEPTED`

That matters because the kernel is not only:

- blocking
- downgrading
- naming next safe steps

It is also carrying one ugly repaired contour all the way back to honest acceptance.

### 4. Economics reading

The same scenario now also has a first economics-aware comparison record:

- `comparison_economics.json`

Observed economics reading:

- verdict: `SYNRAIL_BETTER`
- false-green exposure reduced: `3`
- artifact completeness gained: `70`
- operator minutes added: `33`

This is useful because the compound fixture now tests not only:

- runtime behavior

but also:

- whether the extra control still looks worth paying for on a proof-sensitive ugly path

## Why this run matters

This fixture strengthens the repo in a way the clean single-family runs could not:

- it proves one compound path through blocked, partial, degraded, and repaired states
- it proves the precedence rules are not only decorative
- it proves the current primary run artifact shape still makes sense under messier execution
- it gives the economics harness one first compound pressure-test surface

## What this does not prove

It does not prove:

- that all compound families are already equally mature
- that hybrid compound cases are already equally strong
- that the current economics model is complete
- that the kernel is already production-grade under messy reality

It only proves that the current stack can now hold one honest canonical compound repair contour inside the repo itself.
