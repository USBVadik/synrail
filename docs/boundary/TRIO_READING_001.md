# Trio Reading 001

## Purpose

State the shortest honest current reading of the three canonical run artifacts.

This document exists so the repo can summarize the current product wedge from actual machine-readable run artifacts rather than from scattered prose or single-case interpretation.

## Canonical trio

The current trio is:

1. strong path
   - `fixtures/executable_loop_run_001/run.json`
2. weak path
   - `fixtures/executable_loop_run_002/run.json`
3. hybrid path
   - `fixtures/executable_loop_run_003/run.json`

These are the current canonical run artifacts for:

- where `Synrail` clearly earns its cost
- where a lighter baseline may already be enough
- where the signal is still mixed

## Current readings

### 1. Strong path

Current reading:

- `SYNRAIL_BETTER`

Why:

- proof-sensitive closure work
- stronger false-success reduction
- stronger proof completeness
- meaningful recovery discipline

Important nuance:

- the strong-path canonical artifact reflects the post-refresh reality
- so it ends in `CLAIMED_NOT_ACCEPTED`, not a frozen pre-refresh accepted snapshot

### 2. Weak path

Current reading:

- `BASELINE_GOOD_ENOUGH`

Why:

- low false-success risk
- cheap validation
- stronger proof semantics from `Synrail` are real
- but the overhead is harder to justify on this class

Important nuance:

- this envelope is still useful because it shows `Synrail` can preserve honest non-acceptance
- but it does not show decisive product advantage

### 3. Hybrid path

Current reading:

- `UNCLEAR`

Why:

- `Synrail` adds bounded stop/no-bluff discipline
- proof completeness is somewhat better
- but current evidence is not strong enough to claim a clear win

Important nuance:

- this is not a failure
- it is a useful signal that the hybrid mode is plausible but still under-proven

## What the trio now supports

The trio now supports a tighter wedge statement:

- use full `Synrail` where wrong closure is expensive
- do not assume the full governed path is justified on small low-risk incidents
- treat the hybrid subset as promising but not yet settled

## What the trio does not support

The trio does not support the broader claim:

- `Synrail` should be the default full path everywhere

It also does not yet support:

- strong claims of low overhead
- broad runtime readiness
- a mature verdict on the hybrid mode

## Why this matters

This trio is stronger than any single run because it gives the repo:

- one winning case
- one baseline-sufficient case
- one unresolved middle case

That is a healthier product reading than trying to compress everything into a universal success story.

## Decision rule

The next strongest build work should improve one of these:

1. strong-path superiority
2. hybrid-mode evidence quality
3. integration depth between the current runtime slices

If a change does not help one of those, it is probably not the best next move right now.
