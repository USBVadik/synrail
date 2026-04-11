# REPO_SKELETON_PLAN

## Purpose

Describe the first believable directory skeleton for a future dedicated `Synrail` repository.

This document exists so the eventual extraction can start from a clean target shape instead of improvising structure during the move.

It is not a signal to create the repository yet.

## Core rule

The first extracted repository should optimize for:

- kernel clarity
- boundary clarity
- narrow reference implementations
- low proving-ground contamination

It should not optimize for:

- historical completeness
- preserving every existing path name
- broad UI or shell ambition

## Proposed top-level layout

```text
synrail/
  README.md
  docs/
    core/
    boundary/
    reference/
  tools/
    reference/
  examples/
  fixtures/
```

## Top-level intent

### `README.md`

Should explain only:

- the wedge
- what `Synrail` accepts or rejects
- what belongs to kernel vs adapters vs proving ground

### `docs/core/`

Should contain kernel contracts and truth surfaces.

Recommended first contents:

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

### `docs/boundary/`

Should contain extraction and boundary-setting artifacts.

Recommended first contents:

- `docs/boundary/SYNRAIL_PRODUCT_BOUNDARY.md`
- `docs/boundary/SYNRAIL_ADAPTER_INTERFACES.md`
- `docs/boundary/SYNRAIL_KERNEL_SEPARATION_STATUS.md`
- `docs/boundary/SYNRAIL_EXTRACTION_READINESS_CHECKLIST.md`
- `docs/boundary/MINIMAL_KERNEL_EXTRACTION_CUT.md`
- `docs/boundary/EXTRACTION_MIGRATION_MAP.md`
- `docs/boundary/REPO_SKELETON_PLAN.md`

### `docs/reference/`

Should contain narrow operational reference behaviors, not battlefield history.

Recommended first contents:

- `docs/reference/TARGET_SURFACE_ATTESTATION.md`
- `docs/reference/INCIDENT_AND_PRODUCTION_CONFIRMATION_HELPERS.md`
- `docs/reference/DIRECT_LOOP_SPEC.md`
- `docs/reference/INCIDENT_FLOW_EVALUATION_TEMPLATE.md`
- `MINIMAL_EXECUTION_SUPERVISION_SLICE.md` only if we still want those references in the first cut

### `tools/reference/`

Should contain only the narrow reference helpers that express kernel behavior clearly.

Recommended first contents:

- `require_attested_target_surface.sh`
- `attest_target_surface.sh`
- `intake_incident_hypothesis.sh`
- `confirm_live_production_fix.sh`
- `incident_operator_flow.sh`

Optional later additions:

- `check_isolation.sh`
- `classify_attempt.sh`
- `fetch_terminal_artifact.sh`

### `examples/`

Should stay small.

Use only curated examples that demonstrate kernel behavior without dragging in one whole battlefield.

Possible future contents:

- one sanitized incident-hypothesis example
- one sanitized production-confirmation example
- one sanitized exact-task proof-bundle example

### `fixtures/`

Optional.

Use only if we decide to preserve small machine-readable samples for tests or demonstrations.

Do not dump raw runtime history here.

## What should remain in the current repo

The current repo should continue to hold:

- live proving-ground incident records
- runtime artifacts
- one-off support / retry runs
- dirty repo archaeology
- downstream bot specifics
- environment-specific recovery records
- downstream capability-layer policies for one agent, including:
  - image prompt enhancers
  - backend routing rules
  - photoreal quality heuristics

These are still useful here.

They should not dominate the first extracted `Synrail` repo.

## Naming rule

When the move eventually happens:

- preserve document names where practical
- prefer grouping by role over renaming for style
- only rename if it clearly reduces confusion

This keeps the first extraction focused on boundary clarity rather than churn.

## First extraction batch

If the operational gate opens, the safest first batch is:

1. `docs/core/`
2. `docs/boundary/`
3. `tools/reference/`
4. minimal `README.md`

Everything else can wait.

## Decision rule

The first extracted repo should feel smaller and cleaner than the current battlefield.

If the planned skeleton still looks like a historical archive, the cut is wrong.
