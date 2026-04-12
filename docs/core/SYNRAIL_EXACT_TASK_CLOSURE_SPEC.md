# SYNRAIL_EXACT_TASK_CLOSURE_SPEC

## Purpose

Define what it means for an exact task to be truly closed under `Synrail` kernel rules.

This document exists so the phrase:

- `proof-complete exact-task cycle`

has one explicit meaning inside the product.

## Closure rule

An exact task is closed only when all of the following are true:

1. the exact task identity is preserved
2. the exact prompt identity is preserved
3. the exact execution policy is preserved
4. the exact-retry lane no longer has an active blocker that invalidates trust
5. the full proof bundle meets `SYNRAIL_PROOF_BUNDLE_STANDARD`
6. the resulting acceptance is explicit, not implied

## Closure record should answer

A valid exact-task closure record should answer:

- which exact task was attempted
- on which trusted baseline
- through which execution surface
- with which prompt identity
- under which exact policy
- with which proof bundle
- whether the result is accepted
- if not accepted, why not

## Minimal closure states

### 1. `OPEN`

The task is still open.

Reasons may include:

- active blocker remains
- proof bundle incomplete
- exact-task identity ambiguity
- diagnosis without artifact proof

### 2. `CLAIMED_NOT_ACCEPTED`

A result was claimed, but the kernel cannot accept it.

### 3. `ACCEPTED_EXACT_CLOSURE`

The exact task is accepted as closed under kernel rules.

## Task-specific state boundary

Task-specific live closure state should not be embedded in this extracted core document.

Use this document for:

- generic exact-task closure semantics
- generic acceptance rules
- generic closure states

Put live task-specific closure state in:

- proving-ground records
- sanitized examples
- future bounded status artifacts that are explicitly scoped to one task

## Relation to extraction readiness

The extraction checklist item:

- `At least one proof-complete exact-task cycle under kernel rules exists`

cannot pass until at least one exact-task closure reaches:

- `ACCEPTED_EXACT_CLOSURE`

## Decision rule

Do not downgrade the closure requirement just to advance extraction.

Extraction readiness should follow real exact-task closure, not replace it.
