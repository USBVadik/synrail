# ARTIFACT_CONSISTENCY_RUN_001

## Purpose

Record the first bounded artifact-consistency proof slice for the Synrail kernel.

## Scenario set

This slice now carries two paired readings:

1. one consistent current-state surface
2. one intentionally inconsistent derived report surface

## Artifacts

- `fixtures/artifact_consistency_run_001/consistent.json`
- `fixtures/artifact_consistency_run_002/report_conflict.json`
- `fixtures/artifact_consistency_run_002/inconsistent.json`

## Current proof

Consistent case:

- `result = CONSISTENT`
- `dominant_conflict = ""`

Conflict case:

- one report was modified so its `resulting_state` no longer matched the source-of-truth state
- the consistency helper then returned:
  - `result = INCONSISTENT`
  - `dominant_conflict = RESULTING_STATE_MISMATCH`

## Current reading

This is the first narrow proof that Synrail can now machine-readably distinguish:

- one healthy derived artifact surface
- one stale derived surface that should no longer be trusted without re-emission or checkpoint restore
