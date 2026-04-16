# OPERATOR_RENDER_001

## Purpose

Define the first strictly derived human-readable render for the operator layer.

This slice exists to do one bounded thing:

- make `operator-brief` and `operator-brief-chain` easier to read quickly

without introducing a new source of truth.

## Artifacts

The render slice now lives at:

- `tools/reference/synrail_operator_render_v0.py`
- `fixtures/operator_render_run_001/operator_render.md`
- `fixtures/operator_render_run_002/operator_render.md`

## What it does

The render helper reads either:

- one `operator_brief_record_v0`
- or one `operator_brief_chain_record_v0`

and writes one small markdown summary.

It preserves:

- primary action
- next safe step
- current step
- required inputs
- termination reading
- final action on chain contours

It does not replace:

- `state`
- `report`
- `repair_packet`
- `operator_brief`
- `operator_brief_chain`

## Canonical readings

The first render is built from the repairable recovery brief:

- `fixtures/operator_brief_run_002/operator_brief.json`
- output:
  - `fixtures/operator_render_run_001/operator_render.md`

That render keeps the key reading compact:

- `primary_action = REPAIR_CURRENT_STEP`
- `current_step_id = complete_recovery_reverification`
- required inputs:
  - `refresh_recovery_complete`
  - `refresh_reverification_complete`

The second render is built from the stop-ending operator chain:

- `fixtures/operator_brief_chain_run_002/operator_brief_chain.json`
- output:
  - `fixtures/operator_render_run_002/operator_render.md`

That render keeps the full operator progression compact:

- repair proof
- repair doctor pressure
- stop and start a new run after `MAX_REPAIR_ATTEMPTS`

## Why this matters

This is the first operator-layer move that is explicitly for human reading.

That only makes sense now because the runtime-owned truth surfaces already exist underneath it.

So the render layer stays:

- derived
- bounded
- disposable if it stops helping

rather than becoming a parallel runtime language.

## Current reading

The shortest honest reading is:

- Synrail now has one small human-readable render layer for operator briefs and chains
- it improves scanability of the existing operator summaries
- and it does so without adding a new machine-readable control surface
