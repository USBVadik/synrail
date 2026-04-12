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
3. emit one machine-readable block report when a transition is denied
4. apply a doctor record back into the state machine
5. apply a proof-bundle artifact back into the state machine
6. apply a closure verdict back into the state machine
7. run one bounded orchestration contour across doctor, optional preparation, bundle, closure, optional refresh, and optional comparison
8. absorb one mode-selection receipt into that bounded orchestration contour
9. emit one machine-readable repair handoff from the current non-green state
10. auto-synthesize one machine-readable repair packet from the current non-green truth surface
11. record one explicit runtime-resume origin for continuation from a non-green state
12. deny disallowed transitions through hard gate checks
13. emit one primary canonical run artifact for the bounded contour
14. emit the current machine-readable state

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

It can now also emit one governed-path proof plan and one preparation receipt from inside that same bounded contour, which is the first move toward reducing governed-path proof scrambling before closure.

It can now also absorb one preparation-aware strong-path selection receipt into that same bounded contour, which is the first move toward turning mode selection into an executable runtime handoff instead of leaving it as a separate advisory layer.

It can now also carry one explicit runtime continuation marker from a non-green starting state, which is the first move toward making re-entry a first-class runtime behavior instead of leaving it only as a family of canonical repaired fixtures.

It can now also emit and consume one repair handoff contract around that continuation path, which is the first move toward making continuation inputs machine-readable instead of leaving them mostly in operator memory.

It can now also auto-synthesize and participate in one richer repair-packet continuation flow, where the spine itself can now provide:

- one embedded handoff
- one embedded resumability family
- one continuation plan
- one repair-input bundle
- one runtime output-default set
- one embedded selection/preparation context
- one summarized runtime-truth slice

That continuation marker is now proven on:

- one partial-proof continuation family
- one degraded recovery continuation family
- one doctor-blocked readiness continuation family

That repair-handoff layer is now proven on:

- one blocked continuation attempt that stops explicitly at `repair_handoff`
- one ugly compound continuation that uses two staged handoffs plus named `resume`

That repair-packet layer is now proven on:

- one blocked continuation packet that no longer needs a fake `final_result`
- one second uglier compound continuation that crosses blocked readiness, invalid proof, degraded recovery, and accepted closure
- one third uglier compound continuation that carries selection/preparation handoff through packet-first runtime continuation
- one fourth uglier compound continuation that carries selection/preparation handoff through repair-handoff blocking, recovery repair, and one explicit terminal not-resumable finish

It now also chooses the comparison harness by input schema version, so the same bounded contour can still read legacy comparison inputs while moving the active pressure-testing path toward economics-aware comparison records.

It can now also advance a fresh initialized run through the early readiness contour by absorbing:

- target-surface attestation
- doctor readiness
- exact-task integrity
- execution completion

It now also gives explicit state shape to the main failure branches instead of leaving them only in closure fields:

- `DOCTOR_BLOCKED`
- `PROOF_BUNDLE_PARTIAL`
- `PROOF_BUNDLE_INVALID`

It now also gives explicit precedence to competing blockers inside the spine itself, instead of letting the first checked gate silently dominate.

It now also holds one canonical reverse edge from a blocked readiness contour back to accepted closure when:

- the missing exact-task identity is restored
- proof inputs are complete enough for acceptance

It now also holds one canonical reverse edge from a partial proof lane back to accepted closure when:

- the missing proof sections are supplied
- the resulting bundle becomes complete enough for acceptance

It now also holds one canonical reverse edge from a degraded recovery lane back to accepted closure when:

- recovery reverification is completed
- no stronger invalidation remains after refresh reconciliation

The current machine-readable block artifact for denied transitions lives at:

- `schemas/spine_block_report_v0.schema.json`

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

It now also proves two stronger continuation edges than before:

- one explicit truly not-resumable selection-blocked family that stops at `resume` with `STATE_NOT_RESUMABLE`
- one fifth uglier packet-first continuation family that carries stale-artifact hints, explicit repair order, one newly surfaced readiness failure, recovery repair, and accepted closure on the same runtime surface
