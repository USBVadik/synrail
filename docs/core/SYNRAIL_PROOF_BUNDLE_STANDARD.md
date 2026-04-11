# SYNRAIL_PROOF_BUNDLE_STANDARD

## Purpose

Define the minimal product-standard proof bundle required for exact-task acceptance in `Synrail`.

This document exists so exact-task closure is judged by one explicit proof standard rather than by scattered expectations across execution policy, evaluation lanes, and session memory.

## Core rule

No exact-task result is accepted unless a full proof bundle is present and reviewable.

`final_json_received` is never enough.

## What proof bundle is

A proof bundle is the minimum reviewable artifact set required to distinguish:

- claimed result
- observed activity
- accepted exact-task closure

## What proof bundle is not

Proof bundle is not:

- narrative diagnosis alone
- final JSON alone
- a diff without read-back confirmation
- a read-back without task-level scenario proof
- a tool log that does not prove the exact-task outcome

## Required sections for exact-task acceptance

### 1. Final machine-readable result

Required:

- final JSON or equivalent machine-readable terminal result artifact

Purpose:

- prove the run reached a structured terminal state

### 2. Modified-files proof

Required:

- explicit modified file list
- explicit empty list if no files changed

Purpose:

- prevent hidden changes or hand-wavy file claims

### 3. Diff/provenance proof

Required:

- diff or unified diff for the exact run
- or explicit proof that no diff exists for the exact run

Purpose:

- bind the claimed result to real current-run artifact provenance

### 4. Read-back proof

Required:

- direct read-back of the relevant changed logic
- enough evidence to confirm the exact path that supposedly changed

Purpose:

- prevent accepting a claimed fix that is not actually present in the file state

### 5. Scenario-test proof

Required:

- case-specific evidence that the target behavior now matches expected behavior
- for `NODE2_IMAGE_TRIGGER_FIX_001`, this means proof around text-routing vs image-trigger behavior

Purpose:

- prevent accepting code-shape changes without task-behavior proof

### 6. Artifact identity

Required:

- trusted baseline identity
- execution surface identity
- exact prompt identity
- task id identity

Purpose:

- prevent acceptance when exact-task semantics drifted or the wrong surface was evaluated

### 7. Cleanup status

Required:

- explicit cleanup status for temp branch/process/artifact paths when the lane depends on them

Purpose:

- prevent accepting runs that leave execution residue and ambiguous state

## Acceptance rule

An exact-task result is accepted only when:

- all required proof sections are present
- no active blocker invalidates trust in the run
- exact-task identity is preserved
- the proof sections agree with each other
- the final result does not rely on narrative claims stronger than the artifact basis allows

## Non-acceptance rule

Do not accept when:

- any proof section is missing
- final JSON is present but proof sections are incomplete
- read-back contradicts the claimed fix
- scenario proof is absent or off-scope
- artifact identity is ambiguous
- cleanup status is unknown for a run class that requires it

## Relation to existing Synrail artifacts

This standard should be read together with:

- `EXECUTION_POLICY_NODE2_IMAGE_TRIGGER_FIX_001`
- `EVALUATION_LANE_EXACT_RETRY_001`
- `SAFE_PROMOTION`

The purpose of this document is not to replace those artifacts, but to unify the proof-complete acceptance standard they imply.

## Minimal success condition

This layer is successful when the kernel can answer one narrow question without hand-waving:

- do we have an accepted exact-task result, or only a claimed one?

## Decision rule

If the proof bundle cannot separate claimed closure from accepted closure, the exact task remains open.
