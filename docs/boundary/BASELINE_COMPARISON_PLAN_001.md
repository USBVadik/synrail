# Baseline Comparison Plan 001

## Purpose

Define the simplest honest baseline against which `Synrail` should now be compared.

This document exists to prevent the project from treating internal coherence as proof of product value.

## Comparison question

The question is not:

- is `Synrail` conceptually richer

The question is:

- does `Synrail` outperform a materially simpler operator loop on the killer path

## Current comparison target

Compare `Synrail` against:

- a disciplined operator loop with no explicit kernel

That baseline means:

1. one human/operator
2. one bounded task statement
3. one agent run
4. one manual sanity check
5. one manual retry or stop decision

No doctor layer.

No explicit truth surfaces.

No proof-bundle standard.

No formal transition/closure model.

## Why this baseline is the right one now

It is honest because it is:

- simple
- cheap
- plausible in real teams
- strong enough to beat if `Synrail` truly has product value

If `Synrail` cannot clearly beat this baseline on the killer path, then the kernel is still too heavy for its current value.

## Metrics to compare

Use a narrow metric set:

1. blocker-to-closure cycle count
2. false-success rate
3. operator confusion about current state
4. proof completeness at decision time
5. recovery cost after a wrong claim

## What counts as `Synrail` advantage

`Synrail` shows real advantage only if it produces at least one of the following with acceptable overhead:

- fewer false success claims
- faster convergence to a truthful blocker
- more reliable acceptance/rejection decisions
- lower cost of recovering from misleading agent output

## What does not count

These do not count as product advantage:

- cleaner terminology alone
- prettier repo structure alone
- more documents alone
- stronger internal framing without measurable change on the killer path

## Minimum comparison design

The minimum useful comparison is:

1. choose one narrow exact-task scenario
2. replay it through a simpler operator loop
3. compare it against the governed `Synrail` path
4. record where `Synrail` helped and where it added overhead

## Decision rule

If comparison shows that `Synrail` adds complexity without reducing false completion or recovery cost, then the core must shrink again.

If comparison shows a real advantage on the killer path, then that path becomes the product wedge.
