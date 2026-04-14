# ARTIFACT_CONSISTENCY_001

## Purpose

Define one first explicit artifact-consistency invariant for the Synrail kernel.

This document exists to stop Synrail from behaving like one rich artifact ecology without one clear source of truth.

## Source of truth

For the current kernel tranche, the machine-readable `state_file` is the source of truth.

Derived runtime artifacts are authoritative only if they remain consistent with that state.

## Derived artifacts

The current bounded consistency model treats these as derived surfaces:

- `report`
- `orchestration`
- `run`
- `repair_packet`
- `repair_handoff`
- `repair_receipt`

## Invariant

A derived artifact is consistent only if:

- `run_id` matches the source state
- `task_class` matches the source state
- any state-carrying field refers to the same current state as the source state
- the derived artifact is still readable and not corrupt

## Conflict precedence

Current precedence is:

1. `CORRUPT_DERIVED_ARTIFACT`
2. `RUN_ID_MISMATCH`
3. `TASK_CLASS_MISMATCH`
4. `DERIVED_FROM_STATE_MISMATCH`
5. `RESULTING_STATE_MISMATCH`

## Update model

The current bounded rule is:

- current-state artifacts must be treated as one atomic-or-rollbackable derived surface
- spine writes current-state artifacts with atomic replace instead of in-place partial overwrite

Meaning:

- if one derived artifact disagrees with the source state, that derived surface must be re-emitted or restored from a verified checkpoint
- if one derived artifact is corrupt, the kernel must tell the operator to restore it from a verified checkpoint or re-emit it from the source state
- the kernel must not silently trust stale derived artifacts just because they are machine-readable

## Current reading

The shortest honest reading is:

- Synrail now treats `state_file` as the current source of truth
- derived runtime artifacts are useful only while they remain consistent with that source state
- corrupt derived artifacts now also count as first-class consistency failures
- spine can now emit one runtime-owned artifact-consistency record after writing the derived surface
- consistency failures can now also feed one explicit restore-or-reemit recovery bridge when a matching verified checkpoint exists
- artifact richness without consistency is not kernel maturity
