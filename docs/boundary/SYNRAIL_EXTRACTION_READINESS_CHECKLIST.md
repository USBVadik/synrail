# SYNRAIL_EXTRACTION_READINESS_CHECKLIST

## Purpose

Define the minimal checklist that must be satisfied before `Synrail` is extracted into its own dedicated repository.

This checklist exists so extraction is based on kernel maturity rather than on the mere number of artifacts.

## Checklist

### 1. Product boundary is explicit

Status:

- `PASS`

Evidence:

- `docs/boundary/SYNRAIL_PRODUCT_BOUNDARY.md`

### 2. Doctor verdicts are concrete

Status:

- `PASS`

Evidence:

- `docs/core/SYNRAIL_DOCTOR.md`
- `docs/core/SYNRAIL_DOCTOR_RECORD_SPEC.md`

### 3. Minimal repeatable evaluation lanes exist

Status:

- `PASS`

Evidence:

- `docs/core/SYNRAIL_EVALUATION_LANE.md`

### 4. At least one proof-complete exact-task cycle under kernel rules exists

Status:

- `PASS`

Evidence:

- first exact-task success artifact remains in the proving ground and is referenced in the originating records

Why:

- `RUN_011` returned a success artifact under the exact-retry path
- the artifact contains a real `commit_hash`
- the artifact contains concrete `modified_files`
- the artifact contains a literal `git_diff`
- the artifact reports `cleanup_status.success = true`
- the result came through the governed exact executor path rather than through a live incident-only path
- this now satisfies the minimum operational unlock that had been blocking extraction readiness

### 5. Kernel can be described without treating one downstream bot as the product

Status:

- `PASS`

Evidence:

- `docs/boundary/SYNRAIL_PRODUCT_BOUNDARY.md`

### 6. Adapter boundary is visible

Status:

- `PASS`

Reason:

- adapter-like surfaces are named
- a minimal adapter interface model now exists

Evidence:

- `docs/boundary/SYNRAIL_PRODUCT_BOUNDARY.md`
- `docs/boundary/SYNRAIL_ADAPTER_INTERFACES.md`

### 7. Future shell is separated from the kernel

Status:

- `PASS`

Evidence:

- `docs/boundary/SYNRAIL_PRODUCT_BOUNDARY.md`

## Separation reference

A current separation-status summary now exists in:

- `docs/boundary/SYNRAIL_KERNEL_SEPARATION_STATUS.md`
- `docs/boundary/SYNRAIL_KERNEL_SEPARATION_STATUS.md`

This complements the extraction checklist by separating architectural/product separation from operational separation.

## Current assessment

Current extraction readiness:

- `READY FOR FIRST EXTRACTION MOVE`

Reason:

- the kernel is substantially clearer now
- the kernel cut is also substantially clearer now
- at least one proof-complete exact-task cycle now exists under kernel rules
- the disciplined incident flow has also already reached multiple accepted live outcomes on fresh narrow incidents
- the strongest remaining work is no longer readiness proof, but careful execution of the first extraction move

## Narrow next step

The strongest next step before extraction is:

- use:
  - `docs/boundary/EXTRACTION_EXECUTION_PLAN.md`
  as the active mechanical move-order
- use:
  - `docs/boundary/FIRST_EXTRACTION_COMMIT_PLAN.md`
  as the first bounded extraction payload
- keep incident flow discipline in place for fresh runtime issues during extraction prep
- do not widen the first extraction cut beyond the already-defined allowlist

## Decision rule

Do not extract if item 4 falls back out of `PASS` or if the first extraction move would exceed the bounded first-cut allowlist.

`Synrail` should move into its own repository when the kernel is not only well-described, but also proven to close at least one exact-task cycle under its own acceptance semantics.
