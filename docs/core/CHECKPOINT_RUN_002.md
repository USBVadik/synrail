# CHECKPOINT_RUN_002

## Purpose

Record the first failed-restore checkpoint pressure-test for `Synrail`.

This slice exists to prove the stricter checkpoint claim:

- restore success is not “files copied”
- restore must start from one pre-verified safe point
- restore success requires restore verification
- failed restore must not silently leave a half-restored target behind

## Artifacts

The canonical failed-restore fixture now lives at:

- `fixtures/checkpoint_run_002/checkpoint_create.json`
- `fixtures/checkpoint_run_002/checkpoint_verify.json`
- `fixtures/checkpoint_run_002/checkpoint_restore.json`

## Scenario

- checkpoint id: `CHECKPOINT_RUN_002`
- source contour:
  - `EXECUTABLE_LOOP_SELECTED_PREPARED_RUN_001`
- restore target pressure:
  - one unexpected artifact already exists under the restore target

## What happened

### 1. Create and verify

Checkpoint creation and verification both passed.

Observed result:

- `CREATE -> OK`
- `VERIFY -> OK`
- `safe_point_class = VERIFIED_ACCEPTED_STATE`

### 2. Restore

Restore copied the checkpoint manifest into the target root and then re-verified the restored surface.

That verification found:

- `artifacts/unexpected.json`

Observed result:

- `event_type = RESTORE_ROLLBACK`
- `result = BLOCKED`
- `restore.status = RESTORE_FAILED`
- `rollback.status = ROLLED_BACK`

### 3. Post-rollback target state

After rollback, the checkpoint-owned restored artifacts are gone and only the pre-existing conflicting artifact remains.

## Why this matters

This is the first narrow proof that checkpoint now behaves more like kernel safety infrastructure and less like loose file copying.

The runtime now has one honest answer when restore verification fails:

- do not claim restore success
- emit the failure
- roll back the checkpoint-owned restore artifacts

## Current reading

The shortest honest reading is:

- happy-path checkpoint is now real
- failed-restore rollback is now also real
- restore is now gated by pre-verified safe-point truth, not only by copied files
- checkpoint is now strong enough to move from “future safety idea” into “bounded kernel capability”
