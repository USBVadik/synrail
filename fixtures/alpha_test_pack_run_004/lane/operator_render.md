# Operator Render

## Do This Now

- Update the result payload in .synrail/final_result.json. Leave every other proof surface unchanged.
- next safe step: `repair the final result artifact and rebuild the proof bundle`
- suggested CLI: `synrail resume --state-file .synrail/state.json --repair-packet-file .synrail/repair_packet.json`

## Current Focus

- current step: `repair_final_result_artifact`
- current subsurface: `final_result_payload`
- edit target: `.synrail/final_result.json`
- operator focus: update the result payload in .synrail/final_result.json
- required inputs:
- `final_result`

## Runtime Summary

- run: `ALPHA_RUN_20260415T182201Z`
- task class: `bounded_change`
- entry state: `PROOF_BUNDLE_INVALID`
- resulting state: `PROOF_BUNDLE_INVALID`
- result: `OK`
- stopping stage: `closure`
- reason: `INVALID_PROOF_BUNDLE`
- primary action: `REPAIR_CURRENT_STEP`

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

## Why

the packet still names one current repair step, its required inputs, and the stale sub-surfaces to tighten next
