# ARTIFACT_CONSISTENCY_RUN_004

Run one mixed corrupt/stale artifact-consistency pressure slice on the tightened kernel.

## Purpose

This is a short proof that the kernel does not need a fully broken artifact surface before it can act honestly.
It should be able to see a mixed contour where:
- one derived artifact is corrupt
- another derived artifact is merely stale
- `state_file` still remains the source of truth

## Canonical artifacts

- `fixtures/executable_loop_minimal_continuation_run_001/state.json`
- `fixtures/executable_loop_minimal_continuation_run_001/starting_repair_packet.json`
- `fixtures/artifact_consistency_run_004/corrupt_report.json`
- `fixtures/artifact_consistency_run_004/mixed.json`

## Expected reading

The consistency record should say:
- `result = INCONSISTENT`
- `dominant_conflict = CORRUPT_DERIVED_ARTIFACT`
- `report -> RESTORE_FROM_CHECKPOINT_OR_REEMIT`
- `repair_packet -> REEMIT_FROM_STATE`

This is the kind of mixed contour that matters in practice:
- not every broken artifact is equally broken
- but the kernel still has to tell us what to trust and what to re-emit
