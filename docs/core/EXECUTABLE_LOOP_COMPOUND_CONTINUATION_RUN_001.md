# Executable Loop Compound Continuation Run 001

## Purpose

Record the first canonical ugly continuation contour where a multi-stage repair returns to accepted closure through named `resume` plus machine-readable handoff artifacts.

This document exists so the repo proves that messy continuation no longer depends only on a broad replay of the orchestration command.

## Scenario

- run id: `EXECUTABLE_LOOP_COMPOUND_CONTINUATION_RUN_001`
- task class: `bounded_router_trigger_fix`
- starting shape:
  - state already `DOCTOR_BLOCKED`
  - exact prompt identity was missing
  - later continuation still had both partial proof and pending recovery pressure

## Artifacts

The compound continuation artifacts now live under:

- `fixtures/executable_loop_compound_continuation_run_001/`

Included artifacts:

- `starting_state.json`
- `stage1_handoff.json`
- `stage2_state.json`
- `stage2_handoff.json`
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
- `final_result.json`
- `readback.txt`
- `scenario.txt`

## What was executed

The run used the current executable stack in three steps:

1. emit one repair handoff from the doctor-blocked starting state
2. call `synrail_cli_v0.py resume` with the first repaired identity inputs
3. emit one second repair handoff from the resulting mixed partial-plus-recovery state
4. call `synrail_cli_v0.py resume` again with the missing proof and recovery inputs

## Observed path

### 1. Stage one handoff

The first handoff started from:

- `DOCTOR_BLOCKED`
- `CLAIMED_NOT_ACCEPTED`
- `DOCTOR_NOT_GREEN`

Required continuation inputs:

- `prompt_identity`
- `task_identity`

### 2. First runtime continuation

After those inputs were repaired, the runtime continued through the named `resume` entrypoint and reached a mixed non-green state.

Observed stage-two reading:

- `OK | refresh | MISSING_PROOF_SECTIONS | PROOF_BUNDLE_PARTIAL | CLAIMED_NOT_ACCEPTED`

That stage still carried:

- missing proof sections
- pending recovery reverification

### 3. Stage two handoff

The second handoff then named the remaining continuation contract explicitly.

Required continuation inputs:

- `readback`
- `scenario_proof`
- `refresh_recovery_complete`
- `refresh_reverification_complete`

Runtime defaults now also carried:

- `refresh_event_type = RECOVERY_EVENT`
- `refresh_use_bundle = true`
- `refresh_use_closure = true`

### 4. Final runtime continuation

After the remaining proof and recovery inputs were supplied, the same named `resume` contour returned to:

- `OK | refresh | NONE | CLOSURE_ACCEPTED | ACCEPTED`

The final runtime artifacts now record:

- `resume_applied = true`
- `resume_from_state = PROOF_BUNDLE_PARTIAL`
- `repair_handoff_applied = true`
- `repair_handoff_from_state = PROOF_BUNDLE_PARTIAL`

## Why this run matters

This is stronger than the earlier ugly compound repair proof because the runtime now carries that path through:

- one named continuation entrypoint
- one explicit first handoff
- one explicit second handoff
- one shared primary run-artifact surface

That means the compound repair contour is now less ceremonial and less dependent on the operator remembering what the next repair packet should contain.

## Current reading

The shortest honest reading is:

- `Synrail` now has one ugly compound continuation family that runs through named `resume` plus machine-readable repair handoff
- continuation is now strong enough to cross readiness repair, proof repair, and recovery repair on the same runtime surface
- this is still bounded, but it is a materially more product-real continuation contour than the earlier generic replay path
