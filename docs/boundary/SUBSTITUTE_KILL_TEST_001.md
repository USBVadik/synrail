# SUBSTITUTE_KILL_TEST_001

## Purpose

Pressure-test `Synrail` against simple substitute stacks rather than only against one abstract baseline.

## Artifacts

The first substitute-pressure slice now lives at:

- `tools/reference/synrail_substitute_harness_v0.py`
- `tools/reference/synrail_substitute_pressure_v0.py`
- `schemas/comparison_input_v2.schema.json`
- `schemas/substitute_comparison_record_v0.schema.json`
- `schemas/substitute_pressure_record_v0.schema.json`
- `fixtures/substitute_kill_test_001/substitute_pressure.json`

## Substitute stacks tested

1. `temp_clone_strict_validation`
2. `ci_approval_checklist`
3. `bounded_patch_validation_loop`

## Current honest result

The current pressure record says:

- `SYNRAIL_BETTER = 2`
- `SUBSTITUTE_GOOD_ENOUGH = 0`
- `UNCLEAR = 1`

That means:

- `Synrail` already looks materially stronger than a temp-clone strict-validation stack on the strong wedge
- `Synrail` already looks materially stronger than a CI plus approval plus checklist stack on the compound continuation wedge
- the bounded patch substitute on the weak path is still not cleanly killed yet

So this slice is useful precisely because it is not a total victory narrative.

## Why this matters

This is the first move from:

- `Synrail vs abstract baseline`

toward:

- `Synrail vs concrete substitute stacks`

That is a better product question because it asks whether the kernel is necessary against the things a real team would actually use instead.

## Current reading

The shortest honest reading is:

- the strong wedge now has one first substitute-kill signal
- the compound continuation wedge now has one second substitute-kill signal
- the weak path still remains non-decisive against a lighter substitute stack
- so the product is starting to prove necessity against substitutes, but not universally yet
