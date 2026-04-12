# Reentry Lattice 001

## Purpose

State the shortest honest current reading of which reverse edges the executable `Synrail` kernel can already carry back toward greener states.

This document exists so the repo can summarize not only:

- outcome classes
- forward transitions
- degradation paths

but also whether the kernel can return from a less-green contour after the blocking condition is repaired.

## Current re-entry anchors

The current re-entry lattice is anchored by one canonical reverse edge:

1. blocked readiness to accepted closure

That is a narrow but important start.

It shows the kernel is not only a reject or downgrade engine.

## 1. Blocked readiness to accepted closure

Current readable path:

- blocked starting surface:
  - `fixtures/executable_loop_blocked_run_001/run.json`
- repaired re-entry surface:
  - `fixtures/executable_loop_reentry_run_001/run.json`

Readable transition:

- `TARGET_SURFACE_ATTESTED`
- `CLAIMED_NOT_ACCEPTED`
- `EXACT_TASK_IDENTITY_NOT_CONFIRMED`
- restore exact-task identity
- `READY`
- `EXECUTION_COMPLETED`
- `PROOF_BUNDLE_COMPLETE`
- `CLOSURE_ACCEPTED`

What this proves:

- a blocked readiness contour is not automatically terminal
- the kernel can accept a repaired run without pretending the original blocked attempt was fine
- the reverse edge now exists as a canonical machine-readable repo surface

Why this matters:

- it strengthens `Synrail` as a closure-guidance system, not only a denial system
- it gives the repo one explicit repaired contour, not only accepted, partial, degraded, and blocked end states

## What the re-entry lattice now supports

The current re-entry lattice supports a stronger kernel-level claim:

- `Synrail` can now hold at least one explicit reverse edge from a blocked state back to accepted closure

That is stronger than saying only:

- the kernel can stop
- the kernel can degrade
- the kernel can accept

because it shows the kernel can sometimes recover honestly after a prior block.

## What is still weaker than it should be

The re-entry lattice still has visible gaps:

- partial-to-accepted re-entry is not yet canonical
- degraded-to-accepted re-entry is not yet canonical
- the current canonical reverse edge is readiness-blocked recovery, not the full set of recovery families
- runtime support for doctor-blocked re-entry is ahead of canonical repo evidence

## How this relates to other readings

This document does not replace:

- `OUTCOME_LATTICE_001.md`
- `TRANSITION_LATTICE_001.md`

Because:

- `OUTCOME_LATTICE_001.md` is about stable outcome classes
- `TRANSITION_LATTICE_001.md` is about the broader forward and downgrade edges the kernel already holds
- this document is specifically about reverse movement back toward greener states

## Why this matters

With this re-entry lattice, the repo can now describe the executable kernel in four complementary ways:

1. wedge/value
2. outcome classes
3. transitions and degradations
4. reverse edges back toward acceptance

That is a healthier internal product surface than treating repair only as something implied by prose or ad hoc operator behavior.

## Decision rule

The next strongest kernel work should improve one of these:

1. make one additional reverse edge canonical, especially `partial -> accepted`
2. make one degraded-to-greener re-entry less manual and more spine-owned
3. reduce ambiguity between “repairable blocked” and “still not re-enterable” states

If a change does not strengthen one of those, it is probably not the best next move for the executable kernel right now.
