# Gate Set 001

## Purpose

Define the first minimal hard gate set for the executable `Synrail` spine.

This document exists so the product stops depending on prose-only control rules for its most important denials.

## Current hard gates

The first executable gate set is:

### Gate 1. Target surface attestation gate

Rule:

- if the target surface is not attested, `TARGET_SURFACE_ATTESTED` cannot be entered

### Gate 2. Doctor readiness gate

Rule:

- if doctor state is not `PASS`, `READY` cannot be entered

### Gate 3. Exact-task integrity gate

Rule:

- if exact-task identity is not confirmed, `READY` and later execution states cannot be entered

### Gate 4. Artifact completeness gate

Rule:

- if the execution artifact bundle is not present, proof-complete states cannot be entered

### Gate 5. Proof bundle acceptance gate

Rule:

- if proof bundle state is not `COMPLETE`, closure cannot be accepted

### Gate 6. Recovery acceptance gate

Rule:

- if recovery is pending and reverification is incomplete, closure cannot be accepted

## Why this set is enough for v0

This set is intentionally the minimum first deny/allow layer.

It is enough to prove that `Synrail` can:

- stop unsafe progression
- keep closure from outrunning evidence
- encode the core acceptance semantics in code

## Artifact

These gates are currently expressed in:

- `tools/reference/synrail_spine_v0.py`

## Decision rule

Do not add more gates to v0 unless they clearly improve:

- wrong-surface prevention
- false-success prevention
- closure-proof integrity

More gates are not automatically better.
