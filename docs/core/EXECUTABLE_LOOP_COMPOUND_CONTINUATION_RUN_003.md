# Executable Loop Compound Continuation Run 003

## Purpose

Record the first canonical ugly continuation contour where:

- selection/preparation handoff enters the governed runtime contour
- the runtime auto-synthesizes richer repair packets from current truth
- packet-first `resume` carries invalid-proof and degraded-recovery repair back to accepted closure

This document exists so the repo proves that packet-driven continuation is no longer only:

- a richer follow-up helper

It is now:

- the default continuation surface for ugly non-green runtime repair

## Scenario

- run id: `EXECUTABLE_LOOP_COMPOUND_CONTINUATION_RUN_003`
- task class: `bounded_router_trigger_fix`
- starting shape:
  - strong-path selection already chose the prepared governed contour
  - the first prepared attempt still landed in `PROOF_BUNDLE_INVALID`
  - continuation then had to cross both invalid proof and degraded recovery before closure could return to green

## Canonical artifacts

The canonical artifact set now lives at:

- `fixtures/executable_loop_compound_continuation_run_003/`

Key artifacts:

- `selection_receipt.json`
- `recommendation.json`
- `stage0_packet.json`
- `stage1_packet.json`
- `stage0_run.json`
- `stage1_run.json`
- `stage2_run.json`
- `run.json`
- `plan.json`
- `preparation_receipt.json`
- `repair_packet.json`

## What was executed

The contour used the current runtime in three steps:

1. start the prepared governed contour from one strong-path selection receipt
2. let the runtime auto-emit `stage0_packet.json` from the resulting invalid-proof state
3. call `synrail_cli_v0.py resume` without replaying the full selection/preparation surface by hand
4. let the runtime auto-emit `stage1_packet.json` from the resulting degraded-recovery state
5. call `synrail_cli_v0.py resume` again through that packet-first continuation path

## Observed path

### 1. Stage 0

Observed reading:

- `OK | closure | INVALID_PROOF_BUNDLE | PROOF_BUNDLE_INVALID | CLAIMED_NOT_ACCEPTED`

Auto-synthesized packet reading:

- `from_state = PROOF_BUNDLE_INVALID`
- `ready_for_resume = false`
- `missing_inputs = ["final_result"]`
- `selection_context.applied = true`
- `selection_context.selected_with_preparation = true`
- `preparation_context.applied = true`
- `runtime_truth.result = OK`

### 2. Stage 1

After the invalid proof inputs were repaired through packet-first `resume`, the runtime reached:

- `OK | refresh | RECOVERY_REVERIFICATION_INCOMPLETE | RECOVERY_PENDING | CLAIMED_NOT_ACCEPTED`

The new auto-synthesized packet then recorded:

- `from_state = RECOVERY_PENDING`
- `ready_for_resume = false`
- `missing_inputs = ["refresh_recovery_complete", "refresh_reverification_complete"]`
- `selection_context.applied = true`
- `selection_context.selected_with_preparation = true`
- `preparation_context.applied = true`
- `runtime_truth.stopping_stage = refresh`

### 3. Stage 2

After recovery completion and reverification were supplied through the same packet-first continuation path, the runtime returned to:

- `OK | refresh | NONE | CLOSURE_ACCEPTED | ACCEPTED`

The final canonical run artifact now records:

- `resume_applied = true`
- `resume_from_state = RECOVERY_PENDING`
- `repair_packet.emitted = false`

That last field matters because the final accepted stage no longer pretends another continuation packet still belongs there.

## Why this run matters

This is stronger than the earlier packet-driven continuation proof because it now combines:

- selection handoff
- preparation handoff
- runtime-owned repair-packet synthesis
- packet-first `resume`
- invalid-proof repair
- degraded-recovery repair

on the same primary run-artifact surface.

That is a much more product-real contour than:

- hand-authoring the next packet
- replaying selection context manually
- or treating `resume` like a convenience wrapper above the “real” orchestration flow

## Current reading

The shortest honest reading is:

- `Synrail` now has one canonical ugly continuation contour where selection/preparation handoff survives into packet-first continuation
- repair packets are now runtime-owned enough that the operator no longer has to rebuild most continuation context by hand
- this is still bounded, but it is materially closer to a real continuation surface than the earlier staged packet run
