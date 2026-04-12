# Repeatability Plan

## Purpose

Define the next bounded plan for strengthening confidence that closure-grade exact-task success is repeatable rather than one-off.

This document exists to keep repeatability work disciplined and narrow.

## Why this matters

The extracted repo already has:

- strong structure
- strong boundary
- one accepted closure-grade exact-task proof floor

What it does not yet have is strong confidence that the same class of governed exact-task success can happen again without extraordinary luck.

## Repeatability question

The question is not:

- can we get many wins quickly

The question is:

- can the same governed exact-task path produce at least one more accepted closure-grade result without breaking the kernel’s own trust rules

## Minimum target

The next repeatability target is:

- one additional closure-grade exact-task success on a bounded exact-task scenario

This should be enough to move confidence from:

- `single strong proof floor`

toward:

- `initial repeatability confidence`

## Constraints

Repeatability work should stay narrow:

- preserve exact-task identity
- preserve exact prompt identity where required
- preserve exact execution policy where required
- keep surface attestation and proof discipline intact
- do not dilute acceptance rules just to get a second success

## Reuse rule

Reuse as much of the governed path as possible:

- exact-task closure semantics
- proof-bundle standards
- doctor and lane logic
- trusted baseline discipline
- artifact review rules

If repeatability requires changing the acceptance bar, it is not proving repeatability.

## What counts as a success

A repeatability run counts only if:

1. the task stays within bounded exact-task semantics
2. the proof bundle is reviewable
3. the result reaches accepted closure under the existing kernel rules
4. the acceptance does not depend on hand-waving around contradictions

## What does not count

These do not count as repeatability proof:

- a narrative-only success claim
- a live incident `PASS` that never enters exact-task closure semantics
- a result that only works by weakening the proof rules
- a broad “similar enough” scenario that breaks exact-task identity

## Suggested next move

The next safe repeatability move is:

1. choose one bounded closure-grade candidate
2. restate its task identity and proof expectations explicitly
3. rerun through the governed exact path
4. record the result as:
   - accepted repeatability signal
   - or bounded blocker, without widening scope

## Decision rule

If the next repeatability attempt fails, do not answer by broadening the project.

First decide whether the failure came from:

- execution-surface instability
- proof-path fragility
- task-selection weakness
- or genuine lack of repeatability in the current governed path
