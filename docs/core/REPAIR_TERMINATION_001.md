# REPAIR_TERMINATION_001

## Purpose

Define the first explicit repair termination contract for `Synrail`.

This document exists to stop packet-first continuation from becoming one controlled but endless retry loop.

## Core rule

A repair loop must not continue forever just because the contour is still machine-readable.

The runtime now needs one explicit answer to a stricter question:

- when should `resume` stop trying to repair this contour and tell the operator to stop?

## Current termination reasons

The first bounded termination contract now recognizes:

1. `NON_RESUMABLE`
2. `MAX_REPAIR_ATTEMPTS`
3. `NO_PROGRESS_DETECTED`

These reasons are not interchangeable.

## `NON_RESUMABLE`

This is the pre-existing hard boundary.

It means:

- the contour should no longer continue through `resume`
- the next move must be a new run or another named non-resumable path

## `MAX_REPAIR_ATTEMPTS`

This is the bounded retry ceiling.

Current sprint default:

- `MAX_REPAIR_ATTEMPTS = 3`

Meaning:

- once three repair attempts are already recorded in the repair-history chain, the next packet must terminate continuation instead of inviting one more blind retry

## `NO_PROGRESS_DETECTED`

This is the bounded convergence check.

Current sprint default:

- `NO_PROGRESS_WINDOW = 2`

Meaning:

- if the last two repair-history entries both show no real step progression
- and they are still stuck on the same active repair step
- the next packet must terminate continuation instead of pretending the loop is still moving

## Required recording

Termination must preserve the full repair-history chain accumulated so far.

The runtime must not stop by erasing history.

At minimum the packet-facing truth must record:

- `status`
- `reason`
- `attempt_count`
- `max_attempts`
- `no_progress_window`
- `stalled_step_id`
- `next_action`

## Runtime rule

If the packet already says `TERMINATE`, then `resume` must stop before starting another repair attempt.

That stop must be machine-readable and operator-visible.

## Why this matters

This is a kernel-hardening move, not richer continuation vocabulary.

It protects against one of the most expensive forms of false confidence:

- a loop that looks disciplined
- but is no longer converging

## Current reading

The shortest honest reading is:

- continuation now needs both repairability and termination truth
- repair history alone is not enough if the runtime never uses it to stop
- the next proof step is one explicit convergence pressure-test where repeated non-progress now terminates the loop honestly
