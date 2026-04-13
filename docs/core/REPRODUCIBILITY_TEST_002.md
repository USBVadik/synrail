# REPRODUCIBILITY_TEST_002

## Purpose

Record one less-curated reproducibility pressure-test on an uglier packet-first continuation contour.

This slice exists to prove a narrower but harsher kernel claim:

- repeated replays of the same repeated-doctor continuation step preserve the same bounded stop truth

## Artifacts

The canonical slice now lives at:

- `fixtures/second_operator_test_002/starting_run.json`
- `fixtures/reproducibility_test_002/starting_run.json`
- `fixtures/reproducibility_test_002/reproducibility.json`

## Scenario

Two independent replays use the same ugly continuation entry:

- `state = DOCTOR_BLOCKED`
- packet family: `REPAIRABLE_COMPOUND`
- required step input: `target_identity_file`
- repeated doctor pressure remains active

Both replays stop at the same bounded runtime truth:

- `BLOCKED | doctor | DOCTOR_NOT_GREEN | DOCTOR_BLOCKED`
- repair-history now also terminates with `MAX_REPAIR_ATTEMPTS`

## Current result

The reproducibility record says:

- `verdict = REPRODUCIBLE_ON_KEY_TRUTH`
- `mismatches = []`

Key preserved truth includes:

- `result = BLOCKED`
- `stopping_stage = doctor`
- `reason = DOCTOR_NOT_GREEN`
- `repair_history_termination_reason = MAX_REPAIR_ATTEMPTS`
- `repair_packet_family = REPAIRABLE_COMPOUND`

## Why this matters

This is harsher than the first reproducibility slice because the repeated contour carries:

- repeated doctor pressure
- mixed stale proof and recovery pressure
- bounded stop instead of a clean repaired acceptance

## Current reading

The shortest honest reading is:

- one uglier repeated-doctor continuation step now reproduces the same bounded block and termination truth across repeated replays
- reproducibility is still pressure-tested only on narrow kernel slices, not yet on broader external-ish usage
