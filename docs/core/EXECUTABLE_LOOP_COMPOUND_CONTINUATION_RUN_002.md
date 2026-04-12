# Executable Loop Compound Continuation Run 002

## Purpose

Record one uglier packet-driven continuation contour for the executable `Synrail` runtime.

This document exists so the repo proves a messier continuation path through:

- blocked readiness
- invalid proof bundle
- degraded recovery
- accepted closure

using named `resume` plus richer repair packets.

## Canonical artifacts

The canonical artifact set now lives at:

- `fixtures/executable_loop_compound_continuation_run_002/stage0_run.json`
- `fixtures/executable_loop_compound_continuation_run_002/stage1_run.json`
- `fixtures/executable_loop_compound_continuation_run_002/stage2_run.json`
- `fixtures/executable_loop_compound_continuation_run_002/stage3_run.json`
- `fixtures/executable_loop_compound_continuation_run_002/run.json`

The richer continuation packets for that same contour now live at:

- `fixtures/executable_loop_compound_continuation_run_002/stage0_packet.json`
- `fixtures/executable_loop_compound_continuation_run_002/stage1_packet.json`
- `fixtures/executable_loop_compound_continuation_run_002/stage2_packet.json`
- `fixtures/executable_loop_compound_continuation_run_002/stage3_packet.json`

## Run shape

The contour now goes:

1. `DOCTOR_BLOCKED`
2. blocked at `repair_handoff`
3. repair prompt/task identity
4. `PROOF_BUNDLE_INVALID`
5. repair bundle inputs
6. refresh degradation to `RECOVERY_PENDING`
7. complete reverification
8. `CLOSURE_ACCEPTED`

## Stage readings

### Stage 0

- artifact:
  - `fixtures/executable_loop_compound_continuation_run_002/stage0_run.json`
- reading:
  - `BLOCKED | repair_handoff | CONTINUATION_INPUTS_MISSING | DOCTOR_BLOCKED | CLAIMED_NOT_ACCEPTED`

### Stage 1

- artifact:
  - `fixtures/executable_loop_compound_continuation_run_002/stage1_run.json`
- reading:
  - `OK | closure | INVALID_PROOF_BUNDLE | PROOF_BUNDLE_INVALID | CLAIMED_NOT_ACCEPTED`

### Stage 2

- artifact:
  - `fixtures/executable_loop_compound_continuation_run_002/stage2_run.json`
- reading:
  - `OK | refresh | RECOVERY_REVERIFICATION_INCOMPLETE | RECOVERY_PENDING | CLAIMED_NOT_ACCEPTED`

### Stage 3

- artifact:
  - `fixtures/executable_loop_compound_continuation_run_002/stage3_run.json`
- reading:
  - `OK | refresh | NONE | CLOSURE_ACCEPTED | ACCEPTED`

## Why this matters

This contour proves three things together:

1. richer repair packets can now carry continuation intent, not only missing-input truth
2. named `resume` can now cross more than one non-green family in the same run
3. runtime continuation is now less dependent on replaying a long raw CLI argument set

## Product reading

This is a stronger runtime proof than the first compound continuation contour because it now carries:

- an incomplete packet
- an invalid bundle repair
- a degraded recovery repair

through packet-driven `resume`.
