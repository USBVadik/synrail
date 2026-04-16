# CONTINUATION_ADOPTION_001

## Purpose

Measure whether packet-first continuation is getting easier to adopt without losing its ugly runtime truth.

## Artifacts

The first continuation-adoption slice now lives at:

- `tools/reference/synrail_continuation_adoption_v0.py`
- `tools/reference/synrail_continuation_adoption_delta_v0.py`
- `schemas/continuation_adoption_record_v0.schema.json`
- `schemas/continuation_adoption_delta_v0.schema.json`
- `fixtures/continuation_adoption_run_001.json`
- `fixtures/continuation_adoption_run_002.json`
- `fixtures/continuation_adoption_delta_001.json`

## What it compares

Current delta compares:

1. `EXECUTABLE_LOOP_COMPOUND_CONTINUATION_RUN_009`
- packet-first repeated-doctor baseline

2. `EXECUTABLE_LOOP_COMPOUND_CONTINUATION_RUN_010`
- packet-chained minimal-core repeated-doctor continuation

## Current honest result

The current delta says:

- `verdict = FRICTION_REDUCED_WITHOUT_TRUTH_LOSS`
- `side_files_reduced = 2`
- `packet_only_entry_gained = true`
- `doctor_pressure_preserved = true`
- `accepted_terminal_truth_preserved = true`

That means:

- the newer contour still carries repeated doctor pressure
- the newer contour still reaches accepted terminal truth
- but the visible root continuation side-file tax is lower

## Why this matters

This is the first machine-readable answer to a now-central product question:

- is continuation getting easier to use, or only more internally complete?

The current slice says at least one ugly contour is now lighter at the root entry without flattening the truth pressure that made the contour interesting in the first place.
