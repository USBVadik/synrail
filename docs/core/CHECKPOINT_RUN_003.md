# CHECKPOINT_RUN_003

## Purpose

Record the first canonical working-state checkpoint lifecycle for `Synrail`.

This slice proves that checkpoint is not limited to accepted closure.
It can also protect one verified working state before a risky continuation move.

## Artifacts

The canonical working-state fixture now lives at:

- `fixtures/checkpoint_run_003/checkpoint_create.json`
- `fixtures/checkpoint_run_003/checkpoint_verify.json`
- `fixtures/checkpoint_run_003/checkpoint_restore.json`

## Scenario

- checkpoint id: `CHECKPOINT_RUN_003`
- source contour:
  - `EXECUTABLE_LOOP_RUNTIME_NON_RESUMABLE_RUN_004`
- source state:
  - `READY`
- source closure status:
  - `CLAIMED_NOT_ACCEPTED`
- source doctor status:
  - `PASS`
- source target surface status:
  - `ATTESTED`
- source integrity status:
  - `PASS`

## What happened

### 1. Create

Checkpoint creation classified this source as:

- `safe_point_class = VERIFIED_WORKING_STATE`
- `safe_point_eligible = true`

Observed result:

- `event_type = CREATE`
- `result = OK`

### 2. Verify

Checkpoint verification then confirmed:

- required artifacts present
- schema validation passed
- state consistency passed
- safe-point eligibility remained true

Observed result:

- `event_type = VERIFY`
- `result = OK`
- `verification.status = PASSED`

### 3. Restore

Checkpoint restore copied the verified working-state artifact set into the restore target and re-verified the restored state before calling restore successful.

Observed result:

- `event_type = RESTORE`
- `result = OK`
- `restore.status = RESTORED`
- `rollback.status = NOT_NEEDED`

## Why this matters

This is the narrower product move we need for risky repair and continuation:

- preserve one verified working state before a damaging step
- let the runtime restore to that state if the next move goes bad
- keep checkpoint useful even before closure reaches acceptance

## Current reading

The shortest honest reading is:

- checkpoint now protects both:
  - one verified accepted state
  - one verified working state
- restore still requires verification
- checkpoint is now closer to a real safe-point primitive than a snapshot helper
