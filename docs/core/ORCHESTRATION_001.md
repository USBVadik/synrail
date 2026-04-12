# Orchestration 001

## Purpose

Define the first bounded orchestration pass for the executable `Synrail` stack.

This document exists so the kernel loop stops looking only like a set of cooperating slices and starts acting more like one practical control contour.

## Artifacts

The first bounded orchestration slice now lives at:

- `tools/reference/synrail_spine_v0.py`
- `tools/reference/synrail_cli_v0.py`
- `tools/reference/synrail_runtime_v0.py`
- `schemas/orchestration_report_v0.schema.json`
- `schemas/worked_orchestration_artifact_v0.schema.json`
- `schemas/canonical_run_artifact_v0.schema.json`

## What it does

The `orchestrate` command currently runs one bounded path:

1. attest the target surface into state
2. run doctor
3. write the doctor result back into state
4. confirm exact-task integrity into state
5. advance execution readiness for fresh runs
6. optionally absorb one mode-selection receipt before runtime progression starts
7. optionally emit one governed-path proof plan
8. assemble the proof bundle
9. optionally emit one preparation receipt comparing the plan to the assembled bundle
10. write the bundle result back into state
11. compute closure
12. write the closure verdict back into state
13. optionally run refresh after a state-changing event
14. optionally run baseline comparison
15. emit one machine-readable orchestration report
16. optionally emit one canonical worked orchestration artifact
17. optionally emit one primary canonical run artifact

When `resume` is used, that same contour can now also:

- load one repair handoff contract
- block explicitly at `repair_handoff` if the required continuation inputs are still missing
- absorb bounded runtime defaults from the handoff when recovery repair requires refresh reconciliation

The bounded orchestration contour now lives in:

- `tools/reference/synrail_spine_v0.py`

The surrounding layers now act as:

- `tools/reference/synrail_cli_v0.py`
  as the terminal entry layer
- `tools/reference/synrail_runtime_v0.py`
  as a compatibility wrapper for the same spine-driven contour

## Why this matters

Before this pass, the repo had executable slices, but the operator still had to stitch most of the contour together manually.

The orchestration pass is the first move toward:

- one bounded runtime path
- less manual contour assembly
- one summary artifact for what happened in the run

The first canonical worked orchestration envelope now lives at:

- `fixtures/executable_loop_run_001/orchestration.json`

The CLI can now emit that envelope directly through the orchestration path, instead of requiring a hand-assembled artifact after the fact.

The same contour can now also absorb one preparation-aware strong-path selection receipt directly through:

- `--mode-selection-receipt`

When that receipt says:

- `selected_mode = FULL_GOVERNED_PATH`
- `selected_with_preparation = true`

the runtime can now derive:

- `plan.json`
- `preparation_receipt.json`

without separately restating those output paths on the CLI.

When that receipt instead says:

- `selected_mode = LIGHTWEIGHT_BASELINE`
- or `selected_mode = HYBRID_EXCEPTION`

the governed orchestration path now blocks at `selection` instead of silently ignoring the lighter policy choice.

The terminal layer can now also enter that same contour through:

- `resume`

which records:

- `resume_applied`
- `resume_from_state`

on the resulting runtime artifacts.

That same continuation path can now also carry one explicit repair handoff artifact, which matters because the runtime can now say:

- which state continuation is resuming from
- which inputs are still missing
- which bounded refresh defaults should carry forward during recovery repair

That continuation path is now proven on:

- one partial-proof repair family
- one degraded recovery repair family
- one doctor-blocked readiness repair family
- one blocked repair-handoff attempt that now stops explicitly at `repair_handoff`
- one ugly compound continuation that now crosses readiness repair, proof repair, and recovery repair through staged handoffs plus named `resume`

That matters because it keeps the canonical worked artifact aligned with the final runtime contour, including post-refresh closure state when refresh is part of the run.

The spine can now also emit one primary canonical run artifact that compresses:

- the report reading
- the resulting state reading
- the worked-envelope reading

That artifact is now the best single machine-readable starting point for an internal run reading.

Blocked contours can now emit the same primary run artifact shape too, which matters because it keeps blocked runs on the same truth surface as accepted or partial runs.

The first canonical blocked fixture for that surface now lives at:

- `fixtures/executable_loop_blocked_run_001/run.json`

The first canonical re-entry fixture for that surface now lives at:

- `fixtures/executable_loop_reentry_run_001/run.json`

The first canonical partial-proof re-entry fixture for that surface now lives at:

- `fixtures/executable_loop_partial_reentry_run_001/run.json`

The first canonical degraded re-entry fixture for that surface now lives at:

- `fixtures/executable_loop_degraded_reentry_run_001/run.json`

The first canonical selected-prepared governed fixture for that same surface now lives at:

- `fixtures/executable_loop_selected_prepared_run_001/run.json`

The spine-driven contour now also emits explicit blocked state lanes instead of leaving the main failures only in report fields:

- `DOCTOR_BLOCKED`
- `PROOF_BUNDLE_PARTIAL`
- `PROOF_BUNDLE_INVALID`

It now also emits explicit blocked-transition readings when a contour step is denied, including:

- all applicable blockers
- one dominant blocker
- one resulting blocked state / next safe step reading

## Current boundaries

The v0 orchestration slice is intentionally narrow.

It does not yet try to:

- replace every slice-specific command
- replace all refresh behavior
- replace all comparison behavior
- become a broad orchestration shell

It only tightens the most important productive contour:

- doctor
- optional preparation
- proof bundle
- closure

And now, when explicitly requested:

- one mode-selection receipt handoff into the governed runtime contour
- one named runtime continuation contour from a non-green starting state
- one machine-readable repair handoff layer around that continuation contour
- one doctor-blocked runtime continuation contour from an early readiness-failure state
- one governed-path proof plan plus one preparation receipt
- refresh after a bounded event
- baseline comparison after the run contour
- economics-aware comparison when the supplied inputs use the `v1` comparison schema

## Decision rule

Future orchestration growth should improve one of these:

- contour integration
- machine-readable state consistency
- reduction of operator stitching burden

without turning the current v0 path into a broad coordination framework too early.
