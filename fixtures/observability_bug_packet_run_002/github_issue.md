# Synrail Bug Packet

## Summary
- run id: `ALPHA_RUN_20260414T185910Z`
- task class: `bounded_change`
- state: `DOCTOR_BLOCKED`
- result: `BLOCKED`
- reason: `DOCTOR_NOT_GREEN`
- component error class: `DOCTOR_NOT_GREEN`
- next safe step: `move to a clean or explicitly observed-safe execution surface`

## Acceptance
- criteria revision: ``
- validation status: ``
- validation reason: ``

## Doctor
- final verdict: `NOT_ACCEPTABLE_DIRTY_SURFACE`
- blocking failure classes: `dirty-surface unsafe`
- coverage gate: `PASS`
- coverage reason: `CRITICAL_FAIL_MODE_COVERAGE_MET`

## Continuation
- repair family: `REPAIRABLE_DOCTOR_BLOCKED`
- current step id: `restore_readiness_truth`
- packet replay ready: `True`
- entry artifacts: `state_file, repair_packet`
- precedence: `state_file, repair_packet, repair_receipt, repair_history_chain`
- missing inputs: `clean_surface_confirmation`

## Observability
- transition count: `0`
- repair attempt count: `1`
- rejection count: `1`

## Available Artifacts
- `doctor`
- `observability`
- `repair_packet`
- `report`
- `state`
- `thin_output`

## Missing Artifacts
- `acceptance_validation`
