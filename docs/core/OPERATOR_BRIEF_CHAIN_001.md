# OPERATOR_BRIEF_CHAIN_001

## Purpose

Define the first multi-stage operator-brief chain slice.

This slice exists to prove that the broader operator layer can compress:

- more than one blocked or repairable snapshot
- one full repair sequence across an ugly continuation contour

without replacing the underlying runtime-owned truth surfaces.

## Artifacts

The chain slice now lives at:

- `tools/reference/synrail_operator_brief_chain_v0.py`
- `schemas/operator_brief_chain_record_v0.schema.json`
- `fixtures/operator_brief_chain_run_001/operator_brief_chain.json`

That canonical fixture also includes four stage-level briefs:

- `fixtures/operator_brief_chain_run_001/stage0_operator_brief.json`
- `fixtures/operator_brief_chain_run_001/stage1_operator_brief.json`
- `fixtures/operator_brief_chain_run_001/stage2_operator_brief.json`
- `fixtures/operator_brief_chain_run_001/stage3_operator_brief.json`

## Canonical chain

The first chain is built from:

- `core/EXECUTABLE_LOOP_COMPOUND_CONTINUATION_RUN_010.md`

Observed operator sequence:

1. `stage0`
   - `PROOF_BUNDLE_PARTIAL`
   - `primary_action = REPAIR_CURRENT_STEP`
   - `current_step_id = complete_missing_proof_sections`
2. `stage1`
   - `DOCTOR_BLOCKED`
   - `primary_action = REPAIR_CURRENT_STEP`
   - `current_step_id = restore_readiness_truth`
3. `stage2`
   - `PROOF_BUNDLE_COMPLETE`
   - `primary_action = REPAIR_CURRENT_STEP`
   - `current_step_id = complete_recovery_reverification`
4. `stage3`
   - `CLOSURE_ACCEPTED`
   - `primary_action = FOLLOW_NON_RESUMABLE_BOUNDARY`

The resulting chain summary now says:

- `stage_count = 4`
- `action_counts.REPAIR_CURRENT_STEP = 3`
- `action_counts.FOLLOW_NON_RESUMABLE_BOUNDARY = 1`
- `repairable_stage_ids = [stage0, stage1, stage2]`
- `final_action = FOLLOW_NON_RESUMABLE_BOUNDARY`
- `final_resumability_family = NOT_RESUMABLE_TERMINAL_ACCEPTED`

## Why this matters

The single-brief layer already proved two useful things:

- stop this contour
- repair this current step

The chain layer now adds the next bounded operator value:

- show the whole repair sequence across one ugly contour without forcing the operator to re-read every packet and report from scratch

That matters because the operator layer is only worth keeping if it reduces reading tax on real multi-stage runtime pressure, not only on one isolated snapshot.

## Current reading

The shortest honest reading is:

- `operator-brief` is now useful on both single-stage and multi-stage continuation reading
- the chain surface keeps the repair sequence compact while leaving state, report, doctor, and packet as the real sources of truth
- and on one ugly contour it correctly ends with a terminal follow-the-boundary decision instead of pretending the repair sequence should continue forever
