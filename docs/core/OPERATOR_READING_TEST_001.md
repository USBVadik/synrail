# OPERATOR_READING_TEST_001

## Purpose

Record the first less-curated operator reading pass for the human-readable render layer.

This slice exists to answer one narrow product question:

- can a second operator still follow the repeated-doctor stop decision when reading the derived render instead of only the raw operator brief?

## Artifacts

The canonical slice now lives at:

- `tools/reference/synrail_operator_reading_v0.py`
- `schemas/operator_reading_record_v0.schema.json`
- `fixtures/operator_render_run_003/operator_render.md`
- `fixtures/operator_reading_test_001/operator_reading.json`

## Scenario

This slice reuses the less-curated repeated-doctor contour from:

- `core/SECOND_OPERATOR_TEST_002.md`

Source brief:

- `fixtures/operator_brief_run_001/operator_brief.json`

Derived render:

- `fixtures/operator_render_run_003/operator_render.md`

The expected operator truth stays the same:

- `reason = DOCTOR_NOT_GREEN`
- `primary_action = STOP_AND_START_NEW_RUN`
- `current_step_id = restore_readiness_truth`
- `termination_reason = MAX_REPAIR_ATTEMPTS`

## Current result

The reading record says:

- `packet_only_entry = true`
- `requires_author_intuition = false`
- `missing_markers = []`
- `verdict = FOLLOWABLE_WITH_RENDER`

That means the human-readable render still preserves the stop decision on the less-curated repeated-doctor contour.

## Why this matters

This is a better test than only checking whether the render is shorter.

It checks whether the layer still carries the exact operator decision that matters most on an exhausted contour:

- stop replaying
- start a new run

## Current reading

The shortest honest reading is:

- the render layer now survives one less-curated repeated-doctor reading pass
- it still preserves the stop-and-restart decision and its required inputs
- so the render currently looks usable not only on cleaner repairable cases but also on one harsher operator stop case
