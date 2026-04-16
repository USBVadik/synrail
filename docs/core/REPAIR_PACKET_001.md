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
2. embedded `resumability`
3. embedded `continuation_plan`
4. embedded `selection_context`
5. embedded `repair_inputs`
6. embedded `output_defaults`
7. explicit `provided_inputs`
8. explicit `missing_inputs`
9. explicit `ready_for_resume`
10. embedded `preparation_context`
11. embedded `runtime_truth`
12. packet-native `repair_history_chain`
13. one compact embedded `continuation_core`

That means the packet can now say both:

- what is still missing
- how the runtime should continue once those inputs exist
- whether the current non-green contour is still repairable at all
- what repair order the runtime believes should come next
- which existing artifact surface is still stale while that repair order is unfolding

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
- richer resumability-aware selection/preparation continuation:
  - `fixtures/executable_loop_compound_continuation_run_004/stage0_repair_packet.json`
  - `fixtures/executable_loop_compound_continuation_run_004/stage1_repair_packet.json`
  - `fixtures/executable_loop_compound_continuation_run_004/stage2_repair_packet.json`
- richer artifact-quality and ordered-repair continuation:
  - `fixtures/executable_loop_compound_continuation_run_005/stage0_repair_packet.json`
  - `fixtures/executable_loop_compound_continuation_run_005/stage1_repair_packet.json`
  - `fixtures/executable_loop_compound_continuation_run_005/stage2_repair_packet.json`
- repair-receipt-aware ordered continuation:
  - `fixtures/executable_loop_compound_continuation_run_006/stage0_repair_packet.json`
  - `fixtures/executable_loop_compound_continuation_run_006/stage1_repair_packet.json`
  - `fixtures/executable_loop_compound_continuation_run_006/stage2_repair_packet.json`
  - `fixtures/executable_loop_compound_continuation_run_006/stage3_repair_packet.json`
- lower-replay packet-first runtime continuation:
- `fixtures/executable_loop_runtime_resume_run_004/repair_packet.json`
  - `fixtures/executable_loop_runtime_resume_run_004/run.json`
- packet-native multi-stage repair-history continuation:
  - `fixtures/executable_loop_compound_continuation_run_008/stage0_repair_packet.json`
  - `fixtures/executable_loop_compound_continuation_run_008/stage1_repair_packet.json`
  - `fixtures/executable_loop_compound_continuation_run_008/stage2_repair_packet.json`
  - `fixtures/executable_loop_compound_continuation_run_008/stage3_repair_packet.json`

These prove:

- blocked continuation can now be expressed without a fake `final_result`
- packet-driven resume can now cross invalid bundle and recovery degradation without restating the full runtime surface each time
- runtime-owned packets can now carry selection and preparation handoff through a nastier continuation contour without making the operator rebuild that context by hand
- runtime-owned packets can now distinguish:
  - repairable compound invalid or degraded states
  - and terminal accepted states that should start a new run instead
- runtime-owned packets can now narrow `required_inputs` to the current repair step instead of flattening the whole future repair debt into one giant input list
- runtime-owned packets can now emit artifact-quality hints that say which existing artifact surface is still stale during continuation
- runtime-owned packets can now emit narrower stale sub-surface ids inside those artifacts
- runtime-owned packets can now carry repair-receipt context so one later packet can say which repair step actually completed on the previous continuation step
- packet-first `resume` can now auto-discover sibling continuation artifacts strongly enough to reach accepted closure with almost no raw flag replay
- packet-first `resume` can now also use stage-aware sibling names like `stage2_repair_packet.json`, `stage2_target_identity.txt`, and `stage2_resume_inputs.json` so multi-step continuation can stay mostly file-driven instead of flag-driven
- repair-receipt context can now carry operator-facing evidence about:
  - the last completed repair step
  - the next exact stale sub-surfaces
  - the next exact required inputs
- repair packets can now carry one explicit repair-history chain across multiple continuation stages instead of only one last-step receipt snapshot
- packet-first `resume` no longer needs temporary unpacked selection and repair-handoff files in the normal continuation path
- one even uglier continuation can now move through:
  - doctor identity pressure
  - partial proof pressure
  - recovery pressure
  - accepted terminal truth
  while still keeping that repair-history chain inside the packet surface
- repair packets can now also expose one smaller embedded continuation core so `resume` can treat the packet as its default continuation contract instead of first depending on wider sibling discovery
- one low-friction canonical continuation run now proves that `resume` can return from `DOCTOR_BLOCKED` to accepted closure from just:
  - `state.json`
  - `repair_packet.json`
- repair packets can now also be rebuilt from one previous packet, so later continuation steps no longer need the operator to restate the full runtime context every time
- one tenth uglier continuation now proves that repeated doctor pressure can survive that packet-chained continuation model and still return to accepted closure

## Current boundary

The packet is richer than the handoff, but still intentionally bounded.

It does not yet try to become:

- a general multi-run plan object
- a broad operator workflow document
- a replacement for all runtime artifacts

It is one continuation packet for one named `resume` path.

The current improvement makes that packet stronger where runtime truth already knew more than the old bounded fields expressed, especially around richer repair receipts, deeper multi-step repair order, and lower-replay operator continuation.

- packet-first continuation now also defaults to fewer root-level side artifacts because the packet can carry the prior receipt and repair-history chain by itself
- packet-first continuation now also has one smaller embedded core so the packet can stay rich without forcing the runtime to consume all of that richness as the default operator contract
- packet-first continuation now also lets later repair packets inherit resume context, repair inputs, and history from the previous packet instead of forcing a full context replay at every step
