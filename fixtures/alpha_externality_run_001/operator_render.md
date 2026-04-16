# Operator Render

## Summary

- run: `ALPHA_RUN_20260414T110438Z`
- task class: `bounded_change`
- entry state: `PROOF_BUNDLE_INVALID`
- resulting state: `PROOF_BUNDLE_INVALID`
- result: `OK`
- stopping stage: `closure`
- reason: `INVALID_PROOF_BUNDLE`
- primary action: `REPAIR_CURRENT_STEP`

## Why

the packet still names one current repair step, its required inputs, and the stale sub-surfaces to tighten next

## Current step

- current step: `repair_final_result_artifact`
- next safe step: `repair the final result artifact and rebuild the proof bundle`
- operator focus: repair the final result artifact and rebuild the proof bundle

## Inputs

- `final_result`

## Stale sub-surfaces

- `final_result_payload`
- `diff_provenance_record`
- `cleanup_status_record`
- `readback_record`
- `scenario_proof_record`

## Termination

- status: `CONTINUE`
- reason: `NONE`
- attempts: `0`

## Suggested CLI

`synrail resume --state-file synrail/fixtures/alpha_external_run_001/state.json --repair-packet-file synrail/fixtures/alpha_external_run_001/repair_packet.json`
