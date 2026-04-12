# Hybrid Status 001

## Purpose

State the first machine-readable status reading for the hybrid mode.

This document exists so hybrid policy stops floating between:

- “probably useful”
- “maybe the middle lane”
- “we should keep it around just in case”

and instead stays tied to one explicit measured status.

## Primary artifact

The first hybrid-status artifact now lives at:

- `fixtures/hybrid_status_001.json`

It is built from:

- `fixtures/cost_of_control_001.json`
- `fixtures/executable_loop_run_003/comparison_economics.json`

## Current measured status

The current measured status is:

- `PROVISIONAL`

The current policy decision is:

- `KEEP_HYBRID_SECONDARY`

The current default-policy reading is:

- keep hybrid secondary and explicit
- do not expand hybrid semantics yet
- do not let mixed answers alone auto-select hybrid

## Why it is not promoted

Hybrid is not promoted because the current measured evidence is still too thin:

- `evidence_count = 1`
- current verdict mix = `UNCLEAR`

That is enough to keep hybrid alive as a bounded option.

It is not enough to treat hybrid as a settled default middle lane.

## Why it is not fully demoted

Hybrid is not fully demoted because the current evidence does not show:

- `BASELINE_GOOD_ENOUGH`

on the hybrid scenario class.

So the current signal is not:

- hybrid was tested and clearly lost

The current signal is:

- hybrid was tested once and still did not earn promotion

## What this changes

Current policy should now behave like this:

1. default to the lightweight baseline on mixed-but-not-expensive work
2. only reach for hybrid when one explicit ambiguity makes the baseline feel too loose
3. keep hybrid bounded and secondary until another measured pressure-test improves the signal

## Promotion requirements

The current artifact sets a simple promotion bar:

- add at least one more economics-aware hybrid comparison record
- add one uglier hybrid pressure-test instead of another clean policy example
- only promote hybrid if the measured verdict stops staying unclear

## Decision rule

Until those requirements are met:

- keep hybrid in the repo
- keep hybrid explicit
- keep hybrid secondary

That is the shortest honest current reading.
