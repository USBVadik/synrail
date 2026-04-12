# Repair Handoff 001

## Purpose

Define the first machine-readable repair handoff slice for `Synrail` continuation.

This document exists so continuation from a blocked, partial, or degraded contour stops depending only on operator memory.

## Artifacts

The first repair handoff slice now lives at:

- `tools/reference/synrail_repair_handoff_v0.py`
- `schemas/repair_handoff_v0.schema.json`

The first canonical blocked handoff fixture now lives at:

- `fixtures/repair_handoff_run_001/repair_handoff.json`
- `fixtures/repair_handoff_run_001/report.json`
- `fixtures/repair_handoff_run_001/run.json`

The first canonical ugly continuation handoff set now lives at:

- `fixtures/executable_loop_compound_continuation_run_001/stage1_handoff.json`
- `fixtures/executable_loop_compound_continuation_run_001/stage2_handoff.json`
- `fixtures/executable_loop_compound_continuation_run_001/run.json`

## What it does

The handoff slice reads one current `run_state` and emits:

- `from_state`
- `blocking_reason`
- `continuation_allowed`
- `continuation_entrypoint`
- `resumability`
- `required_inputs`
- `runtime_defaults`
- `next_safe_step`
- `repair_policy`
- `artifact_quality_hints`

That output is intentionally narrow.

It does not try to solve the repair.
It names the missing continuation contract clearly enough for the runtime and the operator to stay aligned.

It now also names:

- which repair step is current
- which existing artifact surface is still stale
- and whether the current contour is repairable at all or should follow a non-resumable next step instead

## Current mappings

The current handoff can already name required continuation inputs for:

- exact prompt and task identity repair after `DOCTOR_BLOCKED`
- final result repair after invalid or missing proof bundle inputs
- readback and scenario proof repair after `PROOF_BUNDLE_PARTIAL`
- recovery completion plus reverification after `RECOVERY_PENDING`
- target identity, clean-surface confirmation, helper path, artifact path, and credential-surface repair when doctor failure classes require them

When recovery repair is part of the handoff, the slice also emits bounded runtime defaults for:

- `RECOVERY_EVENT`
- `refresh_use_bundle = true`
- `refresh_use_closure = true`

That matters because continuation can now carry some refresh truth forward without restating the same runtime scaffolding by hand.

## First blocked handoff reading

The first blocked repair handoff run now records:

- `from_state = DOCTOR_BLOCKED`
- `blocking_reason = DOCTOR_NOT_GREEN`
- `resumability.family = REPAIRABLE_DOCTOR_BLOCKED`
- required inputs:
  - `prompt_identity`
  - `task_identity`

When `resume` is attempted without those inputs, the runtime now blocks explicitly at:

- `stopping_stage = repair_handoff`
- `reason = CONTINUATION_INPUTS_MISSING`

Observed blocked reading:

- `BLOCKED | repair_handoff | CONTINUATION_INPUTS_MISSING | DOCTOR_BLOCKED | CLAIMED_NOT_ACCEPTED`

## Expanded handoff reading

The current handoff layer now also proves one non-resumable family:

- `fixtures/executable_loop_runtime_non_resumable_run_001/repair_handoff.json`

That handoff records:

- `resumability.family = NOT_RESUMABLE_SELECTION_BLOCKED`
- `repair_policy.policy_type = NON_RESUMABLE_NEXT_STEP`
- `repair_policy.next_step_id = switch_to_lighter_mode`
- artifact-quality hint:
  - `mode_selection_receipt`

The current handoff layer also now supports one stricter multi-step compound family:

- `fixtures/executable_loop_compound_continuation_run_005/stage0_repair_handoff.json`
- `fixtures/executable_loop_compound_continuation_run_005/stage1_repair_handoff.json`
- `fixtures/executable_loop_compound_continuation_run_005/stage2_repair_handoff.json`

Those prove:

- required inputs now narrow to the current repair step
- the repair order is explicit
- the handoff can point to the stale artifact surface that still needs repair

## Why this matters

This is the first time `Synrail` can say, in one machine-readable artifact:

- what state continuation is coming from
- why that state is still non-green
- whether that state is repairable or terminal
- which concrete inputs are missing before honest continuation can resume

That is stronger than only having:

- one next-safe-step string
- one repaired fixture family
- one operator remembering what to pass next

## Current reading

The shortest honest reading is:

- `Synrail` now has one first-class repair handoff layer
- the runtime can now block continuation at `repair_handoff` when required inputs are still missing
- the same handoff layer can now also say when a continuation family is truly not resumable
- and it can now point to which artifact surface is still stale while multi-step repair is unfolding
- named continuation is starting to look like a real product contour instead of only a repaired evidence pattern
