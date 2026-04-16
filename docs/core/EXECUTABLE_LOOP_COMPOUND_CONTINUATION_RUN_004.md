# Executable Loop Compound Continuation Run 004

## Purpose

Record the next uglier continuation contour where the runtime now has to carry three things together:

- selection/preparation truth from the strong-path handoff
- packet-first `resume` as the default continuation surface
- explicit resumability truth that distinguishes repairable compound states from a truly terminal accepted finish

This document exists so the repo proves that continuation is now strong enough to express not only:

- what can still be repaired

but also:

- when continuation should stop and a new run should begin instead

## Scenario

- run id: `EXECUTABLE_LOOP_COMPOUND_CONTINUATION_RUN_004`
- task class: `bounded_router_trigger_fix`
- governing selection:
  - `FULL_GOVERNED_PATH`
- preparation:
  - selected and carried into the continuation contour

The path starts from one prepared governed attempt that still lands in a repairable compound invalid-proof state.

## Canonical artifacts

The canonical artifact set now lives at:

- `fixtures/executable_loop_compound_continuation_run_004/`

Key stage artifacts:

- `stage0_run.json`
- `stage1_run.json`
- `stage2_run.json`
- `stage3_run.json`
- `run.json`

Key continuation artifacts:

- `stage0_repair_packet.json`
- `stage1_repair_packet.json`
- `stage2_repair_packet.json`

There is intentionally no `stage3_repair_packet.json`.

The final accepted stage now carries:

- `resumability_status = NOT_RESUMABLE`
- `resumability_family = NOT_RESUMABLE_TERMINAL`

## Observed path

### Stage 0

Observed reading:

- `OK | closure | INVALID_PROOF_BUNDLE | PROOF_BUNDLE_INVALID | CLAIMED_NOT_ACCEPTED`

Packet reading:

- `resumability.family = REPAIRABLE_COMPOUND`
- `active_pressures = ["INVALID_PROOF", "PARTIAL_PROOF"]`
- `selection_context.applied = true`
- `selection_context.selected_with_preparation = true`
- `ready_for_resume = false`
- `missing_inputs = ["final_result", "readback", "scenario_proof"]`

### Stage 1

Observed reading:

- `BLOCKED | repair_handoff | CONTINUATION_INPUTS_MISSING | PROOF_BUNDLE_INVALID | CLAIMED_NOT_ACCEPTED`

This is important because the runtime now blocks before false continuation while still preserving:

- selection truth
- preparation truth
- repairable compound-family truth

### Stage 2

After the missing proof inputs are repaired and the contour is resumed through the packet-first path, the runtime reaches:

- `OK | refresh | RECOVERY_REVERIFICATION_INCOMPLETE | RECOVERY_PENDING | CLAIMED_NOT_ACCEPTED`

Packet reading:

- `resumability.family = REPAIRABLE_RECOVERY_PENDING`
- `active_pressures = ["RECOVERY_PENDING"]`
- `missing_inputs = ["refresh_recovery_complete", "refresh_reverification_complete"]`
- `selection_context.applied = true`
- `preparation_context.applied = true`

### Stage 3

After recovery completion and reverification are supplied through the same packet-first path, the runtime returns to:

- `OK | refresh | NONE | CLOSURE_ACCEPTED | ACCEPTED`

The final canonical run artifact now also records:

- `selection_applied = true`
- `selected_with_preparation = true`
- `resumability_status = NOT_RESUMABLE`
- `resumability_family = NOT_RESUMABLE_TERMINAL`
- `repair_packet.emitted = false`

That final reading matters because the runtime no longer blurs:

- a repairable continuation state
- and a terminal accepted finish that should start a new run instead

## Why this matters

This contour is stronger than the previous packet-first continuation proof because it now shows all of these on one primary run-artifact surface:

1. strong-path selection handoff survives into continuation
2. preparation handoff survives into continuation
3. packet-first `resume` blocks honestly when the repair contract is still incomplete
4. repairable compound invalid-proof truth narrows into repairable recovery truth
5. final acceptance now lands in an explicit not-resumable terminal family instead of a fuzzy “still maybe resumable” reading

## Product reading

The shortest honest reading is:

- repair packets are now richer because they carry resumability family, active repair pressures, repair order, selection context, preparation context, and runtime truth together
- packet-first `resume` now reads much more like the main continuation surface than a helper layer
- the runtime can now distinguish between:
  - repairable invalid or degraded continuation states
  - and terminal accepted states that should start a new run instead of resuming
