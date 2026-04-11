# EXTRACTION_MIGRATION_MAP

## Purpose

Translate the current extraction discussion into a concrete migration map for a future dedicated `Synrail` repository.

This document exists so extraction can later become a technical move rather than another broad planning phase.

It is not an extraction approval.

## Core rule

Move the kernel by stable behavior groups, not by historical chronology.

The new repository should be assembled around the kernel wedge, not around the order in which artifacts happened to be created.

## Migration groups

### Group A. Kernel contracts

Move first because they define the core acceptance language:

- `docs/core/SAFE_PROMOTION.md`
- `docs/core/FORMAL_VALIDATION.md`
- `docs/core/SYNRAIL_PROOF_BUNDLE_STANDARD.md`
- `docs/core/SYNRAIL_EXACT_TASK_CLOSURE_SPEC.md`
- `docs/core/SYNRAIL_EXACT_TASK_PROGRESSION.md`
- `docs/core/SYNRAIL_TRANSITION_GATE_STANDARD.md`
- `docs/core/SYNRAIL_RECOVERY_EVENT_STANDARD.md`
- `docs/core/SYNRAIL_READINESS_UNLOCK_SPEC.md`
- `docs/core/SYNRAIL_KERNEL_STATUS_CONTRACT.md`

### Group B. Kernel truth surfaces

Move next because they define how the kernel compresses and evaluates reality:

- `docs/core/SYNRAIL_RUNTIME_TRUTH_SURFACE.md`
- `docs/core/SYNRAIL_RUNTIME_TRUTH_RECORD_SPEC.md`
- `docs/core/SYNRAIL_EVIDENCE_PRECEDENCE.md`
- `docs/core/SYNRAIL_STATE_REFRESH_CHAIN.md`
- `SYNRAIL_CONSISTENCY_CHECK_*.md` as reference patterns
- `docs/core/SYNRAIL_DOCTOR.md`
- `docs/core/SYNRAIL_DOCTOR_RECORD_SPEC.md`
- `docs/core/SYNRAIL_EVALUATION_LANE.md`

### Group C. Boundary and extraction definitions

Move early because they prevent the new repo from inheriting battlefield identity:

- `docs/boundary/SYNRAIL_PRODUCT_BOUNDARY.md`
- `docs/boundary/SYNRAIL_ADAPTER_INTERFACES.md`
- `docs/boundary/SYNRAIL_KERNEL_SEPARATION_STATUS.md`
- `docs/boundary/SYNRAIL_EXTRACTION_READINESS_CHECKLIST.md`
- `docs/boundary/MINIMAL_KERNEL_EXTRACTION_CUT.md`
- `docs/boundary/EXTRACTION_MIGRATION_MAP.md`

### Group D. Incident and runtime-truth controls

Move as the first reference implementations of narrow operational kernel behavior:

- `docs/reference/TARGET_SURFACE_ATTESTATION.md`
- `docs/reference/INCIDENT_AND_PRODUCTION_CONFIRMATION_HELPERS.md`
- `docs/reference/DIRECT_LOOP_SPEC.md`
- `docs/reference/INCIDENT_FLOW_EVALUATION_TEMPLATE.md`
- `tools/reference/require_attested_target_surface.sh`
- `tools/reference/intake_incident_hypothesis.sh`
- `tools/reference/confirm_live_production_fix.sh`
- `tools/reference/incident_operator_flow.sh`

### Group E. Exact-run supervision references

Move only if we still want the new repo to carry narrow reference implementations for run supervision:

- `tools/reference/check_isolation.sh`
- `tools/reference/classify_attempt.sh`
- `tools/reference/fetch_terminal_artifact.sh`
- `MINIMAL_EXECUTION_SUPERVISION_SLICE.md`

These are valuable, but they are one step closer to proving-ground operations than Groups A-D.

## What should stay here for now

Keep in the current repo until operational proof is stronger:

- proving-ground incidents like `NODE2_IMAGE_TRIGGER_FIX_001`
- runtime artifacts under `docs/context/runtime_artifacts/`
- incident-specific records
- production confirmation records for one live bot
- dirty repo archaeology
- one-off support / retry run records
- environment-specific recovery records
- downstream agent capability-layer work such as:
  - prompt-enhancer tuning
  - backend suitability routing
  - photoreal prompt-class policies
  - image-model quality heuristics

These may later become examples or test fixtures.

They should not shape the first cut of the separate kernel repo.

## Suggested migration order

When extraction becomes justified, move in this order:

1. Group A
2. Group B
3. Group C
4. Group D
5. Group E only if still useful
6. selected proving-ground examples only after explicit curation

This order keeps the first extracted repo centered on:

- kernel contracts
- kernel truth surfaces
- kernel boundary
- narrow operational reference behaviors

## What the first extracted repo should contain

At minimum:

- `docs/core/` for kernel contracts and truth surfaces
- `docs/boundary/` for product boundary and adapter boundary
- `tools/reference/` for attestation / intake / confirmation / operator flow helpers
- one short `README` explaining the wedge:
  - claims are not accepted reality without proof

Concrete target shape now also exists in:

- `docs/boundary/REPO_SKELETON_PLAN.md`

It should not initially try to contain:

- every historical record
- every proving-ground incident
- every runtime artifact
- every support-run experiment

## Pre-extraction freeze rule

Until the operational unlock happens:

- do not start physically moving files yet
- do not rename everything for aesthetic consistency
- do not build repo shell/UI around an unproven cut

Keep planning concrete, but keep the actual move gated.

## Operational unlock for this map

This migration map becomes actionable only after:

1. one accepted proof-complete closure or accepted live-fix confirmation through the new incident flow
2. one honest evaluation using `docs/reference/INCIDENT_FLOW_EVALUATION_TEMPLATE.md`
3. downstream capability-layer experiments are explicitly kept outside the kernel cut

## Decision rule

The migration map should reduce extraction hesitation later.

It should not create extraction pressure now.
