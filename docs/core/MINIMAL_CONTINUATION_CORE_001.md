# Minimal Continuation Core 001

## Purpose

Define the smallest continuation contract that still preserves `Synrail`'s real value.

This document exists so continuation can stay truth-disciplined without forcing the operator to reopen the whole packet grammar on every repair step.

## Artifact

The current minimal continuation core now lives inside:

- `schemas/repair_packet_v0.schema.json`
- `tools/reference/synrail_repair_packet_v0.py`
- `fixtures/executable_loop_minimal_continuation_run_001/starting_repair_packet.json`

## What the core keeps

The embedded `continuation_core` keeps only the fields the runtime and operator most need to continue honestly:

- resumability status and family
- current repair step id
- required and still-missing inputs
- next-step stale sub-surface ids
- operator focus
- next safe step
- repair-history chain length
- whether the packet already supplies resume context, repair inputs, and output defaults
- whether sibling discovery is still needed at all

## What it deliberately does not try to be

It is not:

- a replacement for the full repair packet
- a full workflow plan
- a broad multi-run repair object

It is the minimal lovable continuation contract inside the larger packet.

## Why this matters

This is the compression move that keeps continuation from turning into a complexity tax.

The operator can still inspect the richer packet when needed, but the runtime can now treat one compact continuation core as the default contract for packet-first `resume`.

## Current proof point

The first canonical proof point is:

- `core/EXECUTABLE_LOOP_MINIMAL_CONTINUATION_RUN_001.md`

That run proves that one `DOCTOR_BLOCKED` contour can now resume back to accepted closure from:

- `state.json`
- `repair_packet.json`

without relying on extra root-level repair handoff, repair receipt, prompt identity, task identity, or resume-input side artifacts.
