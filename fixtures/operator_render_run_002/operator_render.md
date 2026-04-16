# Operator Render

## Summary

- run: `EXECUTABLE_LOOP_COMPOUND_CONTINUATION_RUN_010`
- task class: `bounded_router_trigger_fix`
- stage count: `3`
- final action: `STOP_AND_START_NEW_RUN`
- final next safe step: `restore the trusted baseline and expected target-surface identity`
- final resumability family: `REPAIRABLE_COMPOUND`

## Action counts

- `REPAIR_CURRENT_STEP`: `2`
- `STOP_AND_START_NEW_RUN`: `1`

## Stage sequence

### stage0

- resulting state: `PROOF_BUNDLE_PARTIAL`
- result: `OK`
- stopping stage: `closure`
- reason: `MISSING_PROOF_SECTIONS`
- primary action: `REPAIR_CURRENT_STEP`
- current step: `complete_missing_proof_sections`
- next safe step: `collect readback from changed sections on the attested surface`
- required inputs:
- `readback`
- `scenario_proof`
- termination reason: `NONE`

### stage1

- resulting state: `DOCTOR_BLOCKED`
- result: `BLOCKED`
- stopping stage: `doctor`
- reason: `DOCTOR_NOT_GREEN`
- primary action: `REPAIR_CURRENT_STEP`
- current step: `restore_readiness_truth`
- next safe step: `restore the trusted baseline and expected target-surface identity`
- required inputs:
- `target_identity_file`
- termination reason: `NONE`

### stage2

- resulting state: `DOCTOR_BLOCKED`
- result: `BLOCKED`
- stopping stage: `doctor`
- reason: `DOCTOR_NOT_GREEN`
- primary action: `STOP_AND_START_NEW_RUN`
- current step: `restore_readiness_truth`
- next safe step: `restore the trusted baseline and expected target-surface identity`
- required inputs:
- `target_identity_file`
- termination reason: `MAX_REPAIR_ATTEMPTS`

## Why

the operator chain preserves one explicit sequence of repair, continue, and terminal decisions across the multi-stage contour
