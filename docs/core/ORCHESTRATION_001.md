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

## What it does

The `orchestrate` command currently runs one bounded path:

1. run doctor
2. write the doctor result back into state
3. assemble the proof bundle
4. write the bundle result back into state
5. compute closure
6. write the closure verdict back into state
7. optionally run refresh after a state-changing event
8. optionally run baseline comparison
9. emit one machine-readable orchestration report
10. optionally emit one canonical worked orchestration artifact

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

That matters because it keeps the canonical worked artifact aligned with the final runtime contour, including post-refresh closure state when refresh is part of the run.

## Current boundaries

The v0 orchestration slice is intentionally narrow.

It does not yet try to:

- replace every slice-specific command
- replace all refresh behavior
- replace all comparison behavior
- become a broad orchestration shell

It only tightens the most important productive contour:

- doctor
- proof bundle
- closure

And now, when explicitly requested:

- refresh after a bounded event
- baseline comparison after the run contour

## Decision rule

Future orchestration growth should improve one of these:

- contour integration
- machine-readable state consistency
- reduction of operator stitching burden

without turning the current v0 path into a broad coordination framework too early.
