# SYNRAIL_EVIDENCE_PRECEDENCE

## Purpose

Define which `Synrail` artifacts are authoritative when multiple product surfaces disagree.

This document exists so the kernel resolves contradictions by explicit precedence instead of by accidental optimism.

## Core rule

When `Synrail` artifacts disagree, the product must prefer:

- the deeper evidence surface
- the stricter state
- the fresher lower-level artifact

It must not average contradictions into a softer green state.

## Precedence tiers

### Tier 1. Direct run or direct environment evidence

Examples:

- direct observed doctor-gate facts
- direct provider/credential discoverability facts
- direct proof-bundle completeness facts
- direct execution-surface identity facts

This tier has the highest authority because it is closest to the actual run truth.

### Tier 2. Doctor and lane records

Examples:

- doctor records
- evaluation-lane records

These interpret direct facts into readiness and acceptance implications.

### Tier 3. Progression, transition, recovery, and unlock records

Examples:

- progression records
- transition gates
- recovery records
- unlock records

These depend on lower tiers and must yield when lower tiers are fresher or stricter.

### Tier 4. Runtime truth record

Runtime truth compresses the current operational state.

It is useful, but it must yield to lower-tier contradictions.

### Tier 5. Kernel status record

Kernel status is the most compressed surface.

It is the least authoritative when lower layers disagree.

## Freshness rule

If a higher-tier artifact is older than a refreshed lower-tier artifact, the lower-tier artifact wins.

If freshness cannot be established, `Synrail` must prefer the stricter interpretation.

## Strictness rule

If one artifact says:

- `NOT_ACCEPTABLE`

and another says:

- `ACCEPTABLE`

without a complete refresh chain linking them, `Synrail` must treat the stricter state as authoritative.

## Current practical precedence for the exact-retry path

Current practical order is:

1. doctor gate facts and exact-retry lane facts
2. progression / transition / recovery / unlock records
3. runtime truth record
4. kernel status record

## Contradiction handling rule

When contradiction is detected:

1. identify the deeper artifact
2. identify the fresher artifact
3. choose the stricter state
4. mark higher-level stale surfaces for refresh

## Decision rule

If `Synrail` cannot determine freshness cleanly, it must not upgrade state.

Uncertain precedence must resolve toward the safer interpretation.
