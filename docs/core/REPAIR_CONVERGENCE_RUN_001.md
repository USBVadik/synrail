# REPAIR_CONVERGENCE_RUN_001

## Purpose

Record the first explicit repair-convergence pressure-test for `Synrail`.

This slice exists to prove one narrow but important kernel claim:

- packet-first continuation now stops honestly when the repair loop is no longer making real progress

## Artifacts

The canonical fixture for this run now lives at:

- `fixtures/repair_convergence_run_001/stage0_repair_packet.json`
- `fixtures/repair_convergence_run_001/stage1_repair_receipt.json`
- `fixtures/repair_convergence_run_001/stage1_followup_packet.json`
- `fixtures/repair_convergence_run_001/stage2_repair_receipt.json`
- `fixtures/repair_convergence_run_001/stage2_followup_packet.json`
- `fixtures/repair_convergence_run_001/stage3_report.json`
- `fixtures/repair_convergence_run_001/final_repair_packet.json`
- `fixtures/repair_convergence_run_001/orchestration.json`
- `fixtures/repair_convergence_run_001/run.json`

## Scenario

Starting state:

- `DOCTOR_BLOCKED`

Repair policy:

- active step: `restore_readiness_truth`
- waiting step: `rerun_closure`

The test deliberately withholds the same exact continuation inputs twice:

- `prompt_identity`
- `task_identity`

That creates two consecutive packet-first repair attempts with no real step completion and no new evidence.

## Stage Reading

### Stage 0

The runtime emits one initial packet for the blocked contour.

Current packet truth:

- `repair_termination.status = CONTINUE`
- `continuation_core.ready_for_resume = false`
- missing inputs remain the same exact readiness inputs

### Stage 1

The first `resume` attempt stays blocked.

Receipt truth:

- `result = STEP_NOT_COMPLETED`
- `completed_step_id = ""`
- `next_step_id = restore_readiness_truth`

### Stage 2

The second `resume` attempt stays blocked on the same repair step with the same missing inputs.

Receipt truth:

- `result = STEP_NOT_COMPLETED`
- `completed_step_id = ""`
- `next_step_id = restore_readiness_truth`

The next follow-up packet then switches to:

- `repair_termination.status = TERMINATE`
- `repair_termination.reason = NO_PROGRESS_DETECTED`
- `repair_termination.stalled_step_id = restore_readiness_truth`

### Stage 3

The third `resume` call does not begin another blind repair attempt.

Instead the runtime blocks immediately at `resume` with:

- `result = BLOCKED`
- `stopping_stage = resume`
- `reason = NO_PROGRESS_DETECTED`

Final packet truth stays aligned with that stop:

- `repair_termination.status = TERMINATE`
- `repair_termination.reason = NO_PROGRESS_DETECTED`
- `repair_history.history_chain_length = 2`

## Why this matters

This is the first narrow proof that continuation is no longer only repairable.

It is also bounded by convergence truth.

That matters because a disciplined-looking loop can still be a bad loop if it keeps replaying the same repair step without new inputs or evidence.

## Current reading

The shortest honest reading is:

- `Synrail` can now preserve repair-history chain and still stop before the next useless retry
- early termination no longer synthesizes one phantom repair attempt after the stop
- repair termination is now part of kernel behavior, not just a descriptive future rule
