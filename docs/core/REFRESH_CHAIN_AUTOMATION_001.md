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
5. emit one machine-readable refresh report
6. optionally write the refreshed state back to disk

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
