# Outcome Lattice 001

## Purpose

State the shortest honest current reading of the canonical outcome classes the executable `Synrail` stack can already represent.

This document exists so the repo can summarize kernel behavior through outcome types, not only through scenario-by-scenario narratives.

## Canonical outcome surfaces

The current lattice is anchored by four canonical surfaces:

1. accepted
   - `fixtures/executable_loop_accepted_run_001/run.json`
2. partial
   - `fixtures/executable_loop_run_002/run.json`
3. degraded
   - `fixtures/executable_loop_run_001/run.json`
4. blocked
   - `fixtures/executable_loop_blocked_run_001/run.json`

These four surfaces are useful because together they show more than “does Synrail win?”

They show what the kernel currently knows how to do with a run.

## Current readings

### 1. Accepted

Current reading:

- `OK | accepted | NONE | CLOSURE_ACCEPTED | ACCEPTED`

What it means:

- readiness was green enough
- proof was complete enough
- closure was accepted honestly
- no lower-level degradation forced a downgrade afterward

Why it matters:

- proves the kernel can carry one contour to a clean accepted state
- gives the repo one stable accepted reference surface inside the repo itself

### 2. Partial

Current reading:

- `OK | comparison | MISSING_PROOF_SECTIONS | PROOF_BUNDLE_PARTIAL | CLAIMED_NOT_ACCEPTED`

What it means:

- execution can finish
- some proof can exist
- closure still remains honestly unaccepted
- the kernel can stop without pretending the run is good enough

Why it matters:

- shows the stack can preserve honest non-acceptance on incomplete proof
- keeps “worked somewhat” separate from “closure accepted”

### 3. Degraded

Current reading:

- `OK | comparison | RECOVERY_REVERIFICATION_INCOMPLETE | RECOVERY_PENDING | CLAIMED_NOT_ACCEPTED`

What it means:

- the run was greener earlier
- then a lower-level recovery truth changed
- refresh invalidated the greener closure state
- the kernel preserved post-event truth instead of keeping a stale accepted reading

Why it matters:

- proves anti-drift behavior
- shows the kernel can model “was acceptable, no longer acceptable”

### 4. Blocked

Current reading:

- `BLOCKED | ready_transition | EXACT_TASK_IDENTITY_NOT_CONFIRMED | TARGET_SURFACE_ATTESTED | CLAIMED_NOT_ACCEPTED`

What it means:

- the contour was stopped before execution progression
- the stop reason is explicit
- the dominant blocker is explicit
- the run still gets a canonical primary artifact

Why it matters:

- proves blocked progression is first-class
- keeps blocked runs on the same truth surface as greener runs

## What the lattice now supports

The lattice now supports a stronger kernel-level claim:

- `Synrail` can represent not just success vs failure, but:
  - accepted truth
  - incomplete proof
  - post-acceptance degradation
  - pre-execution blockage

That is a more useful product reading than saying only:

- “the system can accept”
- “the system can reject”

## What the lattice does not yet support

The lattice does not yet prove:

- that every important outcome type is already modeled
- that precedence is perfect across all future failure classes
- that hybrid semantics are mature
- that production-scale runtime behavior is already captured

It also does not replace:

- `TRIO_READING_001.md`

because the trio is about:

- value comparison
- wedge shape
- where `Synrail` beats or does not beat a simpler baseline

while this lattice is about:

- kernel outcome classes
- how the run state itself can end up

## Why this matters

With this lattice, the repo can now point to:

- one canonical accepted contour
- one canonical partial contour
- one canonical degraded contour
- one canonical blocked contour

That is a much healthier internal product surface than having rich reference material only for the greener paths.

## Decision rule

The next strongest kernel work should improve one of these:

1. make one outcome class more executable and less narrative
2. reduce ambiguity between neighboring outcome classes
3. tighten the transitions between accepted, degraded, partial, and blocked states

If a change does not help one of those, it is probably not the strongest next move for the executable kernel right now.
