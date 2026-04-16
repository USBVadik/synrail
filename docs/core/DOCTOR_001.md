# Doctor 001

## Purpose

Define the executable doctor slice for `Synrail`, now strengthened with bounded readiness probes.

This document exists so doctor stops living only as a conceptual readiness surface and starts acting like one machine-readable preflight layer in the executable loop.

## Artifacts

The current doctor slice now lives at:

- `tools/reference/synrail_doctor_v1.py`
- `schemas/doctor_record_v0.schema.json`

## What it does

The current doctor can:

1. evaluate one narrow gate set for the intended run class
2. emit one machine-readable doctor record
3. classify the run as acceptable or not acceptable
4. emit one recommended next safe step
5. optionally write the doctor result back into the run state
6. catch two more expensive false-readiness shapes through targeted pressure-tests
7. block one wrong-target-surface assumption before execution begins

## Current gate set

The executable doctor currently evaluates:

- baseline identity
- clean execution surface
- artifact viability
- helper integrity when required
- credential surface when required
- prompt/task identity for exact retry doctor

And it can now probe several of those from real local conditions instead of only from booleans:

- git cleanliness on a target execution surface
- artifact path parent existence
- helper entrypoint existence
- credential env presence
- credential path validity when env points at a file or directory
- exact prompt identity file presence
- exact task identity match when an expected exact task is supplied
- target identity match when an expected target surface is supplied

The first targeted doctor pressure-test slice for those stronger probes now lives at:

- `docs/core/DOCTOR_PRESSURE_TEST_001.md`
- `docs/core/DOCTOR_PRESSURE_TEST_002.md`

## Why this matters

Without an executable doctor, the rest of the loop has to assume readiness from prose or manual interpretation.

The doctor slice is the first move toward making readiness:

- explicit
- machine-readable
- writable back into the state machine

## Current limitations

The doctor still does not perform:

- automatic environment probing
- deep helper contamination discovery
- provider reachability tests
- richer multi-step readiness diagnosis

It is intentionally a small executable readiness layer, not the final doctor runtime.

The point of current doctor work is not breadth.

It is to reduce a few expensive false-readiness decisions more honestly.

## Decision rule

Future doctor work should strengthen:

- pre-run readiness truth
- clearer blocking failure classes
- better integration with the executable state loop

without turning doctor into a broad diagnostics platform too early.
