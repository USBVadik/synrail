# Governed Path Cost Reduction 001

## Purpose

Record the first measured cost-reduction slice inside the winning governed path.

This document exists so preparation is judged not only as a cleaner contour, but as a bounded economic improvement inside the contour that already earns its weight.

## Artifacts

The first governed-path cost delta slice now lives at:

- `tools/reference/synrail_governed_cost_delta_v0.py`
- `schemas/governed_path_cost_input_v0.schema.json`
- `schemas/governed_path_cost_delta_v0.schema.json`

The first measured record now lives at:

- `fixtures/governed_path_cost_delta_001.json`

Its source inputs now live at:

- `fixtures/governed_path_cost_input_unprepared_001.json`
- `fixtures/governed_path_cost_input_prepared_001.json`

## Scenario

- scenario id: `GOVERNED_PATH_COST_001`
- scenario class: `proof_sensitive_governed_path`
- task class: `bounded_router_trigger_fix`

The narrow question here is:

- does preparation reduce operator tax inside the governed path without weakening the safety surface?

## Current measured reading

The first bounded record says:

- verdict = `PREPARATION_REDUCES_GOVERNED_PATH_COST`

Measured delta:

- `5` operator minutes reduced
- `1` intervention reduced
- `1` repair cycle reduced
- `7` closure-latency minutes reduced
- first bundle status improved from non-complete to `COMPLETE`
- first-pass closure readiness improved
- no safety regression observed

## Why this matters

This is the first economic sign that governed-path preparation is not only:

- better organized
- easier to explain

but also:

- cheaper in a bounded way inside the contour that we already think is worth paying for

## Current reading

The shortest honest reading is:

- preparation is now runtime-integrated
- preparation now also has one bounded governed-path cost win
- this is still only one internal economic slice, not yet a broad governed-path cost proof
