# SYNRAIL_EXACT_TASK_PROGRESSION

## Purpose

Define the allowed progression of an exact task inside `Synrail` from blocked readiness to accepted closure.

This document exists so exact-task movement is governed by explicit transitions rather than by narrative momentum.

## Core rule

An exact task may move forward only through named state transitions.

It must not jump from:

- blocker awareness

to:

- accepted closure

without passing through the required readiness and proof states.

## Progression states

### 1. `BLOCKED_READINESS`

The task cannot yet be attempted safely for an exact retry.

Typical reasons:

- missing credential surface
- missing exact prompt artifact
- ambiguous execution surface
- unresolved exact-retry doctor blocker

### 2. `READY_FOR_EXACT_RETRY`

The exact-retry lane is acceptable.

This means:

- exact-retry doctor is acceptable
- no active blocker invalidates trust
- exact task identity remains unchanged

### 3. `EXECUTION_ATTEMPTED`

An exact retry was actually executed under the preserved task semantics.

This state does not imply acceptance.

### 4. `CLAIMED_RESULT`

The run returned a claim about diagnosis or fix outcome.

This state still does not imply acceptance.

### 5. `PROOF_BUNDLE_REVIEWABLE`

A full reviewable proof bundle is present.

This means the kernel can meaningfully judge the run.

### 6. `ACCEPTED_EXACT_CLOSURE`

The task is accepted as closed under kernel rules.

## Allowed transitions

Allowed transitions are:

- `BLOCKED_READINESS -> READY_FOR_EXACT_RETRY`
- `READY_FOR_EXACT_RETRY -> EXECUTION_ATTEMPTED`
- `EXECUTION_ATTEMPTED -> CLAIMED_RESULT`
- `CLAIMED_RESULT -> PROOF_BUNDLE_REVIEWABLE`
- `PROOF_BUNDLE_REVIEWABLE -> ACCEPTED_EXACT_CLOSURE`

## Disallowed transitions

Disallowed transitions include:

- `BLOCKED_READINESS -> ACCEPTED_EXACT_CLOSURE`
- `EXECUTION_ATTEMPTED -> ACCEPTED_EXACT_CLOSURE`
- `CLAIMED_RESULT -> ACCEPTED_EXACT_CLOSURE`
- `READY_FOR_EXACT_RETRY -> ACCEPTED_EXACT_CLOSURE`

These are disallowed because they skip explicit proof evaluation.

## Transition conditions

### `BLOCKED_READINESS -> READY_FOR_EXACT_RETRY`

Requires:

- exact-retry doctor no longer blocked
- exact-retry lane no longer blocked
- active blocker list for exact retry is empty or non-invalidating

### `READY_FOR_EXACT_RETRY -> EXECUTION_ATTEMPTED`

Requires:

- actual execution start under unchanged exact-task semantics

### `EXECUTION_ATTEMPTED -> CLAIMED_RESULT`

Requires:

- run returns a terminal claim artifact
- at minimum, a structured terminal result exists

### `CLAIMED_RESULT -> PROOF_BUNDLE_REVIEWABLE`

Requires:

- full proof bundle per `SYNRAIL_PROOF_BUNDLE_STANDARD`

### `PROOF_BUNDLE_REVIEWABLE -> ACCEPTED_EXACT_CLOSURE`

Requires:

- proof bundle passes review
- no contradiction across proof sections
- exact-task closure record explicitly moves to accepted state

## Task-specific state boundary

Task-specific live progression state should not be embedded in this extracted core document.

Use this document for:

- generic exact-task progression states
- generic allowed transitions
- generic transition conditions

Put live task-specific progression state in:

- proving-ground records
- sanitized examples
- future bounded task-status artifacts that are explicitly scoped to one task

## Relation to other artifacts

This progression should be read together with:

- `SYNRAIL_PROOF_BUNDLE_STANDARD`
- `SYNRAIL_EXACT_TASK_CLOSURE_SPEC`

## Decision rule

If the current progression state is unclear, the task should be treated as less advanced rather than more advanced.
