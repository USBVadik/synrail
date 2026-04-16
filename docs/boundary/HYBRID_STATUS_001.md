# Hybrid Status 001

## Purpose

State the first machine-readable status reading for the hybrid mode.

This document exists so hybrid policy stops floating between:

- “probably useful”
- “maybe the middle lane”
- “we should keep it around just in case”

and instead stays tied to one explicit measured status.

## Primary artifact

The current hybrid-status artifact now lives at:

- `fixtures/hybrid_status_003.json`

It is built from:

- `fixtures/cost_of_control_003.json`
- `fixtures/executable_loop_run_003/comparison_economics.json`
- `fixtures/executable_loop_hybrid_pressure_run_002/comparison_economics.json`
- `fixtures/executable_loop_hybrid_pressure_run_003/comparison_economics.json`

## Current measured status

The current measured status is:

- `DEMOTED`

The current policy decision is:

- `DEMOTE_HYBRID_FROM_DEFAULT_POLICY`

The current default-policy reading is:

- do not treat hybrid as a default middle mode
- reach for baseline unless one explicit hybrid pressure-test justifies the extra control

## Why it is not promoted

Hybrid is demoted because the current measured evidence is now:

- `evidence_count = 3`
- current verdict mix = `UNCLEAR`, `SYNRAIL_BETTER`, `BASELINE_GOOD_ENOUGH`

That means the class-level signal is no longer just mixed.

It now explicitly includes a hybrid case where:

- the baseline is already good enough

That is enough to remove hybrid from default policy status.

## Why it is not deleted

Hybrid is not deleted because the current evidence also still includes:

- one measured `SYNRAIL_BETTER` hybrid pressure-test

So the current signal is not:

- hybrid was always pointless

The current signal is:

- hybrid can win on some named ambiguities
- but it is too inconsistent to remain a standing policy tier

## What this changes

Current policy should now behave like this:

1. default to the lightweight baseline on mixed-but-not-expensive work
2. only reach for hybrid when one explicit ambiguity makes the baseline feel too loose and there is a good reason to expect the extra control to pay off
3. treat hybrid as an exception pattern rather than a default middle lane

## Promotion requirements

The current artifact sets a re-entry bar:

- add at least one more economics-aware hybrid comparison record
- add one uglier hybrid pressure-test instead of another clean policy example
- only revisit promotion if the class-level measured signal stops containing `BASELINE_GOOD_ENOUGH`

## Decision rule

Until those requirements are met:

- keep hybrid in the repo as a bounded exception pattern
- keep baseline as the default middle-path choice
- do not describe hybrid as a standing third policy mode

That is the shortest honest current reading.
