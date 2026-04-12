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
  - includes `orchestration.json` as the first canonical worked run envelope
  - that envelope now matches a direct `orchestrate` output shape
- `../fixtures/executable_loop_run_002/`
  - second internal end-to-end artifact set on a weaker scenario
  - includes `orchestration.json` as the weak-path worked envelope
- `../fixtures/executable_loop_run_003/`
  - third internal end-to-end artifact set on a hybrid middle-mode scenario
  - includes `orchestration.json` as the hybrid-path worked envelope

## Rule

Examples in this directory should stay:

- small
- generic
- sanitized
- useful without outside conversation context
