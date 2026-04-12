# Examples

These examples are intentionally small and sanitized.

They are here to show how `Synrail` artifacts fit together without importing raw runtime history or one full battlefield.

## Included examples

- `sanitized_narrow_incident_flow.md`
  - a compact example of a narrow production incident moving through:
    - bounded hypothesis intake
    - target-surface attestation
    - production confirmation
    - post-incident evaluation
- `sanitized_application_policy_examples.md`
  - three compact examples showing when to choose:
    - full governed path
    - lightweight baseline
    - hybrid subset
- `sanitized_end_to_end_kernel_loop.md`
  - one compact worked example showing:
    - machine-readable state
    - proof bundle assembly
    - closure decision
    - refresh after degradation
    - baseline comparison

## Related fixtures

- `../fixtures/executable_loop_run_001/`
  - first internal end-to-end artifact set for the current executable stack
  - includes `run.json` as the first canonical run artifact
  - includes `orchestration.json` as the worked-envelope layer inside that run
- `../fixtures/executable_loop_run_002/`
  - second internal end-to-end artifact set on a weaker scenario
  - includes `run.json` as the weak-path canonical run artifact
- `../fixtures/executable_loop_run_003/`
  - third internal end-to-end artifact set on a hybrid middle-mode scenario
  - includes `run.json` as the hybrid-path canonical run artifact
- `../fixtures/executable_loop_accepted_run_001/`
  - first canonical accepted contour for the executable stack
  - includes `run.json` as the accepted-path primary run artifact
  - includes `report.json` as the clean accepted orchestration reading
- `../fixtures/executable_loop_blocked_run_001/`
  - first canonical blocked contour for the executable stack
  - includes `run.json` as the blocked-path primary run artifact
  - includes `report.json` as the direct blocked orchestration reading
- `../fixtures/executable_loop_reentry_run_001/`
  - first canonical re-entry contour for the executable stack
  - starts from a blocked readiness surface and returns to accepted closure
  - includes `run.json` as the repaired reverse-edge primary run artifact
- `../fixtures/executable_loop_partial_reentry_run_001/`
  - first canonical partial-proof re-entry contour for the executable stack
  - starts from a partial proof surface and returns to accepted closure
  - includes `run.json` as the repaired proof-completion primary run artifact
- `../fixtures/executable_loop_degraded_reentry_run_001/`
  - first canonical degraded re-entry contour for the executable stack
  - starts from a degraded recovery surface and returns to accepted closure
  - includes `run.json` as the repaired recovery primary run artifact
- `../fixtures/executable_loop_selected_prepared_run_001/`
  - first canonical contour where a preparation-aware strong selection receipt hands off directly into prepared governed execution
  - includes `run.json` as the selection-to-runtime primary run artifact
- `../fixtures/executable_loop_selection_blocked_run_001/`
  - first canonical contour where a lighter selection receipt blocks governed orchestration at `selection`
  - includes `run.json` as the selection-guard primary run artifact
- `../fixtures/executable_loop_runtime_resume_run_001/`
  - first canonical contour where a partial-proof state continues through the named `resume` runtime path
  - includes `run.json` as the runtime-continuation primary run artifact

## Rule

Examples in this directory should stay:

- small
- generic
- sanitized
- useful without outside conversation context
