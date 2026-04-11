# SYNRAIL_STATE_REFRESH_CHAIN

## Purpose

Define the required re-verification and refresh order after any real state-changing event in `Synrail`.

This document exists so product state does not become internally inconsistent after recovery, readiness change, or closure progress.

## Core rule

If a lower-level truth artifact changes, all dependent higher-level artifacts must be refreshed in order.

No higher-level artifact may claim greener state than the last refreshed lower-level evidence allows.

## Why this matters

`Synrail` now has multiple linked state surfaces:

- doctor records
- evaluation lanes
- runtime truth
- progression records
- transition gates
- recovery records
- unlock records
- closure records
- kernel status

Without a refresh chain, these can drift out of sync.

## Refresh order

When a real recovery or readiness-affecting change happens, refresh in this order:

### 1. Surface-specific doctor records

Refresh the directly affected doctor records first.

For the current exact-retry path this means at minimum:

- `DOCTOR_RUN_CREDENTIAL_SURFACE_001`
- `DOCTOR_RUN_SUPPORT_READINESS_001`
- `DOCTOR_RUN_EXACT_RETRY_READINESS_001`

### 2. Evaluation lane

Refresh the affected lane after the doctor records.

For the current exact retry path:

- `EVALUATION_LANE_EXACT_RETRY_001`

### 3. Recovery and unlock records

Then refresh:

- `RECOVERY_EVENT_RECORD_001`
- `READINESS_UNLOCK_RECORD_001`

### 4. Progression and transition records

Then refresh:

- `EXACT_TASK_PROGRESSION_RECORD_001`
- `EXACT_RETRY_TRANSITION_GATE_001`

### 5. Runtime truth

Then refresh:

- `RUNTIME_TRUTH_RECORD_001`

### 6. Closure record

Then refresh:

- `EXACT_TASK_CLOSURE_RECORD_001`

### 7. Kernel status

Only after all dependent lower layers are refreshed, update:

- `KERNEL_STATUS_RECORD_001`

## Refresh trigger types

This chain should run after:

- accepted recovery event
- readiness unlock change
- transition-gate result change
- exact retry attempt completion
- proof-bundle completeness change
- exact-task closure state change

## Anti-drift rule

If a higher-level record is updated without its required lower-level refreshes, that higher-level record is stale.

A stale record must not be treated as authoritative.

## Current strongest use case

The next expected real use of this chain is:

- credential recovery on the intended exact-retry surface
- then exact-retry readiness re-verification

## Decision rule

When in doubt, refresh more of the chain, not less.

`Synrail` should prefer temporary redundancy over stale state.
