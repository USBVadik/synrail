# Execution Spine 001

## Purpose

Define the first executable spine for `Synrail`.

This document exists so the product has one real control contour instead of a loose family of good control surfaces.

## Artifact

The first minimal spine prototype now lives at:

- `tools/reference/synrail_spine_v0.py`

## What the spine does

The v0 spine can:

1. initialize a machine-readable run state
2. attempt a state transition
3. apply a doctor record back into the state machine
4. apply a proof-bundle artifact back into the state machine
5. apply a closure verdict back into the state machine
6. run one bounded orchestration contour across doctor, bundle, closure, optional refresh, and optional comparison
7. deny disallowed transitions through hard gate checks
8. emit the current machine-readable state

## Current transition contour

The current intended contour is:

1. `INITIALIZED`
2. `TARGET_SURFACE_ATTESTED`
3. `READY`
4. `EXECUTION_COMPLETED`
5. `PROOF_BUNDLE_COMPLETE`
6. `PROOF_BUNDLE_PARTIAL` or `PROOF_BUNDLE_INVALID` when proof is not closure-ready
7. `DOCTOR_BLOCKED` when readiness fails early
8. `CLOSURE_ACCEPTED` or `CLOSURE_REJECTED`

## Why this matters

This is the first step toward a real product loop:

- target surface identified
- readiness checked
- execution gated
- artifacts required
- proof validated
- closure decided

The spine now also begins to act as the control contour that absorbs bundle/closure artifacts back into state instead of leaving that linkage entirely manual.

It now also absorbs doctor records back into state, which tightens the contour further around:

- readiness
- proof assembly
- closure

It now also owns the current bounded orchestration contour directly, instead of leaving that contour primarily in a higher wrapper layer.

It can now also advance a fresh initialized run through the early readiness contour by absorbing:

- target-surface attestation
- doctor readiness
- exact-task integrity
- execution completion

It now also gives explicit state shape to the main failure branches instead of leaving them only in closure fields:

- `DOCTOR_BLOCKED`
- `PROOF_BUNDLE_PARTIAL`
- `PROOF_BUNDLE_INVALID`

It is still small, but it is no longer only descriptive.

## Anti-overclaim rule

The current spine prototype is:

- real
- executable
- machine-readable

It is not yet:

- a complete kernel runtime
- a broad orchestrator
- the final operator UX

## Decision rule

Any future spine growth should strengthen one of these:

- hard gating
- state fidelity
- proof/closure enforcement
- next-safe-step emission

If it mostly adds breadth before enforcement depth, it is premature.
