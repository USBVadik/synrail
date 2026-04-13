# Artifact Repair Receipt 001

## Purpose

Define one machine-readable artifact repair receipt for packet-first continuation.

This document exists so `Synrail` can record not only what continuation still needs next, but also what repair step just happened and which narrower artifact sub-surfaces are still stale afterward.

## What the receipt carries

The current receipt records:

- the starting non-green state
- the resulting state after the attempted repair step
- whether the step was completed, only progressed, or hit a non-resumable boundary
- the completed repair step id when one really finished
- remaining stale artifact ids
- remaining stale sub-surface ids
- remaining non-resumable artifact ids
- remaining non-resumable sub-surface ids
- richer stale and non-resumable hint objects with:
  - `artifact_id`
  - `repair_step`
  - `still_stale_parts`
  - `stale_subsurfaces`
- completed artifact hints for the step that just finished
- next-step artifact hints for the repair step that now leads the policy order
- operator-facing evidence fields that now say:
  - which step just completed
  - which exact stale sub-surfaces still matter next
  - which narrower inputs the operator should focus on now
- one bounded repair-history record

## Canonical proof points

Current canonical receipt surfaces are:

- `fixtures/executable_loop_compound_continuation_run_006/stage0_repair_receipt.json`
- `fixtures/executable_loop_compound_continuation_run_006/stage1_repair_receipt.json`
- `fixtures/executable_loop_compound_continuation_run_006/stage2_repair_receipt.json`
- `fixtures/executable_loop_compound_continuation_run_006/stage3_repair_receipt.json`
- `fixtures/executable_loop_runtime_non_resumable_run_004/repair_receipt.json`
- `fixtures/executable_loop_compound_continuation_run_007/stage0_repair_receipt.json`
- `fixtures/executable_loop_compound_continuation_run_007/stage1_repair_receipt.json`
- `fixtures/executable_loop_compound_continuation_run_007/stage2_repair_receipt.json`
- `fixtures/executable_loop_compound_continuation_run_007/stage3_repair_receipt.json`

These now prove:

- stage 0 can say one repair step is still not completed because the operator tried to jump ahead of policy order
- stage 1 can say `repair_final_result_artifact` was completed
- stage 2 can say recovery repair is still blocked and exactly which recovery sub-surfaces remain stale
- stage 3 can say the contour crossed into one explicit non-resumable accepted boundary instead of pretending continuation is still open
- one fresh-orchestration non-resumable contour can still emit one truthful receipt explaining why `resume` is the wrong entrypoint
- one uglier mixed contour can now say that recovery completion was supplied, doctor identity still failed, and `target_identity_record` is now the exact next stale sub-surface to repair
- the next receipt in that same contour can then say that identity repair completed and the runtime crossed into terminal accepted truth

## Why this matters

This is stronger than only having:

- one next repair step id
- one list of missing inputs
- one packet snapshot without progress truth

Because the runtime can now tell the operator:

- what changed
- what did not change
- what is still stale inside the existing artifact surface
- and whether the continuation should keep repairing or stop entirely
- and which exact stale sub-surfaces the operator should focus on next instead of reconstructing that from the whole packet by hand

## Current reading

The shortest honest reading is:

- packet-first continuation now has one first-class repair receipt
- receipts now make stale artifact truth more precise at sub-surface level
- and receipts now make multi-step continuation progress machine-readable instead of leaving it implicit between packet snapshots
