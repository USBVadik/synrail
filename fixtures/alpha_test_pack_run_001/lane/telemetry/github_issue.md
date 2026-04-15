# Synrail Alpha Telemetry

## Summary
- telemetry session: `TELEMETRY_3D357BC4A036`
- tester id: `alpha_pack_smoke`
- synrail version: `0.1.0`
- os: `Darwin 24.6.0`
- python: `3.9.6`
- run id: `ALPHA_RUN_20260415T082755Z`
- task class: `bounded_change`
- latest state: `PROOF_BUNDLE_INVALID`
- latest result: `PROOF_INVALID`
- latest reason: `INVALID_PROOF_BUNDLE`
- component error class: `INVALID_PROOF_BUNDLE`
- repair attempt count: `0`
- next safe step: `repair the final result artifact and rebuild the proof bundle`
- packet replay ready: `True`

## Command Sequence
- `init` | exit=`0` | state=`INITIALIZED` | result=`` | error=`` | flags=`--artifact-root --project-root --task-identity --telemetry-opt-in --tester-id`
- `check` | exit=`0` | state=`PROOF_BUNDLE_INVALID` | result=`PROOF_INVALID` | error=`INVALID_PROOF_BUNDLE` | flags=`--artifact-root`
- `repair-step` | exit=`0` | state=`PROOF_BUNDLE_INVALID` | result=`PROOF_INVALID` | error=`INVALID_PROOF_BUNDLE` | flags=`--artifact-root`

## Questions
- What did Synrail decide correctly?
- Where was the next step unclear?
- What felt like ceremony instead of help?
