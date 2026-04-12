# Baseline Runbook 001

## Purpose

Define the smallest executable comparison between the `Synrail` killer path and a materially simpler baseline.

This document exists to make the comparison concrete enough to run, review, and dispute honestly.

## Comparison target

Compare:

- `Synrail` governed exact-task closure path

against:

- one disciplined lightweight operator loop with no explicit kernel

## Scenario shape

Use one bounded exact-task scenario that fits the killer path:

- narrow bugfix
- small patch surface
- plausible false-success risk
- meaningful closure decision

Prefer scenarios in the existing narrow class:

- bounded router/trigger fixes
- small exact-task bugfixes
- controlled patch tasks

## Baseline procedure

The lightweight baseline should be run like this:

1. define one bounded task
2. run one agent attempt
3. perform one human sanity check
4. decide:
   - accept
   - retry once
   - stop as blocked
5. record outcome in a short note

No explicit attestation layer.

No explicit proof-bundle standard.

No doctor verdict.

No formal closure-state model.

## Synrail procedure

The `Synrail` side should be run like this:

1. restate exact-task identity
2. attest target surface if the path is remote or ambiguous
3. run the governed execution path
4. preserve proof-bearing artifacts
5. apply proof-bundle review
6. explicitly accept or reject closure

## Metrics to record

For both sides, record the same minimal metrics:

1. blocker-to-closure cycle count
2. false-success count
3. operator confusion moments
4. proof completeness at decision time
5. recovery cost after misleading output
6. total coordination overhead

## Overhead rule

Do not pretend `Synrail` is free.

The comparison must also record:

- extra steps introduced by `Synrail`
- extra reading burden
- extra artifact handling burden
- extra operator coordination time

The product claim only survives if the truth/recovery gains are worth that overhead.

## What counts as a win for Synrail

`Synrail` wins only if:

- it prevents or cleanly rejects a false completion the baseline would likely accept
- or it reaches a truthful blocker/closure state faster and with less ambiguity
- or it makes recovery from misleading agent output meaningfully cheaper

## What counts as a loss for Synrail

`Synrail` loses if:

- it adds many steps without reducing false-success risk
- it slows closure without improving truth quality
- it produces better language but not better decisions

## Minimum evidence artifact

The comparison should end with one compact evaluation record containing:

- scenario identity
- baseline outcome
- Synrail outcome
- metric comparison
- honest verdict:
  - `Synrail better`
  - `baseline good enough`
  - `unclear`

## Decision rule

If the first comparison is inconclusive, do not broaden scope immediately.

First decide whether the problem was:

- bad scenario selection
- weak metric capture
- unfaithful baseline replay
- or genuine lack of advantage on the killer path
