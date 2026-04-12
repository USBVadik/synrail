# Executable Loop Hybrid Pressure Run 003

## Purpose

Record the first hybrid pressure-test that now says the simpler baseline is already good enough on a medium-risk ambiguous closure class.

This document exists so the repo can carry a measured hybrid demotion signal instead of only:

- one unresolved hybrid case
- one hybrid win

## Scenario

- run id: `EXECUTABLE_LOOP_HYBRID_PRESSURE_RUN_003`
- task class: `medium_risk_reversible_artifact_fix`
- scenario shape:
  - the artifact surface is still ambiguous enough to justify pressure-testing
  - the ambiguity is also reversible and cheap to validate
  - hybrid still takes one partial-proof stop
  - but the simpler baseline already keeps false-green exposure low enough

## Artifacts

The run artifacts now live under:

- `fixtures/executable_loop_hybrid_pressure_run_003/`

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

- `fixtures/comparison_input_hybrid_pressure_baseline_003_v1.json`
- `fixtures/comparison_input_hybrid_pressure_synrail_003_v1.json`

## What was executed

This pressure-test again used the current executable stack in two passes:

1. stage 1
   - `synrail_cli_v0.py orchestrate`
   - with `readback.txt`
   - without `scenario.txt`
2. stage 2
   - `synrail_cli_v0.py orchestrate`
   - with both `readback.txt` and `scenario.txt`
   - with economics-aware comparison enabled

That means the result is not a purely hypothetical economics demotion.

It is tied to a real runtime contour that still:

- stopped on missing proof
- repaired the proof
- reached accepted closure

## Observed path

### 1. Stage 1 partial stop

The first pass emitted:

- `OK | closure | MISSING_PROOF_SECTIONS | PROOF_BUNDLE_PARTIAL | CLAIMED_NOT_ACCEPTED`

That keeps the hybrid contour honest.

It still pays for a partial-proof stop.

### 2. Stage 2 accepted re-entry

After adding the missing scenario proof, the repaired pass emitted:

- `OK | comparison | NONE | CLOSURE_ACCEPTED | ACCEPTED`

So the runtime contour itself still works.

The demotion signal is not about runtime failure.

It is about economics.

### 3. Economics verdict

The economics-aware comparison record now says:

- verdict = `BASELINE_GOOD_ENOUGH`

Key deltas:

- operator minutes added = `11`
- intervention count added = `1`
- repair cycles added = `1`
- false-green exposure reduced = `0`
- artifact completeness gain = `14`

That means the hybrid contour still adds some process weight here without delivering a decisive safety gain.

## Why this run matters

This run changes the hybrid class-level reading materially.

Before it, hybrid looked like:

- one `UNCLEAR`
- one `SYNRAIL_BETTER`

After it, hybrid now looks like:

- one `UNCLEAR`
- one `SYNRAIL_BETTER`
- one `BASELINE_GOOD_ENOUGH`

That is enough to demote hybrid from default policy status.

## What this means

The shortest current product reading is now:

- hybrid still has some real value on named ambiguities
- but the class is too inconsistent to remain a default middle lane
- the baseline should now be the default choice unless a specific hybrid pressure-test justifies extra control

## What this does not prove

It does not prove:

- that hybrid should be deleted from the repo
- that no hybrid-shaped scenario can ever win
- that the earlier stronger hybrid pressure-test was false

It proves something narrower and more useful:

- hybrid should now be treated as an explicit exception pattern, not as a standing third policy tier
