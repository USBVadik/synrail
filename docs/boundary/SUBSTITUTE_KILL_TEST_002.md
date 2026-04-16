# SUBSTITUTE_KILL_TEST_002

## Purpose

Pressure-test the tightened kernel against simpler substitute stacks after checkpoint, repair termination, artifact consistency, doctor sharpening, observability, reproducibility, and packet-first continuation compression.

This slice asks a better question than `Synrail vs chaos`:

- where is the tightened kernel materially better than real substitute stacks a team could plausibly use instead?

## Artifacts

The second substitute-pressure slice now lives at:

- `tools/reference/synrail_substitute_harness_v0.py`
- `tools/reference/synrail_substitute_pressure_v0.py`
- `fixtures/substitute_kill_test_002/record_convergence.json`
- `fixtures/substitute_kill_test_002/record_second_operator.json`
- `fixtures/substitute_kill_test_002/record_weak.json`
- `fixtures/substitute_kill_test_002/substitute_pressure.json`

## Substitute stacks tested

1. `manual_retry_loop_with_notes`
2. `runbook_resume_checklist`
3. `bounded_patch_validation_loop`

## Current honest result

The current pressure record says:

- `SYNRAIL_BETTER = 2`
- `SUBSTITUTE_GOOD_ENOUGH = 0`
- `UNCLEAR = 1`

Winning tightened-kernel wedges:

- `SUBSTITUTE_SCENARIO_CONVERGENCE_002`
  - `Synrail` now beats a manual retry loop because it stops on `NO_PROGRESS_DETECTED` instead of letting the same blind repair step keep replaying
- `SUBSTITUTE_SCENARIO_SECOND_OPERATOR_002`
  - `Synrail` now beats a runbook-style resume checklist because packet-first continuation keeps next-step and required-input truth explicit with less author-memory dependence

Still non-decisive:

- `SUBSTITUTE_SCENARIO_WEAK_002`
  - the lightweight bounded patch loop is still not cleanly killed on the weak path

## Why this matters

This is the first substitute slice that leans on a tightened kernel rather than only on richer continuation vocabulary.

So the useful result is not just that `Synrail` wins twice.

The useful result is:

- the wins are now attached to convergence control and second-operator followability
- those are closer to product necessity than internal completeness alone

## Current reading

The shortest honest reading is:

- the tightened kernel now has one clearer substitute edge on stalled repair-loop control
- it also has one clearer substitute edge on packet-first second-operator continuation
- the weak path still remains non-decisive against a light substitute stack
- so necessity is sharpening, but it is still wedge-shaped rather than universal
