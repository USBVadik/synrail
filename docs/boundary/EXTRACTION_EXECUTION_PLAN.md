# EXTRACTION_EXECUTION_PLAN

## Purpose

Describe the first believable execution plan for extracting the `Synrail` kernel into its own repository once the remaining operational unlock is reached.

This document exists to turn extraction from a broad intention into a nearly mechanical sequence.

It is not extraction approval.

## Precondition

Do not execute this plan until all of the following are true:

1. one accepted proof-complete closure or accepted live-fix confirmation exists through the disciplined incident flow
2. the result has been evaluated honestly via `docs/reference/INCIDENT_FLOW_EVALUATION_TEMPLATE.md`
3. downstream capability-layer work is still explicitly outside the kernel cut

## Core execution rule

Extract by curated copy, not by broad move.

The first extracted repo should be assembled from an explicit allowlist of kernel files.

Do not begin by moving the whole `docs/context` tree.

## Source of truth for the file allowlist

Build the first extraction batch from:

- `docs/boundary/MINIMAL_KERNEL_EXTRACTION_CUT.md`
- `docs/boundary/EXTRACTION_MIGRATION_MAP.md`
- `docs/boundary/REPO_SKELETON_PLAN.md`
- `docs/boundary/SYNRAIL_PRODUCT_BOUNDARY.md`

If a file is not justified by those artifacts, it should not enter the first cut.

## First extraction batch

### Batch 1. Repository shell

Create the new repo with:

- `README.md`
- `docs/core/`
- `docs/boundary/`
- `docs/reference/`
- `tools/reference/`

### Batch 2. Core docs

Copy the Group A and Group B kernel documents first.

### Batch 3. Boundary docs

Copy the curated boundary/extraction docs next:

- `docs/boundary/SYNRAIL_PRODUCT_BOUNDARY.md`
- `docs/boundary/SYNRAIL_ADAPTER_INTERFACES.md`
- `docs/boundary/SYNRAIL_KERNEL_SEPARATION_STATUS.md`
- `docs/boundary/SYNRAIL_EXTRACTION_READINESS_CHECKLIST.md`
- `docs/boundary/MINIMAL_KERNEL_EXTRACTION_CUT.md`
- `docs/boundary/EXTRACTION_MIGRATION_MAP.md`
- `docs/boundary/REPO_SKELETON_PLAN.md`
- `docs/boundary/EXTRACTION_EXECUTION_PLAN.md`

### Batch 4. Reference helpers

Copy the narrow operational helpers:

- `tools/reference/attest_target_surface.sh`
- `tools/reference/require_attested_target_surface.sh`
- `tools/reference/intake_incident_hypothesis.sh`
- `tools/reference/confirm_live_production_fix.sh`
- `tools/reference/incident_operator_flow.sh`

### Batch 5. Curated examples only if still needed

Only after Batches 1–4 are stable, consider adding small sanitized examples.

Do not add raw production history, runtime artifacts, or one-off Node 2 archaeology in the first extraction commit.

## What must stay behind in the first move

Do not copy these into the first extracted repo:

- `USBAGENT`-specific implementation files
- Node 2 runtime residue
- production incident artifacts tied to one live bot
- photoreal/image-enhancer/backend-routing policies for the Gemini agent
- one-off image-quality investigations
- dirty working-tree archaeology
- runtime credential stories

## First commit intent

The first commit in the new repo should say, in effect:

- this is the proof-first control kernel
- these are its contracts
- these are its truth surfaces
- these are its reference controls
- this is not the downstream bot or its capability stack

If the first commit reads like a migration of one battlefield, the cut is wrong.

## Verification after copy

After the first extraction copy:

1. verify directory shape matches `docs/boundary/REPO_SKELETON_PLAN.md`
2. verify no downstream capability-layer files were accidentally included
3. verify the boundary docs still clearly separate core, adapters, proving ground, and downstream capability logic
4. verify helper scripts still reference the same control assumptions after path adjustments

## Immediate post-extraction follow-up

The first follow-up task in the new repo should be:

- clean README and boundary pass

Not:

- new product features
- UI shell
- broad refactors
- downstream integrations

## Decision rule

If we reach the operational unlock, this plan should let us perform the first extraction as a careful copy-and-curate move rather than another planning phase.
