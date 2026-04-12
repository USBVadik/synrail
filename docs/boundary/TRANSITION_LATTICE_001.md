# Transition Lattice 001

## Purpose

State the shortest honest current reading of which transitions the executable `Synrail` kernel can already carry and which ones it can explicitly stop or invalidate.

This document exists so the repo can summarize the kernel as a state machine, not only as:

- outcome classes
- scenario readings
- product wedge claims

## Current transition anchors

The current lattice is anchored by five transition families:

1. clean progression
2. proof downgrade
3. refresh degradation
4. readiness block
5. blocked re-entry

These are the current most meaningful state edges visible in the canonical artifacts.

## 1. Clean progression

Current readable path:

- `INITIALIZED`
- `TARGET_SURFACE_ATTESTED`
- `READY`
- `EXECUTION_COMPLETED`
- `PROOF_BUNDLE_COMPLETE`
- `CLOSURE_ACCEPTED`

Canonical anchor:

- `fixtures/executable_loop_accepted_run_001/run.json`

What this proves:

- the kernel can carry one run through the intended happy contour
- readiness, proof, and closure can line up cleanly
- accepted closure is not only theoretical

## 2. Proof downgrade

Current readable path:

- `EXECUTION_COMPLETED`
- `PROOF_BUNDLE_PARTIAL`
- `CLAIMED_NOT_ACCEPTED`

Canonical anchor:

- `fixtures/executable_loop_run_002/run.json`

And also visible in:

- `fixtures/executable_loop_run_003/run.json`

What this proves:

- the kernel can distinguish execution completion from closure acceptance
- incomplete proof does not collapse into an “almost accepted” fiction
- the partial lane is a first-class state, not only a note in prose

## 3. Refresh degradation

Current readable path:

- `CLOSURE_ACCEPTED`
- `RECOVERY_PENDING`
- `CLAIMED_NOT_ACCEPTED`

Canonical anchor:

- `fixtures/executable_loop_run_001/run.json`

What this proves:

- a greener earlier state can be invalidated by later lower-level truth
- refresh is not just decorative bookkeeping
- the kernel can model “accepted, then no longer acceptable”

## 4. Readiness block

Current readable path:

- `INITIALIZED`
- `TARGET_SURFACE_ATTESTED`
- `BLOCKED at READY`

Canonical anchor:

- `fixtures/executable_loop_blocked_run_001/run.json`

Dominant blocked reading:

- `EXACT_TASK_IDENTITY_NOT_CONFIRMED`

What this proves:

- blocked progression is first-class
- the kernel can stop before execution starts
- readiness failure is explicit in both report and primary run artifact

## 5. Blocked re-entry

Current readable path:

- `TARGET_SURFACE_ATTESTED`
- `CLAIMED_NOT_ACCEPTED`
- repair exact-task identity
- `READY`
- `EXECUTION_COMPLETED`
- `PROOF_BUNDLE_COMPLETE`
- `CLOSURE_ACCEPTED`

Canonical anchor:

- `fixtures/executable_loop_reentry_run_001/run.json`

What this proves:

- a blocked readiness contour is not necessarily terminal
- the kernel can carry one repaired reverse edge back into a green closure state
- re-entry now exists on the same primary artifact surface as accepted, partial, degraded, and blocked runs

## What the transition lattice now supports

The current transition lattice supports a stronger kernel-level claim:

- `Synrail` can already model:
  - clean progression
  - partial-proof stop
  - post-closure degradation
  - pre-execution blockage
  - one explicit blocked-to-accepted reverse edge

That is stronger than saying only:

- “there are some useful states”

because it shows the kernel can already hold meaningful edges between those states.

## What is still weaker than it should be

The transition lattice still has visible gaps:

- blocked-to-accepted re-entry now exists, but degraded-to-accepted and partial-to-accepted are still weaker than they should be
- hybrid currently shares the partial lane, but its transition semantics are still not richer than that lane
- blocked families are still narrower than a mature readiness graph
- the current lattice is inferred from bounded runtime contours, not yet from a deeper general kernel runtime

## How this relates to other readings

This document does not replace:

- `OUTCOME_LATTICE_001.md`
- `TRIO_READING_001.md`
- `REENTRY_LATTICE_001.md`

Because:

- `OUTCOME_LATTICE_001.md` is about stable outcome classes
- `TRIO_READING_001.md` is about value comparison and wedge shape
- `REENTRY_LATTICE_001.md` is about reverse movement back toward greener states
- this document is about the transitions between the states the kernel currently knows how to hold

## Why this matters

With this transition lattice, the repo can now describe the executable kernel in three complementary ways:

1. wedge/value
2. outcome classes
3. state transitions
4. reverse edges back toward greener states

That is a much healthier internal product surface than describing the project only through scenarios or only through architecture prose.

## Decision rule

The next strongest kernel work should improve one of these:

1. make one current transition less manual and more spine-owned
2. add another missing reverse or recovery transition with real enforcement
3. reduce ambiguity between nearby transition families such as partial vs hybrid

If a change does not strengthen one of those, it is probably not the best next move for the executable kernel right now.
