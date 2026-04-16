# Executable Loop Compound Continuation Run 005

## Purpose

Record the next uglier packet-first continuation contour where the runtime now has to carry all of these together:

- strong-path selection and preparation handoff
- richer artifact-quality hints about what is still stale
- explicit multi-step repair policy order
- one newly surfaced readiness failure in the middle of continuation
- recovery repair back to accepted closure

This document exists so the repo proves that packet-first continuation is now doing more than naming raw inputs:

- it can name which artifact is stale
- it can say which repair step must happen now
- and it can stop out-of-order repair attempts before false progress

## Scenario

- run id: `EXECUTABLE_LOOP_COMPOUND_CONTINUATION_RUN_005`
- task class: `bounded_router_trigger_fix`
- governing selection:
  - `FULL_GOVERNED_PATH`
- preparation:
  - selected and carried into continuation

The path starts from one prepared governed attempt that still lands in an invalid proof state with pending recovery pressure.

## Canonical artifacts

The canonical artifact set now lives at:

- `fixtures/executable_loop_compound_continuation_run_005/`

Key stage artifacts:

- `stage0_run.json`
- `stage1_run.json`
- `stage2_run.json`
- `stage3_run.json`
- `run.json`

Key continuation artifacts:

- `stage0_repair_handoff.json`
- `stage0_repair_packet.json`
- `stage1_repair_handoff.json`
- `stage1_repair_packet.json`
- `stage2_repair_handoff.json`
- `stage2_repair_packet.json`
- `stage3_repair_handoff.json`

## Observed path

### Stage 0

Observed reading:

- `BLOCKED | repair_handoff | REPAIR_POLICY_STEP_OUT_OF_ORDER | PROOF_BUNDLE_INVALID | CLAIMED_NOT_ACCEPTED`

Packet and handoff reading:

- `resumability.family = REPAIRABLE_COMPOUND`
- `active_pressures = ["INVALID_PROOF", "PARTIAL_PROOF", "RECOVERY_PENDING"]`
- `repair_policy.next_step_id = repair_final_result_artifact`
- `required_inputs = ["final_result"]`

Artifact-quality hints now point to the still-stale surfaces:

- `final_result_artifact`
- `supporting_proof_artifacts`
- `recovery_reverification_surface`

### Stage 1

After the final result artifact is repaired and the contour is resumed, the runtime surfaces a narrower but newly discovered problem:

- `BLOCKED | doctor | DOCTOR_NOT_GREEN | DOCTOR_BLOCKED | CLAIMED_NOT_ACCEPTED`

Handoff reading:

- `resumability.family = REPAIRABLE_COMPOUND`
- `repair_policy.next_step_id = restore_readiness_truth`
- `required_inputs = ["artifact_path"]`

Artifact-quality hints now change too:

- `readiness_surface`
- `final_result_artifact`
- `supporting_proof_artifacts`
- `recovery_reverification_surface`

### Stage 2

After readiness is repaired through the same packet-first path, the runtime narrows the contour to:

- `OK | refresh | RECOVERY_REVERIFICATION_INCOMPLETE | RECOVERY_PENDING | CLAIMED_NOT_ACCEPTED`

Packet reading:

- `resumability.family = REPAIRABLE_RECOVERY_PENDING`
- `repair_policy.next_step_id = complete_recovery_reverification`
- `required_inputs = ["refresh_recovery_complete", "refresh_reverification_complete"]`
- stale artifact:
  - `recovery_reverification_surface`

### Stage 3

After recovery completion and reverification are supplied through the same runtime path, the contour returns to:

- `OK | refresh | NONE | CLOSURE_ACCEPTED | ACCEPTED`

Final handoff reading:

- `resumability.family = NOT_RESUMABLE_TERMINAL`
- `repair_policy.next_step_id = start_new_run`

## Why this matters

This is the strongest continuation proof in the repo so far because it now shows, on one canonical run surface:

1. selection and preparation truth survive into packet-first continuation
2. out-of-order repair attempts are blocked explicitly
3. the next repair step is narrowed to the current stale artifact surface
4. a new readiness failure can still surface in the middle of continuation
5. the contour can still recover honestly back to accepted closure

## Product reading

The shortest honest reading is:

- repair packets are now richer because they can point to which existing artifact is still stale, not only which new input is missing
- packet-first continuation now has a clearer multi-step repair order instead of one flatter continuation contract
- the runtime is getting stronger under messier continuation reality, not only under cleaner repaired examples
