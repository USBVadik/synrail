# Synrail Alpha Telemetry

## Summary
- telemetry session: `TELEMETRY_7C1EAA88B358`
- tester id: `alpha_tester_001`
- synrail version: `0.1.0`
- os: `Darwin 24.6.0`
- python: `3.9.6`
- run id: `ALPHA_RUN_20260414T112716Z`
- task class: `bounded_change`
- latest state: `PROOF_BUNDLE_INVALID`
- latest result: `PROOF_INVALID`
- latest reason: `INVALID_PROOF_BUNDLE`
- component error class: `INVALID_PROOF_BUNDLE`
- repair attempt count: `0`
- next safe step: `repair the final result artifact and rebuild the proof bundle`

## Command Sequence
- `init` | exit=`0` | state=`INITIALIZED` | result=`` | error=`` | flags=`--artifact-root --telemetry-opt-in --tester-id`
- `check` | exit=`0` | state=`PROOF_BUNDLE_INVALID` | result=`PROOF_INVALID` | error=`INVALID_PROOF_BUNDLE` | flags=`--artifact-root --artifact-viable --baseline-identity --clean-surface --credentials-ok --execution-surface-identity --final-result --helper-ok --prompt-identity --prompt-identity-ok --target-path --task-identity`
- `generate-prompt` | exit=`0` | state=`PROOF_BUNDLE_INVALID` | result=`PROOF_INVALID` | error=`INVALID_PROOF_BUNDLE` | flags=`--artifact-root`

## Questions
- What did Synrail decide correctly?
- Where was the next step unclear?
- What felt like ceremony instead of help?
