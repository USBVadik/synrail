# SYNRAIL_RUNTIME_TRUTH_RECORD_SPEC

## Purpose

Define the minimal record format for a `Synrail` runtime truth snapshot.

This spec exists so current operational truth can be recorded compactly and compared across cycles.

## Required fields

A runtime truth record must include:

- `truth_record_id`
- `trusted_baseline`
- `observed_live_surface`
- `current_target_run_class`
- `support_readiness`
- `exact_retry_readiness`
- `active_blockers`
- `proof_complete_exact_cycle_exists`
- `narrow_next_safe_step`
- `evidence_basis`
- `timestamp`

## Field meanings

### `truth_record_id`

Stable identifier for the snapshot.

### `trusted_baseline`

Must identify the current trusted kernel surface.

### `observed_live_surface`

Must identify the current live/observed runtime surface when relevant.

### `current_target_run_class`

The next run class the product is currently trying to make acceptable.

### `support_readiness`

One of:

- `ACCEPTABLE`
- `NOT_ACCEPTABLE`
- `PARTIAL`

### `exact_retry_readiness`

One of:

- `ACCEPTABLE`
- `NOT_ACCEPTABLE`
- `PARTIAL`

### `active_blockers`

Named blocker classes that are active now, not historically.

### `proof_complete_exact_cycle_exists`

Must be either:

- `YES`
- `NO`

### `narrow_next_safe_step`

One bounded operational next move.

### `evidence_basis`

Must point to the doctor records, evaluation lanes, or recovery protocols from which this snapshot is derived.

## Decision rule

If a runtime truth record includes historical blockers that are no longer active, it is stale.

If it omits the current active blocker, it is misleading.
