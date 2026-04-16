# Executable Loop Hybrid Pressure Run 002

## Purpose

Record the first uglier hybrid pressure-test that now produces a stronger measured signal than the original hybrid run.

This document exists so the repo can point to one concrete hybrid case where:

- the lightweight baseline looks too loose
- the hybrid subset takes one explicit stop
- the repaired hybrid contour still returns to accepted closure

## Scenario

- run id: `EXECUTABLE_LOOP_HYBRID_PRESSURE_RUN_002`
- task class: `medium_risk_conflicting_artifact_fix`
- scenario shape:
  - the active artifact surface is ambiguous enough to make a fast baseline acceptance risky
  - one explicit readback is available early
  - one explicit scenario check is still missing on the first pass
  - the hybrid contour must stop, repair the missing proof, and only then accept

## Artifacts

The run artifacts now live under:

- `fixtures/executable_loop_hybrid_pressure_run_002/`

Included artifacts:

- `starting_state.json`
- `stage1_state.json`
- `stage1_doctor.json`
- `stage1_bundle.json`
- `stage1_closure.json`
- `stage1_report.json`
- `stage1_orchestration.json`
- `stage1_run.json`
- `state.json`
- `doctor.json`
- `bundle.json`
- `closure.json`
- `report.json`
- `orchestration.json`
- `run.json`
- `comparison_economics.json`
- `final_result.json`
- `readback.txt`
- `scenario.txt`

The economics inputs used for this run are:

- `fixtures/comparison_input_hybrid_pressure_baseline_v1.json`
- `fixtures/comparison_input_hybrid_pressure_synrail_v1.json`

## What was executed

This pressure-test used the current executable stack in two passes:

1. stage 1
   - `synrail_cli_v0.py orchestrate`
   - with `readback.txt`
   - without `scenario.txt`
2. stage 2
   - `synrail_cli_v0.py orchestrate`
   - with both `readback.txt` and `scenario.txt`
   - with economics-aware comparison enabled

That means the contour was not evaluated only as a clean accepted path.

It was evaluated as:

- partial stop
- repaired proof
- accepted re-entry
- measured economics verdict

## Observed path

### 1. Stage 1 partial stop

The first pass emitted:

- `OK | closure | MISSING_PROOF_SECTIONS | PROOF_BUNDLE_PARTIAL | CLAIMED_NOT_ACCEPTED`

That matters because the hybrid contour did not:

- bluff past missing proof
- auto-promote itself to accepted closure

It kept the bounded stop/no-bluff behavior intact.

### 2. Stage 2 accepted re-entry

After adding the missing scenario proof, the repaired pass emitted:

- `OK | comparison | NONE | CLOSURE_ACCEPTED | ACCEPTED`

That matters because the hybrid contour now shows a more realistic sequence than the first hybrid run:

- first stop on missing proof
- then accepted closure after repair

### 3. Economics verdict

The economics-aware comparison record now says:

- verdict = `SYNRAIL_BETTER`

Key deltas:

- operator minutes added = `9`
- intervention count added = `1`
- repair cycles added = `1`
- false-green exposure reduced = `2`
- artifact completeness gain = `38`

This is the strongest hybrid-specific measured signal in the repo so far.

## Why this run matters

This run does something the earlier hybrid evidence did not:

- it shows one medium-risk ambiguous case where the hybrid subset earns extra control cost
- it still stays visibly cheaper than the full governed path
- it proves that hybrid can hold one uglier partial-stop-then-repair contour instead of only a clean unresolved middle reading

That is materially better than keeping hybrid alive only as a policy idea.

## What this does not prove

It does not prove:

- that hybrid is now ready to become a default middle lane
- that one stronger win cancels the earlier `UNCLEAR` hybrid reading
- that hybrid economics are already stable across multiple medium-risk classes

It only proves that hybrid now has:

- one `UNCLEAR` measured case
- one `SYNRAIL_BETTER` measured pressure-test

That is enough to keep hybrid alive.

It is not enough to promote it on its own.

And it is no longer the latest class-level reading after the next hybrid pressure-test was added.
