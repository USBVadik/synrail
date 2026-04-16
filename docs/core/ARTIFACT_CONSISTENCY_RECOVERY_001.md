# ARTIFACT_CONSISTENCY_RECOVERY_001

Run one recovery pass that combines mixed artifact consistency truth with a verified matching checkpoint.

## Purpose

This is a narrow bridge from consistency failure into concrete recovery action.
The goal is not to invent richer recovery vocabulary.
The goal is to turn:
- corrupt derived artifacts
- stale derived artifacts
- verified checkpoint availability

into one explicit restore-or-reemit plan without operator ambiguity.

## Canonical artifacts

- `fixtures/artifact_consistency_run_004/mixed.json`
- `fixtures/artifact_consistency_recovery_run_001/checkpoint_verify.json`
- `fixtures/artifact_consistency_recovery_run_001/recovery.json`

## Expected reading

The recovery record should show:
- `primary_action = RESTORE_CORRUPT_AND_REEMIT_STALE`
- `restore_artifact_ids = [report]`
- `reemit_artifact_ids = [repair_packet]`
- `ambiguous = false`

That is the concrete kernel move we want:
restore what is corrupt from the verified checkpoint, and re-emit what is only stale from `state_file`.
