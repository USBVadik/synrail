# Synrail Docs Map

This repository is intentionally small and wedge-first.

Use this map when you want the fastest way to orient yourself without reading every document in order.

## 1. Core

Start here when you want to understand the kernel itself:

- `core/SYNRAIL_RUNTIME_TRUTH_SURFACE.md`
- `core/SYNRAIL_EVIDENCE_PRECEDENCE.md`
- `core/SYNRAIL_DOCTOR.md`
- `core/SYNRAIL_EXACT_TASK_CLOSURE_SPEC.md`
- `core/SYNRAIL_KERNEL_STATUS_CONTRACT.md`

These documents describe how Synrail decides what is trustworthy, what is blocked, and what can be accepted.

## 2. Boundary

Read these when you want to understand what belongs in Synrail and what stays outside:

- `boundary/SYNRAIL_PRODUCT_BOUNDARY.md`
- `boundary/SYNRAIL_ADAPTER_INTERFACES.md`
- `boundary/SYNRAIL_KERNEL_SEPARATION_STATUS.md`
- `boundary/SYNRAIL_EXTRACTION_READINESS_CHECKLIST.md`

These define the product line between:

- the control kernel
- adapters and execution surfaces
- proving-ground evidence
- downstream capability layers

## 3. Extraction

Read these when you want to understand how the separate repo move is staged:

- `boundary/MINIMAL_KERNEL_EXTRACTION_CUT.md`
- `boundary/EXTRACTION_MIGRATION_MAP.md`
- `boundary/REPO_SKELETON_PLAN.md`
- `boundary/EXTRACTION_EXECUTION_PLAN.md`
- `boundary/FIRST_EXTRACTION_COMMIT_PLAN.md`

## 4. Reference Behaviors

Read these when you want the small operational slices that shaped the proving-ground discipline:

- `reference/TARGET_SURFACE_ATTESTATION.md`
- `reference/INCIDENT_AND_PRODUCTION_CONFIRMATION_HELPERS.md`
- `reference/DIRECT_LOOP_SPEC.md`
- `reference/INCIDENT_FLOW_EVALUATION_TEMPLATE.md`

## 5. Reference Helpers

The scripts under `../tools/reference/` are small reference helpers, not a full orchestration product:

- `attest_target_surface.sh`
- `require_attested_target_surface.sh`
- `intake_incident_hypothesis.sh`
- `confirm_live_production_fix.sh`
- `incident_operator_flow.sh`

## Reading Rule

If you only read three things first, use:

1. `core/SYNRAIL_RUNTIME_TRUTH_SURFACE.md`
2. `boundary/SYNRAIL_PRODUCT_BOUNDARY.md`
3. `core/SYNRAIL_EXACT_TASK_CLOSURE_SPEC.md`
