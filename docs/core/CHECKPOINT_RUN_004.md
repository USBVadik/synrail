# CHECKPOINT_RUN_004

Run one checkpoint pressure-test that restores a verified working state onto a dirtied contour.

## Purpose

This is not a new checkpoint feature.
It is a narrow proof that a verified working checkpoint can overwrite a dirtied target contour and return it to a trusted working state.

## Canonical artifacts

- `fixtures/checkpoint_run_003/checkpoint_verify.json`
- `fixtures/checkpoint_run_004/dirty_state_before_restore.json`
- `fixtures/checkpoint_run_004/checkpoint_restore.json`
- `fixtures/checkpoint_run_004/dirty_target/artifacts/state.json`

## Expected reading

The restore record should show:
- `result = OK`
- `restore.status = RESTORED`
- `rollback.status = NOT_NEEDED`

The restored state should return from the dirtied contour back to:
- `state = READY`
- `doctor.status = PASS`
- the working next safe step from the verified checkpoint
