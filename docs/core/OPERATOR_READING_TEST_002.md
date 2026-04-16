# OPERATOR_READING_TEST_002

## Purpose

Record the second operator reading pass on a repairable recovery contour.

This slice exists to complement the first reading test:

- the first one proved the render preserves a stop decision
- this one proves the render also preserves an active repair decision

## Artifacts

The canonical slice now lives at:

- `fixtures/second_operator_test_003/second_operator.json`
- `fixtures/operator_render_run_001/operator_render.md`
- `fixtures/operator_reading_test_002/operator_reading.json`

Source brief:

- `fixtures/operator_brief_run_002/operator_brief.json`

## Scenario

This slice uses the repairable recovery contour from:

- `fixtures/executable_loop_compound_continuation_run_010/stage2_run.json`

Expected operator truth:

- `reason = RECOVERY_REVERIFICATION_INCOMPLETE`
- `primary_action = REPAIR_CURRENT_STEP`
- `current_step_id = complete_recovery_reverification`
- required inputs:
  - `refresh_recovery_complete`
  - `refresh_reverification_complete`

## Current result

The paired records now say:

- second-operator:
  - `verdict = FOLLOWABLE_BY_SECOND_OPERATOR`
- operator-reading:
  - `verdict = FOLLOWABLE_WITH_RENDER`
  - `missing_markers = []`
  - `packet_only_entry = true`
  - `requires_author_intuition = false`

## Why this matters

The render layer is only worth keeping if it helps in both operator modes:

- stop this contour
- repair this contour

This second reading test now shows that the render still preserves the exact repair step, next safe step, and required inputs on a repairable recovery path.

## Current reading

The shortest honest reading is:

- the render layer now survives one repairable less-curated reading pass as well as one stop-ending pass
- so the current bounded evidence says the layer is useful in both main operator modes we care about
