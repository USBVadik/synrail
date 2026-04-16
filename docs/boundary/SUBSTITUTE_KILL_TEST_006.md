# SUBSTITUTE_KILL_TEST_006

Run one short substitute-kill slice against a simple baseline after tightening the core around checkpoint, repair termination, artifact consistency, bounded doctor, and thin output.

## Purpose

This is intentionally a narrow check.
We are not trying to prove broad platform superiority here.
We only want to know whether the current minimal packet-first continuation already beats a simple manual baseline on the original pain: avoiding false success while repairing back to accepted closure.

## Canonical artifacts

- `fixtures/substitute_kill_test_006/input_minimal_substitute_v2.json`
- `fixtures/substitute_kill_test_006/input_minimal_synrail_v2.json`
- `fixtures/substitute_kill_test_006/record_minimal.json`
- `fixtures/substitute_kill_test_006/substitute_pressure.json`

## What this slice shows

The compared contour is the minimal identity-repair continuation from `EXECUTABLE_LOOP_MINIMAL_CONTINUATION_RUN_001`.

The simple substitute stack can eventually recover the contour, but it keeps more truth in manual operator memory:
- identity restoration is checklist-driven
- proof basis is thinner
- false-green exposure remains higher

Synrail costs a little more coordination, but it wins on the reason we care about:
- lower false-success risk
- higher proof completeness
- lower repair cost once the contour is already packetized

## Expected reading

The record should land at `SYNRAIL_BETTER`, but only for this narrow minimal continuation wedge.
The test does not claim that simple baselines lose everywhere.
