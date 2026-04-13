# OBSERVABILITY_RUN_001

## Purpose

Record the first runtime-emitted observability artifact for a blocked continuation contour.

## Scenario

The runtime starts from one repair packet that already says:

- `TERMINATE / NO_PROGRESS_DETECTED`

The next `resume` then blocks immediately at `resume` and emits one observability record.

## Artifacts

- `fixtures/observability_run_001/report.json`
- `fixtures/observability_run_001/repair_packet.json`
- `fixtures/observability_run_001/repair_receipt.json`
- `fixtures/observability_run_001/observability.json`

## Current proof

The emitted observability record now captures:

- one state transition log
- one repair-attempt log with `3` attempts in history
- one rejection log naming `NO_PROGRESS_DETECTED`
- one sanitized session export with no secret values

## Current reading

This is the first narrow proof that Synrail can now emit one bounded observability surface directly from runtime, not only reconstruct that view later by hand.
