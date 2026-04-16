# Executable Loop Compound Continuation Run 008

## Purpose

Record one even uglier packet-first continuation contour where doctor target-identity pressure comes first, then partial supporting proof pressure, then recovery pressure, and only then honest acceptance.

## Canonical surface

The run now lives at:

- `fixtures/executable_loop_compound_continuation_run_008/run.json`

Stage surfaces:

- `fixtures/executable_loop_compound_continuation_run_008/stage0_run.json`
- `fixtures/executable_loop_compound_continuation_run_008/stage1_run.json`
- `fixtures/executable_loop_compound_continuation_run_008/stage2_run.json`
- `fixtures/executable_loop_compound_continuation_run_008/stage3_run.json`

Packet-native repair history surfaces:

- `fixtures/executable_loop_compound_continuation_run_008/stage0_repair_packet.json`
- `fixtures/executable_loop_compound_continuation_run_008/stage1_repair_packet.json`
- `fixtures/executable_loop_compound_continuation_run_008/stage2_repair_packet.json`
- `fixtures/executable_loop_compound_continuation_run_008/stage3_repair_packet.json`
- `fixtures/executable_loop_compound_continuation_run_008/repair_receipt.json`

## What this contour proves

This run now shows:

1. doctor target-identity pressure can still block the first packet step:
   - `BLOCKED | repair_handoff | CONTINUATION_INPUTS_MISSING | DOCTOR_BLOCKED`
2. once identity is repaired, the same continuation can move into partial supporting proof pressure:
   - `OK | closure | MISSING_PROOF_SECTIONS | PROOF_BUNDLE_PARTIAL`
3. once supporting proof is repaired, the same continuation can move into recovery pressure:
   - `OK | closure | RECOVERY_REVERIFICATION_INCOMPLETE | PROOF_BUNDLE_COMPLETE`
4. once recovery completion is supplied, the same continuation can cross honestly into accepted terminal truth:
   - `OK | refresh | NONE | CLOSURE_ACCEPTED`

## Why this matters

This is stronger than the previous ugly continuation contours because the runtime now proves all of these inside one packet-first family:

- doctor identity repair order
- supporting proof repair order
- recovery repair order
- packet-native repair history across multiple stages
- selected-with-preparation continuation carried forward without stage-specific selection replay
- lower-replay `resume` defaults with fewer required sidecar files

## Current reading

The shortest honest reading is:

- packet-first `resume` now looks much more like the main continuation surface
- repair history is now visible as one chain across stages, not only one last-step receipt
- and the runtime can now survive a nastier order of doctor pressure, proof pressure, recovery pressure, and terminal acceptance in one bounded contour
