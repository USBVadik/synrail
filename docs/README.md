# Synrail Docs Map

This repository is intentionally small and wedge-first.

Use this map when you want the fastest way to orient yourself without reading every document in order.

## 1. Active path

Start here when you want the current product wedge rather than the full repo history:

- `boundary/EXECUTABLE_STACK_READING_001.md`
- `boundary/OUTCOME_LATTICE_001.md`
- `boundary/TRANSITION_LATTICE_001.md`
- `boundary/REENTRY_LATTICE_001.md`
- `boundary/TRIO_READING_001.md`
- `boundary/COST_OF_CONTROL_001.md`
- `boundary/HYBRID_STATUS_001.md`
- `boundary/KILLER_PATH_001.md`
- `boundary/BASELINE_COMPARISON_RECORD_001.md`
- `boundary/MINIMUM_UNDENIABLE_CORE_001.md`

These are the shortest current path to:

- what Synrail is trying to win
- why it currently looks better than a simpler baseline on that path
- what its current control cost actually looks like across the measured scenario set
- what should remain in the core
- what the next pressure-testing tranche should now measure rather than merely describe

Then, if you want the practical “when should we actually use this?” rule, read:

- `boundary/APPLICATION_POLICY_001.md`
- `boundary/HYBRID_SUBSET_001.md`
- `boundary/HYBRID_STATUS_001.md`

## 2. Core

Start here when you want to understand the kernel itself:

- `core/SYNRAIL_RUNTIME_TRUTH_SURFACE.md`
- `core/SYNRAIL_EVIDENCE_PRECEDENCE.md`
- `core/SYNRAIL_DOCTOR.md`
- `core/DOCTOR_001.md`
- `core/DOCTOR_PRESSURE_TEST_001.md`
- `core/DOCTOR_PRESSURE_TEST_002.md`
- `core/SYNRAIL_EXACT_TASK_CLOSURE_SPEC.md`
- `core/SYNRAIL_KERNEL_STATUS_CONTRACT.md`
- `core/RUN_STATE_SCHEMA_001.md`
- `core/EXECUTION_SPINE_001.md`
- `core/GATE_SET_001.md`
- `core/PROOF_BUNDLE_ASSEMBLER_001.md`
- `core/GOVERNED_PATH_PREPARATION_001.md`
- `core/GOVERNED_PATH_COST_REDUCTION_001.md`
- `core/REPAIR_HANDOFF_001.md`
- `core/REPAIR_PACKET_001.md`
- `core/CLOSURE_ENGINE_001.md`
- `core/REFRESH_CHAIN_AUTOMATION_001.md`
- `core/TERMINAL_OPERATOR_UX_001.md`
- `core/ORCHESTRATION_001.md`
- `core/BASELINE_HARNESS_001.md`
- `core/MODE_SELECTOR_001.md`
- `core/MODE_SELECTION_RUN_001.md`
- `core/MODE_SELECTION_RUN_002.md`
- `core/MODE_SELECTION_RUN_003.md`
- `core/MODE_SELECTION_RUN_004.md`
- `core/EXECUTABLE_LOOP_PREPARED_RUN_001.md`
- `core/EXECUTABLE_LOOP_SELECTED_PREPARED_RUN_001.md`
- `core/EXECUTABLE_LOOP_SELECTION_BLOCKED_RUN_001.md`
- `core/EXECUTABLE_LOOP_RUNTIME_RESUME_RUN_001.md`
- `core/EXECUTABLE_LOOP_RUNTIME_RESUME_RUN_002.md`
- `core/EXECUTABLE_LOOP_RUNTIME_RESUME_RUN_003.md`
- `core/EXECUTABLE_LOOP_RUNTIME_RESUME_RUN_004.md`
- `core/EXECUTABLE_LOOP_RUNTIME_NON_RESUMABLE_RUN_001.md`
- `core/EXECUTABLE_LOOP_RUNTIME_NON_RESUMABLE_RUN_002.md`
- `core/EXECUTABLE_LOOP_RUNTIME_NON_RESUMABLE_RUN_003.md`
- `core/EXECUTABLE_LOOP_COMPOUND_CONTINUATION_RUN_001.md`
- `core/EXECUTABLE_LOOP_COMPOUND_CONTINUATION_RUN_002.md`
- `core/EXECUTABLE_LOOP_COMPOUND_CONTINUATION_RUN_003.md`
- `core/EXECUTABLE_LOOP_COMPOUND_CONTINUATION_RUN_004.md`
- `core/EXECUTABLE_LOOP_COMPOUND_CONTINUATION_RUN_005.md`
- `core/SCHEMA_VALIDATION_001.md`
- `core/EXECUTABLE_LOOP_RUN_001.md`
- `core/EXECUTABLE_LOOP_RUN_002.md`
- `core/EXECUTABLE_LOOP_RUN_003.md`
- `core/EXECUTABLE_LOOP_ACCEPTED_RUN_001.md`
- `core/EXECUTABLE_LOOP_BLOCKED_RUN_001.md`
- `core/EXECUTABLE_LOOP_REENTRY_RUN_001.md`
- `core/EXECUTABLE_LOOP_PARTIAL_REENTRY_RUN_001.md`
- `core/EXECUTABLE_LOOP_DEGRADED_REENTRY_RUN_001.md`
- `core/EXECUTABLE_LOOP_COMPOUND_RUN_001.md`
- `core/EXECUTABLE_LOOP_HYBRID_PRESSURE_RUN_002.md`
- `core/EXECUTABLE_LOOP_HYBRID_PRESSURE_RUN_003.md`
- `schemas/spine_block_report_v0.schema.json`
- `schemas/canonical_run_artifact_v0.schema.json`
- `schemas/worked_orchestration_artifact_v0.schema.json`
- `schemas/repair_packet_v0.schema.json`
- `schemas/comparison_input_v1.schema.json`
- `schemas/baseline_comparison_record_v1.schema.json`

These documents describe how Synrail decides what is trustworthy, what is blocked, and what can be accepted.

For the cleanest machine-readable entrypoint into the worked runs, start with:

- `../fixtures/executable_loop_run_001/run.json`
- `../fixtures/executable_loop_run_002/run.json`
- `../fixtures/executable_loop_run_003/run.json`
- `../fixtures/executable_loop_accepted_run_001/run.json`
- `../fixtures/executable_loop_blocked_run_001/run.json`
- `../fixtures/executable_loop_reentry_run_001/run.json`
- `../fixtures/executable_loop_partial_reentry_run_001/run.json`
- `../fixtures/executable_loop_degraded_reentry_run_001/run.json`
- `../fixtures/executable_loop_compound_run_001/run.json`
- `../fixtures/executable_loop_hybrid_pressure_run_002/run.json`
- `../fixtures/mode_recommendation_strong_001.json`
- `../fixtures/mode_recommendation_weak_001.json`
- `../fixtures/mode_recommendation_hybrid_001.json`
- `../fixtures/mode_selection_run_001/receipt.json`
- `../fixtures/mode_selection_run_002/receipt.json`
- `../fixtures/mode_selection_run_003/receipt.json`
- `../fixtures/mode_selection_run_004/receipt.json`
- `../fixtures/governed_path_plan_run_001/preparation_receipt.json`
- `../fixtures/executable_loop_prepared_run_001/run.json`
- `../fixtures/executable_loop_selected_prepared_run_001/run.json`
- `../fixtures/executable_loop_selection_blocked_run_001/run.json`
- `../fixtures/executable_loop_runtime_resume_run_001/run.json`
- `../fixtures/executable_loop_runtime_resume_run_002/run.json`
- `../fixtures/executable_loop_runtime_resume_run_003/run.json`
- `../fixtures/executable_loop_runtime_non_resumable_run_001/run.json`
- `../fixtures/repair_packet_run_001/run.json`
- `../fixtures/repair_handoff_run_001/run.json`
- `../fixtures/executable_loop_compound_continuation_run_001/run.json`
- `../fixtures/executable_loop_compound_continuation_run_002/run.json`
- `../fixtures/executable_loop_compound_continuation_run_003/run.json`
- `../fixtures/executable_loop_compound_continuation_run_004/run.json`
- `../fixtures/executable_loop_compound_continuation_run_005/run.json`
- `../fixtures/governed_path_cost_delta_001.json`
- `../fixtures/executable_loop_hybrid_pressure_run_003/run.json`

That same `run.json` shape is now the canonical starting point for:

- accepted contours
- partial or mixed contours
- blocked contours
- repaired re-entry contours

## 3. Boundary

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

## 4. Extraction

Read these when you want to understand how the separate repo move is staged:

- `boundary/MINIMAL_KERNEL_EXTRACTION_CUT.md`
- `boundary/EXTRACTION_MIGRATION_MAP.md`
- `boundary/REPO_SKELETON_PLAN.md`
- `boundary/EXTRACTION_EXECUTION_PLAN.md`
- `boundary/FIRST_EXTRACTION_COMMIT_PLAN.md`

## 5. Reference Behaviors

Read these when you want the small operational slices that shaped the proving-ground discipline:

- `reference/TARGET_SURFACE_ATTESTATION.md`
- `reference/INCIDENT_AND_PRODUCTION_CONFIRMATION_HELPERS.md`
- `reference/DIRECT_LOOP_SPEC.md`
- `reference/INCIDENT_FLOW_EVALUATION_TEMPLATE.md`

## 6. Reference Helpers

The scripts under `../tools/reference/` are small reference helpers, not a full orchestration product:

- `attest_target_surface.sh`
- `require_attested_target_surface.sh`
- `intake_incident_hypothesis.sh`
- `confirm_live_production_fix.sh`
- `incident_operator_flow.sh`

## Reading Rule

If you only read four things first, use:

1. `boundary/KILLER_PATH_001.md`
2. `boundary/EXECUTABLE_STACK_READING_001.md`
3. `boundary/TRIO_READING_001.md`
4. `boundary/HYBRID_STATUS_001.md`
