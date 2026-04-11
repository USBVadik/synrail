# SYNRAIL_KERNEL_STATUS_CONTRACT

## Purpose

Define the minimal machine-readable status contract for the `Synrail` kernel.

This document exists so the kernel can eventually emit one structured status artifact instead of requiring operators to reconstruct current truth from many separate records.

## Core rule

A kernel status artifact must summarize current product truth without weakening the deeper evidence layers.

It is a status surface, not a substitute for doctor records, evaluation lanes, recovery records, or closure records.

## Status contract goals

The contract should let a consumer answer:

- what is trusted now
- what run class is currently targeted
- which blocker is active now
- whether exact retry is acceptable now
- what the current progression state is
- what the next allowed transition is
- whether recovery has actually happened
- whether exact-task closure is accepted

## Required fields

A status artifact must include:

- `kernel_identity`
- `trusted_baseline`
- `observed_live_surface`
- `current_target_run_class`
- `doctor_verdicts`
- `lane_status`
- `runtime_truth`
- `progression`
- `transition_gate`
- `recovery`
- `closure`
- `active_blockers`
- `narrow_next_safe_step`
- `evidence_basis`
- `timestamp`

## Field meanings

### `kernel_identity`

Must identify the kernel/product name and current status-contract version.

### `trusted_baseline`

Must identify the current trusted kernel surface.

### `observed_live_surface`

Must identify the observed runtime surface when relevant.

### `current_target_run_class`

The run class currently being prepared or evaluated.

### `doctor_verdicts`

Must summarize the relevant doctor verdicts.

### `lane_status`

Must summarize the relevant evaluation lane status.

### `runtime_truth`

Must summarize the current compact runtime truth snapshot.

### `progression`

Must summarize the current exact-task progression state.

### `transition_gate`

Must summarize the next transition and whether it is allowed.

### `recovery`

Must summarize the current recovery outcome.

### `closure`

Must summarize exact-task closure state.

### `active_blockers`

Named blockers active now.

### `narrow_next_safe_step`

One narrow next move.

### `evidence_basis`

Pointers to the deeper artifacts from which the summary is derived.

## Minimal example shape

```yaml
kernel_identity:
  product: Synrail
  status_contract_version: 1
trusted_baseline:
  path: /tmp/usbagent_clean_clone
  head: 3cc13f6f80378ed303797393f2fe47299780f8a4
observed_live_surface:
  path: /root/USBAGENT_V2_1_STABLE
current_target_run_class: exact_retry
doctor_verdicts:
  exact_retry: NOT_ACCEPTABLE_CREDENTIAL_SURFACE
lane_status:
  exact_retry: NOT_ACCEPTED
runtime_truth:
  progression_state: BLOCKED_READINESS
  unlock_status: NOT_UNLOCKED
progression:
  current_state: BLOCKED_READINESS
transition_gate:
  next_allowed_transition: BLOCKED_READINESS -> READY_FOR_EXACT_RETRY
  result: DENY_WITH_RECOVERY_PATH
recovery:
  outcome: RECOVERY_NOT_PERFORMED
closure:
  state: OPEN
  accepted_result: NO
active_blockers:
  - credential-surface missing
narrow_next_safe_step: complete credential recovery and rerun the re-verification chain
evidence_basis:
  - deeper runtime-truth record
  - deeper transition-gate record
  - deeper recovery-event record
  - deeper closure record
timestamp: 2026-04-11
```

## Anti-misuse rule

A status artifact must not claim greener state than its evidence basis allows.

If deeper artifacts disagree, the status contract must reflect the stricter state.

## Decision rule

If the kernel cannot emit a trustworthy status artifact from its current deeper records, then the status surface is premature and should not be treated as authoritative.
