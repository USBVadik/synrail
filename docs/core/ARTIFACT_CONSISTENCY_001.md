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

## Conflict precedence

Current precedence is:

1. `RUN_ID_MISMATCH`
2. `TASK_CLASS_MISMATCH`
3. `DERIVED_FROM_STATE_MISMATCH`
4. `RESULTING_STATE_MISMATCH`

## Update model

The current bounded rule is:

- current-state artifacts must be treated as one atomic-or-rollbackable derived surface

Meaning:

- if one derived artifact disagrees with the source state, that derived surface must be re-emitted or restored from a verified checkpoint
- the kernel must not silently trust stale derived artifacts just because they are machine-readable

## Current reading

The shortest honest reading is:

- Synrail now treats `state_file` as the current source of truth
- derived runtime artifacts are useful only while they remain consistent with that source state
- artifact richness without consistency is not kernel maturity
