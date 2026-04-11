# SYNRAIL_EVALUATION_LANE

## Purpose

Define the minimal repeatable evaluation lane for `Synrail`.

This lane exists so the product can evaluate a bounded run class with:

- explicit baseline
- explicit execution surface
- explicit expected artifact set
- explicit acceptance rule
- explicit non-acceptance rule

The lane is intentionally narrow.

It is not a general benchmark platform.

It is the smallest reproducible contour that lets `Synrail` prove whether a bounded run class is acceptable under kernel rules.

## Core rule

An evaluation lane is valid only if it can answer:

1. what was the trusted baseline?
2. what exact run class was attempted?
3. what exact artifacts were expected?
4. what exact acceptance rule was used?
5. why was the result accepted or not accepted?

If one of these is missing, the lane is incomplete.

## Lane components

Each evaluation lane must define:

- lane id
- target run class
- trusted baseline
- target execution surface
- required artifact set
- acceptance rule
- non-acceptance rule
- blocker classes to record

## Minimal run classes

The initial minimal run classes for `Synrail` are:

- `support_run`
- `exact_retry`

## Required artifact set

At minimum, an evaluation lane must name whether it expects:

- machine-readable final JSON
- modified file list
- diff or unified diff
- read-back proof
- scenario/test proof
- artifact identity
- cleanup status

Different run classes may require different subsets.

## Support lane rule

A support lane is useful if it can prove:

- the execution surface is named
- the support path is reachable
- the run returns machine-readable status
- blockers are surfaced explicitly
- helper/runtime contamination does not silently distort the result

Support lane does not require full bugfix acceptance.

Support lane must still reject false success.

## Exact retry lane rule

An exact retry lane is useful only if it can prove:

- literal exact task identity
- exact baseline identity
- exact required proof bundle
- exact acceptance semantics

If the exact proof bundle is incomplete, the run is not accepted.

## Minimal acceptance rule

A lane result may be accepted only if:

- baseline identity is explicit
- required artifacts are present
- no blocking failure class invalidates the result
- acceptance semantics for the run class are satisfied

## Minimal non-acceptance rule

A lane result must be not accepted if any of the following is true:

- trusted baseline is ambiguous
- execution surface is unsafe for current-run attribution
- required artifacts are missing
- exact prompt identity is missing for exact retry
- result is only narrative without proof artifacts
- a blocker class is active and invalidates trust in the run

## First implementation target

The first concrete lane should be:

- a support-run lane for the current trusted clean Synrail path

Reason:

- it is narrow
- it is already close to reproducible
- it is blocked by named doctor verdicts rather than by uncontrolled ambiguity

## Decision rule

Do not widen the lane into a benchmark suite before one narrow lane is stable and repeatable.
