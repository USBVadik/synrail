# REPRODUCIBILITY_TEST_001

## Purpose

Record the first short reproducibility pressure-test for the tightened `Synrail` kernel.

This slice exists to prove one narrow but important claim:

- repeated continuation runs can preserve the same key runtime truth rather than drifting across retries

## Artifacts

The canonical reproducibility slice now lives at:

- `tools/reference/synrail_reproducibility_v0.py`
- `schemas/reproducibility_record_v0.schema.json`
- `fixtures/repair_convergence_run_001/run.json`
- `fixtures/repair_convergence_run_002/run.json`
- `fixtures/reproducibility_test_001/reproducibility.json`

## Scenario

Two independent runs use the same stalled repair-loop contour:

- starting state: `DOCTOR_BLOCKED`
- same active repair step: `restore_readiness_truth`
- same repeated lack of new continuation inputs
- same bounded termination rule: `NO_PROGRESS_DETECTED`

The question is intentionally small:

- does the kernel preserve the same blocking, repair-history, and next-step truth across repeated runs?

## Current result

The reproducibility record says:

- `verdict = REPRODUCIBLE_ON_KEY_TRUTH`
- `mismatches = []`

Key preserved truth includes:

- `result = BLOCKED`
- `stopping_stage = resume`
- `reason = NO_PROGRESS_DETECTED`
- `resulting_state = DOCTOR_BLOCKED`
- `repair_history_termination_reason = NO_PROGRESS_DETECTED`
- `repair_packet_family = REPAIRABLE_DOCTOR_BLOCKED`

## Why this matters

This is not broad determinism proof.

It is the first bounded sign that the tightened kernel can replay one important non-green contour without silently mutating its key truth surfaces.

## Current reading

The shortest honest reading is:

- one repeated stalled-loop contour now reproduces the same blocking and termination truth
- reproducibility is still only shown on a narrow kernel slice, not across every runtime family
