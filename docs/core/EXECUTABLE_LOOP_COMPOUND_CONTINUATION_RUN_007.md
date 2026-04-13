# Executable Loop Compound Continuation Run 007

## Purpose

Record one uglier packet-first continuation contour where stale proof and stale recovery truth now intersect with one doctor target-identity failure inside the same named `resume` path.

## Canonical surface

The run now lives at:

- `fixtures/executable_loop_compound_continuation_run_007/run.json`

Stage surfaces:

- `fixtures/executable_loop_compound_continuation_run_007/stage0_run.json`
- `fixtures/executable_loop_compound_continuation_run_007/stage1_run.json`
- `fixtures/executable_loop_compound_continuation_run_007/stage2_run.json`
- `fixtures/executable_loop_compound_continuation_run_007/stage3_run.json`

Repair evidence surfaces:

- `fixtures/executable_loop_compound_continuation_run_007/stage0_repair_receipt.json`
- `fixtures/executable_loop_compound_continuation_run_007/stage1_repair_receipt.json`
- `fixtures/executable_loop_compound_continuation_run_007/stage2_repair_receipt.json`
- `fixtures/executable_loop_compound_continuation_run_007/stage3_repair_receipt.json`

## What this contour proves

This run now shows:

1. invalid proof can still stop continuation on the current packet step:
   - `BLOCKED | repair_handoff | CONTINUATION_INPUTS_MISSING | PROOF_BUNDLE_INVALID`
2. packet-first repair can then restore proof truth and move into recovery-pending truth:
   - `OK | closure | RECOVERY_REVERIFICATION_INCOMPLETE | PROOF_BUNDLE_COMPLETE`
3. once recovery completion is supplied, the same continuation can still be stopped by doctor target-identity pressure:
   - `BLOCKED | doctor | DOCTOR_NOT_GREEN | DOCTOR_BLOCKED`
4. the next packet-first continuation can then repair that identity surface and return honestly to accepted closure:
   - `OK | refresh | NONE | CLOSURE_ACCEPTED`

## Why this matters

This is stronger than the previous compound continuation contours because the runtime now proves all of these inside one packet-first family:

- proof repair order
- recovery repair order
- operator-facing repair receipt evidence
- doctor identity pressure mid-continuation
- accepted closure after the identity repair is actually supplied

It is closer to messy runtime reality than a contour that only alternates between proof and recovery pressure.

## Current reading

The shortest honest reading is:

- `resume` is now strong enough to carry one uglier mixed continuation where proof repair, recovery repair, and target-identity repair all show up on the same runtime surface
- repair receipts are now useful enough to tell the operator which exact stale sub-surfaces still matter at each step, not only which generic input bucket is missing
