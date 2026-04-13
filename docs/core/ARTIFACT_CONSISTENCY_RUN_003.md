# ARTIFACT_CONSISTENCY_RUN_003

## Purpose

Record the next bounded artifact-consistency proof slice for `Synrail`.

This tranche proves two narrower things:

- one corrupt derived artifact is now detected as a first-class consistency failure
- the spine can also emit one runtime-owned consistency record after writing a derived surface

## Artifacts

- corrupt derived artifact:
  - `fixtures/artifact_consistency_run_003/corrupt_report.json`
  - `fixtures/artifact_consistency_run_003/corrupt.json`
- runtime-emitted consistency record:
  - `fixtures/artifact_consistency_run_003/runtime_emitted.json`

## Current reading

- corrupt derived surfaces are no longer treated like mere stale artifacts
- runtime-owned derived outputs can now also self-report consistency against the source-of-truth state
