# FIRST_EXTRACTION_COMMIT_PLAN

## Purpose

Describe the first realistic commit that should land in a new dedicated `Synrail` repository once extraction is operationally unlocked.

This document exists so the first commit is intentionally small, clean, and identity-defining.

## Commit goal

The first extraction commit should establish:

- what `Synrail` is
- what belongs to the kernel
- what reference controls come with it
- what explicitly stays outside the repo for now

It should not try to prove historical completeness.

## Commit contents

### 1. Top-level shell

Create:

- `README.md`
- `docs/core/`
- `docs/boundary/`
- `docs/reference/`
- `tools/reference/`

### 2. Core docs to include

Include the kernel contract and truth-surface docs from the extraction cut.

Minimum intended set:

- `docs/core/SAFE_PROMOTION.md`
- `docs/core/FORMAL_VALIDATION.md`
- `docs/core/SYNRAIL_PROOF_BUNDLE_STANDARD.md`
- `docs/core/SYNRAIL_EXACT_TASK_CLOSURE_SPEC.md`
- `docs/core/SYNRAIL_EXACT_TASK_PROGRESSION.md`
- `docs/core/SYNRAIL_TRANSITION_GATE_STANDARD.md`
- `docs/core/SYNRAIL_RECOVERY_EVENT_STANDARD.md`
- `docs/core/SYNRAIL_READINESS_UNLOCK_SPEC.md`
- `docs/core/SYNRAIL_KERNEL_STATUS_CONTRACT.md`
- `docs/core/SYNRAIL_RUNTIME_TRUTH_SURFACE.md`
- `docs/core/SYNRAIL_RUNTIME_TRUTH_RECORD_SPEC.md`
- `docs/core/SYNRAIL_EVIDENCE_PRECEDENCE.md`
- `docs/core/SYNRAIL_STATE_REFRESH_CHAIN.md`
- `docs/core/SYNRAIL_DOCTOR.md`
- `docs/core/SYNRAIL_DOCTOR_RECORD_SPEC.md`
- `docs/core/SYNRAIL_EVALUATION_LANE.md`

### 3. Boundary docs to include

Minimum intended set:

- `docs/boundary/SYNRAIL_PRODUCT_BOUNDARY.md`
- `docs/boundary/SYNRAIL_ADAPTER_INTERFACES.md`
- `docs/boundary/SYNRAIL_KERNEL_SEPARATION_STATUS.md`
- `docs/boundary/SYNRAIL_EXTRACTION_READINESS_CHECKLIST.md`
- `docs/boundary/MINIMAL_KERNEL_EXTRACTION_CUT.md`
- `docs/boundary/EXTRACTION_MIGRATION_MAP.md`
- `docs/boundary/REPO_SKELETON_PLAN.md`
- `docs/boundary/EXTRACTION_EXECUTION_PLAN.md`
- `docs/boundary/FIRST_EXTRACTION_COMMIT_PLAN.md`

### 4. Reference helpers to include

Minimum intended set:

- `attest_target_surface.sh`
- `require_attested_target_surface.sh`
- `intake_incident_hypothesis.sh`
- `confirm_live_production_fix.sh`
- `incident_operator_flow.sh`

## README outline

The first `README.md` should cover only:

1. wedge:
   - claims are not accepted reality without proof
2. kernel scope:
   - trust, acceptance, recovery, evaluation, closure
3. what is not included:
   - downstream bot logic
   - downstream capability layers
   - battlefield runtime history
4. reference helpers:
   - attestation
   - bounded intake
   - production confirmation
   - incident flow

## What must not enter the first commit

Do not include:

- downstream product runtime files
- proving-ground incident records
- downstream photoreal/image-routing policy docs
- runtime artifact dumps
- one-off debugging shells or transport archaeology
- battle-specific backups

## Commit message intent

A good first commit message would communicate:

- initialize Synrail kernel extraction cut

Not:

- migrate all docs
- move project into new repo
- import battlefield history

## Verification checklist before making the commit

Before creating the first commit in the new repo, verify:

1. the copied files match the allowlist
2. the repo can be understood without mentioning one downstream product as the product
3. downstream agent capability-layer files were not copied by accident
4. helper scripts still make sense under `tools/reference/`
5. the boundary docs remain internally consistent

## Decision rule

This plan becomes actionable only after the operational extraction gate opens.

Until then, it should be treated as a final staging artifact, not as permission to move files.
