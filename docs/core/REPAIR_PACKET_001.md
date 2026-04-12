# Repair Packet 001

## Purpose

Define one richer continuation packet for `Synrail`.

This document exists so continuation no longer depends on:

- one bare repair handoff
- one long raw flag replay
- operator memory about which runtime defaults still matter

## Artifacts

The repair-packet slice now lives at:

- `tools/reference/synrail_repair_packet_v0.py`
- `schemas/repair_packet_v0.schema.json`
- `fixtures/repair_packet_run_001/packet.json`

## What the packet adds

The packet keeps the existing handoff, but now auto-synthesizes one fuller continuation envelope from current runtime truth:

1. embedded `repair_handoff`
2. embedded `continuation_plan`
3. embedded `selection_context`
4. embedded `repair_inputs`
5. embedded `output_defaults`
6. explicit `provided_inputs`
7. explicit `missing_inputs`
8. explicit `ready_for_resume`
9. embedded `preparation_context`
10. embedded `runtime_truth`

That means the packet can now say both:

- what is still missing
- how the runtime should continue once those inputs exist

## Why this matters

The handoff is still the narrow contract for:

- what the current non-green state requires next

The packet is now the richer operator/runtime bundle for:

- continuing through `resume`
- restoring bounded runtime defaults
- carrying refresh intent when continuation should re-enter refresh reconciliation
- carrying selection/preparation truth forward without forcing the operator to replay it manually

The runtime now auto-emits that packet from the current non-green truth surface whenever continuation is still honestly possible.

That means the packet is no longer mainly:

- a hand-authored convenience bundle

It is now mainly:

- a runtime-owned continuation packet
- the default artifact that packet-first `resume` expects to consume

## Current proof points

Current canonical packet surfaces are:

- blocked packet:
  - `fixtures/repair_packet_run_001/packet.json`
- blocked packet-driven resume:
  - `fixtures/repair_packet_run_001/run.json`
- compound packet-driven continuation:
  - `fixtures/executable_loop_compound_continuation_run_002/stage0_packet.json`
  - `fixtures/executable_loop_compound_continuation_run_002/stage1_packet.json`
  - `fixtures/executable_loop_compound_continuation_run_002/stage2_packet.json`
- auto-synthesized selection/preparation packet-driven continuation:
  - `fixtures/executable_loop_compound_continuation_run_003/stage0_packet.json`
  - `fixtures/executable_loop_compound_continuation_run_003/stage1_packet.json`

These prove:

- blocked continuation can now be expressed without a fake `final_result`
- packet-driven resume can now cross invalid bundle and recovery degradation without restating the full runtime surface each time
- runtime-owned packets can now carry selection and preparation handoff through a nastier continuation contour without making the operator rebuild that context by hand

## Current boundary

The packet is richer than the handoff, but still intentionally bounded.

It does not yet try to become:

- a general multi-run plan object
- a broad operator workflow document
- a replacement for all runtime artifacts

It is one continuation packet for one named `resume` path.

The next improvement should make that packet:

- richer where runtime truth already knows more than the current bounded fields express

not:

- broader for its own sake
