# Refresh Chain Automation 001

## Purpose

Define the first executable refresh-chain automation for `Synrail`.

This document exists so state-changing events do not rely on operator memory to keep run state, proof state, and closure state aligned.

## Artifacts

The first refresh slice now lives at:

- `tools/reference/synrail_refresh_v0.py`
- `schemas/refresh_report_v0.schema.json`

## What it does

The refresh automation v0 can:

1. read one run-state artifact
2. apply one explicit event type
3. refresh doctor, proof-bundle, closure, and recovery surfaces in deterministic order
4. invalidate over-green closure state when lower-level evidence worsens
5. reconcile one repaired recovery contour back into accepted closure when reverification is completed and no stronger invalidation remains
6. emit one machine-readable refresh report with explicit dominant invalidation
7. optionally write the refreshed state back to disk

## Why this matters

Without refresh automation, `Synrail` risks turning into a drift-prone system where:

- state says one thing
- closure says another
- recovery changed something real
- operator memory is doing the stitching

The refresh layer is the first move toward making state refresh a product behavior rather than a reminder ritual.

## v0 invalidation rules

The refresh automation currently downgrades closure when:

- doctor becomes `FAIL`
- proof bundle becomes non-`COMPLETE`
- recovery becomes `PENDING` without reverification

Those downgrades now also land in explicit degradation states instead of only changing closure fields:

- `DOCTOR_BLOCKED`
- `PROOF_BUNDLE_PARTIAL`
- `PROOF_BUNDLE_INVALID`
- `RECOVERY_PENDING`

The current precedence rule is now explicit:

1. `closure_invalidated_by_doctor`
2. `closure_invalidated_by_invalid_bundle`
3. `closure_invalidated_by_semantic_bundle`
4. `closure_invalidated_by_partial_bundle`
5. `closure_invalidated_by_recovery`

So when multiple degradations apply at once, the refresh report names:

- all applicable invalidations
- one `dominant_invalidation`

That same refresh record now also feeds the default thin-output shell for the active run, so `synrail check` can point at only the stale obligation class instead of broadly restating the whole non-green contour.

## v0 recovery reconciliation rule

The refresh automation can now also reconcile one degraded contour back into accepted closure when:

- the current closure block is `RECOVERY_REVERIFICATION_INCOMPLETE`
- the proof bundle is still `COMPLETE`
- doctor is still green enough
- recovery becomes `COMPLETE`
- reverification is explicitly complete

That matters because the refresh layer is no longer only:

- a downgrade engine

It can now also hold one narrow repaired reverse edge after lower-level recovery truth is restored.

## v0 limitations

The refresh automation currently does not perform:

- multi-artifact dependency discovery
- richer event taxonomies
- full closure recomputation from scratch

Those belong to the next layers.

## Decision rule

Future refresh work should strengthen:

- deterministic refresh order
- explicit invalidation
- lower-level evidence precedence

without turning v0 into a broad orchestration shell.
