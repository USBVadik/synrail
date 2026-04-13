# REPAIR_CONVERGENCE_RUN_003

## Purpose

Record the complementary repair-convergence pressure-test for `Synrail`.

This slice exists to prove the other bounded stop reason:

- packet-first continuation now stops honestly when the repair loop has already used its allowed attempt budget

## Artifacts

The canonical fixture for this run now lives at:

- `fixtures/repair_convergence_run_003/stage0_synthetic_receipt.json`
- `fixtures/repair_convergence_run_003/stage0_repair_packet.json`
- `fixtures/repair_convergence_run_003/stage1_report.json`
- `fixtures/repair_convergence_run_003/final_repair_packet.json`
- `fixtures/repair_convergence_run_003/orchestration.json`
- `fixtures/repair_convergence_run_003/run.json`

## Scenario

Starting state:

- `DOCTOR_BLOCKED`

Repair policy:

- active step: `restore_readiness_truth`
- waiting step: `rerun_closure`

The test feeds one synthetic prior receipt chain with:

- `history_chain_length = 3`
- bounded prior attempt history already recorded
- no last-two-attempt pattern that should downgrade into `NO_PROGRESS_DETECTED`

That means the next packet should terminate specifically on the retry ceiling, not on no-progress detection.

## Stage Reading

### Stage 0

The synthetic prior receipt is folded into one new packet.

Current packet truth:

- `repair_termination.status = TERMINATE`
- `repair_termination.reason = MAX_REPAIR_ATTEMPTS`
- `repair_termination.attempt_count = 3`
- `continuation_core.ready_for_resume = false`

### Stage 1

The next `resume` call does not begin another repair attempt.

Instead the runtime blocks immediately at `resume` with:

- `result = BLOCKED`
- `stopping_stage = resume`
- `reason = MAX_REPAIR_ATTEMPTS`

Final packet truth stays aligned with that stop:

- `repair_termination.status = TERMINATE`
- `repair_termination.reason = MAX_REPAIR_ATTEMPTS`
- `repair_history.history_chain_length = 3`

## Why this matters

This is the narrower proof that bounded continuation does not only stop on obvious repeated non-progress.

It also stops when the repair loop has already consumed its allowed retry budget, even if the recorded history remains machine-readable.

## Current reading

The shortest honest reading is:

- `Synrail` now has both bounded stop reasons proved:
  - `NO_PROGRESS_DETECTED`
  - `MAX_REPAIR_ATTEMPTS`
- packet-level termination now blocks `resume` before another blind repair attempt starts
