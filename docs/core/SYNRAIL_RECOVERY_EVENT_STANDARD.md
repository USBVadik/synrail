# SYNRAIL_RECOVERY_EVENT_STANDARD

## Purpose

Define what counts as a real recovery event in `Synrail`.

This document exists so a blocker is not treated as resolved merely because activity happened around it.

## Core rule

A recovery event is accepted only when it changes product state in a way that is explicit, reviewable, and re-verified.

`attempted recovery` is not the same as `accepted recovery`.

## What recovery event is

A recovery event is the smallest accepted unit of blocker resolution.

It should answer:

- which blocker was targeted
- what changed on the intended surface
- what verification was rerun
- what state transition became allowed, if any

## What recovery event is not

Recovery event is not:

- a note that someone updated environment setup
- a command that merely stopped failing once
- a claim that the blocker is gone without re-verification
- a broad roadmap step

## Required properties

A valid recovery event must include:

### 1. Target blocker identity

The blocker class being addressed must be named.

### 2. Intended surface identity

The exact execution surface must be named.

### 3. Recovery action identity

What changed must be described narrowly.

### 4. Re-verification evidence

At least the directly affected doctor/gate/lane artifacts must be re-evaluated.

### 5. State impact

The recovery event must say whether it:

- removed a blocker
- changed readiness state
- unlocked a transition
- did not change state after all

## Allowed recovery outcomes

A recovery event may end in one of:

- `RECOVERY_NOT_PERFORMED`
- `RECOVERY_ATTEMPTED_NOT_ACCEPTED`
- `RECOVERY_INCONCLUSIVE`
- `RECOVERY_ACCEPTED`

## Decision rule

If the recovery action cannot be linked to explicit re-verification and state change, the recovery event is not accepted.
