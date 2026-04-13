# CHECKPOINT_001

## Purpose

Define checkpoint as a first-class kernel capability for Sprint 01.

Checkpoint here does not mean “save some files somewhere”.

It means:

- create one bounded safe point
- verify that safe point
- restore from that safe point
- roll back the restore if restore verification fails

## Why checkpoint belongs in the core

Checkpoint now belongs in the minimal kernel because it strengthens the original product pain directly:

- expensive false closure
- dangerous repair loops
- risky continuation after non-green state

Without a verified safe point, continuation can still be disciplined but operationally fragile.

With a verified safe point, the kernel can:

- stop before a dangerous repair move
- preserve one known-good truth surface
- return to that surface if a restore or repair step goes bad

## Artifact

The checkpoint contract for this sprint is:

- `schemas/checkpoint_record_v0.schema.json`

The first runtime proof points now live at:

- `docs/core/CHECKPOINT_RUN_001.md`
- `docs/core/CHECKPOINT_RUN_002.md`

The runtime implementation will later emit one machine-readable `checkpoint_record`.

## Lifecycle

Checkpoint has four explicit lifecycle events:

1. `CREATE`
2. `VERIFY`
3. `RESTORE`
4. `RESTORE_ROLLBACK`

These are lifecycle events, not vague status labels.

## Core rule

A Synrail checkpoint is only a safe point if:

- required artifacts exist
- the checkpoint passes schema validation
- the checkpoint passes state-consistency validation
- stale or conflicting artifacts are not silently ignored

If those things are not true, the checkpoint is a snapshot candidate, not a trusted safe point.

## Required behavior

### `CREATE`

Create must:

- bind the checkpoint to one `run_id`
- bind it to one `task_class`
- record the current `source_state`
- record the current `source_closure_status`
- record one artifact manifest

### `VERIFY`

Verify must answer:

- are the required artifacts present
- do they pass schema validation
- does the state remain internally consistent
- are any artifacts stale enough to make the checkpoint unsafe

If verification fails, the checkpoint must not be treated as a trusted restore point.

### `RESTORE`

Restore must:

- name the `target_root`
- record which artifacts were restored
- require restore verification before claiming success

Restore success is not just “files copied”.
Restore success means:

- restored artifacts exist
- restored state is internally consistent
- restore verification passed
- no unexpected conflicting artifacts remain inside the restored checkpoint surface

### `RESTORE_ROLLBACK`

If restore verification fails, the kernel must be able to emit a rollback event.

Rollback must record:

- why rollback was triggered
- which artifacts were rolled back
- whether rollback itself succeeded

If rollback fails, that failure must be explicit.
The kernel must not pretend it is back in a safe state.

## Minimal invariant

Checkpoint must remain stricter than general artifact copying.

The shortest invariant is:

- a checkpoint is trustworthy only if `VERIFY = PASSED`
- a restore is trustworthy only if restore verification passes
- a failed restore without explicit rollback status is not a safe outcome

## Decision rule

Checkpoint work is good kernel work only if it makes at least one of these better:

- safe continuation before risky repair
- recoverability after bad repair
- trust in one known-good state
- operator confidence about where rollback is possible

If it only creates more artifact surface without stronger restore truth, it is off-scope.
