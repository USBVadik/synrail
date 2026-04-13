# CHECKPOINT_RUN_001

## Purpose

Record the first canonical happy-path checkpoint lifecycle for `Synrail`.

This slice proves one narrow kernel move:

- create a checkpoint from a known accepted contour
- verify that checkpoint as a safe point
- restore it
- require restore verification before calling the restore successful

## Artifacts

The first checkpoint runtime slice now lives at:

- `tools/reference/synrail_checkpoint_v0.py`
- `schemas/checkpoint_record_v0.schema.json`

The first canonical checkpoint fixture now lives at:

- `fixtures/checkpoint_run_001/checkpoint_create.json`
- `fixtures/checkpoint_run_001/checkpoint_verify.json`
- `fixtures/checkpoint_run_001/checkpoint_restore.json`

## Scenario

- checkpoint id: `CHECKPOINT_RUN_001`
- source contour:
  - `EXECUTABLE_LOOP_SELECTED_PREPARED_RUN_001`
- source state:
  - `CLOSURE_ACCEPTED`
- source closure status:
  - `ACCEPTED`

## What happened

### 1. Create

Checkpoint creation copied one accepted contour into a dedicated checkpoint root and emitted one machine-readable checkpoint record.

Observed result:

- `event_type = CREATE`
- `result = OK`

### 2. Verify

Checkpoint verification then checked:

- required artifacts present
- schema validation
- state consistency

Observed result:

- `event_type = VERIFY`
- `result = OK`
- `verification.status = PASSED`

### 3. Restore

Checkpoint restore then copied the checkpoint artifact set into a restore target and re-verified the restored state before calling the restore successful.

Observed result:

- `event_type = RESTORE`
- `result = OK`
- `restore.status = RESTORED`
- `rollback.status = NOT_NEEDED`

## Why this matters

This does not yet prove a bad-restore rollback contour.

It does prove the first narrower thing we need first:

- `Synrail` can now treat checkpoint as a kernel lifecycle
- not only as a future idea
- and not only as an unverified snapshot

## Current reading

The shortest honest reading is:

- one first-class checkpoint contract now exists
- one minimal checkpoint runtime now exists
- one canonical happy path now proves:
  - create
  - verify
  - restore
  - restore verification before success
- the next pressure step is now obvious:
  - prove failed restore with explicit rollback
