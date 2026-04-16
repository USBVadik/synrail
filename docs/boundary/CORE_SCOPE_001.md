# CORE_SCOPE_001

## Purpose

Freeze the smallest current Synrail product scope for Sprint 01.

This document is not a long-term product taxonomy.
It is a short-horizon execution rule:

- what counts as the kernel right now
- what is secondary
- what is explicitly frozen until the kernel gets stronger

## Minimal Lovable Core

For this sprint, the Synrail kernel is only:

1. `Doctor`
2. `State / Spine`
3. `Bundle`
4. `Closure`
5. `Refresh`
6. `Continuation / Resume`
7. `Checkpoint`

These are the only layers allowed to drive first-class build work in this tranche.

## Why this freeze exists

The current product risk is no longer “not enough conceptual shape”.

The current risk is:

- internal completeness illusion
- growing continuation vocabulary faster than operator value
- adding more runtime surfaces before the current kernel is hard enough

So this sprint is not about broadening Synrail.
It is about making the current kernel:

- safer
- clearer
- more convergent under repair pressure
- easier to operate without author intuition

## In Scope

Work is in scope when it directly strengthens one of these:

- false-readiness reduction in `Doctor`
- state transition truth in `Spine`
- proof completeness and proof invalidation in `Bundle` or `Closure`
- recovery invalidation and honest re-acceptance in `Refresh`
- repair convergence, non-resumable boundaries, and operator path compression in `Continuation / Resume`
- verified safe-point creation, verification, restore, and rollback in `Checkpoint`

## Secondary, Not Driving The Sprint

These layers may stay present in the repo, but they do not drive current build decisions:

- comparator economics
- mode selection
- substitute-pressure surfaces
- cost-of-control aggregation
- canonical readings that only restate existing truth
- broad product positioning or moat framing

They can still be updated when needed to reflect kernel changes, but they are not the reason for a change.

## Explicitly Frozen For Sprint 01

Do not start new work here unless the kernel hardening step explicitly requires it:

- new continuation families added for richness alone
- richer repair vocabulary without a concrete kernel gap
- hybrid expansion
- novice-facing UX layers
- broad platform or packaging work
- UI or dashboard work
- new meta-doc layers without runtime payload

## Decision Rule

A proposed change is on-scope only if it does at least one of these:

- hardens the kernel against a real failure mode
- reduces operator tax on a current kernel path
- improves convergence or termination under repair pressure
- makes runtime truth easier to verify
- makes checkpoint safety more reliable

If a change mostly adds explanation, surface area, or apparent maturity, it is out of scope for this sprint.

## Active Sprint Order

The current kernel-hardening order is:

1. `Freeze Core`
2. `Checkpoint`
3. `Repair Termination`
4. `Artifact Consistency`
5. `Doctor Coverage + 1 expensive fix`
6. `Basic Observability`
7. `Better Errors`

Each major step must be followed by a short pressure-test before the next major build step begins.
