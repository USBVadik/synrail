# Examples

These examples are intentionally small and sanitized.

They are here to show how `Synrail` artifacts fit together without importing raw runtime history or one full battlefield.

## Included examples

- `deploy_guard/`
  - copyable guard-first deploy and restart patterns
  - shows how to stop `rsync` / `ssh ... pm2 restart` on stale Synrail authorization
  - includes `pm2` and `systemd`-shaped examples
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
- `false-green-demo/`
  - runnable public demo pack with a README, script, and transcript
  - shows the shortest path from false-green claim to bounded repair to accepted closure
- `false-green-benchmark/`
  - denser starter public benchmark pack with curated local cases and case families
  - makes the false-green problem concrete without claiming external empirical proof
- `cross-repo-pilot/`
  - privacy-bounded maintainer dogfood capture for runs in other repositories
  - fixes the evidence class to internal and keeps external alpha claims separate
- `false_green_demo.md`
  - one short public-facing summary of the same false-green wedge

For the bounded tester handoff after these examples, use `../docs/review/FIRST_TESTER_PROTOCOL_001.md` and route feedback through the GitHub issue templates.

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
- `../fixtures/executable_loop_runtime_resume_run_002/`
  - second canonical contour where a degraded recovery state continues through the named `resume` runtime path
  - includes `run.json` as the degraded runtime-continuation primary run artifact
- `../fixtures/executable_loop_runtime_resume_run_003/`
  - third canonical contour where a true `DOCTOR_BLOCKED` state continues through the named `resume` runtime path
  - includes `run.json` as the doctor-blocked runtime-continuation primary run artifact
- `../fixtures/executable_loop_runtime_non_resumable_run_001/`
  - first canonical contour where a governed continuation attempt is honestly rejected because the current selected mode is not resumable into governed execution
  - includes `run.json` as the non-resumable runtime-continuation primary run artifact
- `../fixtures/repair_handoff_run_001/`
  - first canonical contour where `resume` is blocked explicitly at `repair_handoff` because the continuation contract is still incomplete
  - includes `repair_handoff.json` as the machine-readable continuation contract
  - includes `run.json` as the blocked continuation primary run artifact
- `../fixtures/repair_packet_run_001/`
  - first canonical contour where one richer repair packet still blocks honestly at `repair_handoff`
  - includes `packet.json` as the machine-readable continuation packet
  - includes `run.json` as the blocked packet-driven continuation primary run artifact
- `../fixtures/executable_loop_compound_continuation_run_001/`
  - first canonical ugly continuation contour using staged repair handoffs plus named `resume`
  - crosses doctor-blocked readiness, partial proof, and degraded recovery pressure on the same runtime surface
  - includes `run.json` as the compound runtime-continuation primary run artifact
- `../fixtures/executable_loop_compound_continuation_run_002/`
  - second uglier packet-driven continuation contour using staged repair packets plus named `resume`
  - crosses blocked readiness, invalid proof, degraded recovery, and accepted closure on the same runtime surface
  - includes `run.json` as the richer compound runtime-continuation primary run artifact
- `../fixtures/executable_loop_compound_continuation_run_003/`
  - third uglier packet-first continuation contour using selection/preparation handoff plus auto-synthesized repair packets
  - crosses invalid proof, degraded recovery, and accepted closure on the same runtime surface
  - includes `run.json` as the packet-first compound runtime-continuation primary run artifact
- `../fixtures/executable_loop_compound_continuation_run_004/`
  - fourth uglier packet-first continuation contour using selection/preparation handoff plus richer resumability-aware repair packets
  - crosses repair-handoff blocking, repairable recovery, and one explicit terminal not-resumable finish on the same runtime surface
  - includes `run.json` as the richer packet-first compound runtime-continuation primary run artifact
- `../fixtures/executable_loop_compound_continuation_run_005/`
  - fifth uglier packet-first continuation contour using selection/preparation handoff plus stale-artifact hints and explicit multi-step repair order
  - crosses out-of-order repair blocking, doctor-blocked readiness, degraded recovery, and accepted closure on the same runtime surface
  - includes `run.json` as the ordered packet-first compound runtime-continuation primary run artifact
- `../fixtures/executable_loop_runtime_non_resumable_run_002/`
  - explicit accepted-terminal non-resumable continuation contour
  - shows that `resume` stops honestly after accepted closure and points to `start_new_run`
  - includes `run.json` as the accepted-terminal non-resumable primary run artifact
- `../fixtures/executable_loop_runtime_non_resumable_run_003/`
  - explicit rejected-terminal non-resumable continuation contour
  - shows that `resume` also stops honestly after rejected terminal closure and points to `start_new_run`
  - includes `run.json` as the rejected-terminal non-resumable primary run artifact
- `../fixtures/executable_loop_runtime_resume_run_004/`
  - fourth runtime-resume contour using packet-first sibling auto-discovery
  - reaches accepted closure from `DOCTOR_BLOCKED` with much less raw flag replay
  - includes `run.json` as the low-replay runtime-resume primary run artifact

## Rule

Examples in this directory should stay:

- small
- generic
- sanitized
- useful without outside conversation context
- explicit about current support boundaries
