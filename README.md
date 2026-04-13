# Synrail

Guided control for reliable agent execution.

Proof-first control kernel for agentic work.

## Wedge

Claims are not accepted reality without proof.

`Synrail` exists to turn noisy execution into reviewable truth:

- attested execution surfaces
- bounded recovery and transition rules
- explicit doctor and evaluation layers
- proof-bundle review instead of narrative trust
- closure decisions that can be accepted or rejected honestly

## Scope

This repository shell contains only the first extraction cut of the kernel:

- core contracts
- truth surfaces
- recovery and transition standards
- boundary definitions
- narrow reference helpers for attestation, bounded intake, production confirmation, and incident flow

## Not Included

This first cut intentionally does not include:

- downstream bot implementation logic
- downstream capability layers
- live runtime artifacts
- one-off incident archaeology
- image-enhancer or backend-routing policy work
- environment-specific battlefield residue

## Layout

- `docs/core/`: kernel contracts and truth surfaces
- `docs/boundary/`: product boundary and extraction-definition docs
- `docs/reference/`: narrow operational reference behavior
- `tools/reference/`: small helper scripts that express kernel behavior clearly
- `examples/`: small curated and sanitized examples
- `fixtures/`: sanitized machine-readable fixtures, run artifacts, and economics records

For a quick document map, start with:

- `docs/README.md`
- `tools/reference/README.md`
- `tools/reference/USAGE_MATRIX.md`

## First Reference Helpers

- `attest_target_surface.sh`
- `require_attested_target_surface.sh`
- `intake_incident_hypothesis.sh`
- `confirm_live_production_fix.sh`
- `incident_operator_flow.sh`
- `synrail_cli_v0.py`

## Reading Order

Read these first:

1. `docs/boundary/EXECUTABLE_STACK_READING_001.md`
2. `docs/boundary/CORE_SCOPE_001.md`
3. `docs/boundary/OUTCOME_LATTICE_001.md`
4. `docs/boundary/TRANSITION_LATTICE_001.md`
5. `docs/boundary/REENTRY_LATTICE_001.md`
6. `docs/boundary/TRIO_READING_001.md`
7. `docs/boundary/COST_OF_CONTROL_001.md`
8. `docs/boundary/HYBRID_STATUS_001.md`
9. `docs/boundary/KILLER_PATH_001.md`
10. `docs/boundary/BASELINE_COMPARISON_RECORD_001.md`
11. `docs/boundary/MINIMUM_UNDENIABLE_CORE_001.md`
12. `docs/core/SYNRAIL_RUNTIME_TRUTH_SURFACE.md`
13. `docs/core/SYNRAIL_EXACT_TASK_CLOSURE_SPEC.md`

Read these next only if you need them:

- `docs/boundary/BASELINE_RUNBOOK_001.md`
- `docs/boundary/APPLICATION_POLICY_001.md`
- `docs/boundary/HYBRID_SUBSET_001.md`
- `docs/boundary/OVERHEAD_VS_VALUE_MAP_001.md`
- `docs/boundary/CORE_COMPRESSION_PASS_001.md`
- `docs/core/CHECKPOINT_001.md`
- `docs/core/CHECKPOINT_RUN_001.md`
- `docs/core/CHECKPOINT_RUN_002.md`
- `docs/core/REPAIR_TERMINATION_001.md`
- `docs/core/REPAIR_CONVERGENCE_RUN_001.md`
- `docs/core/ARTIFACT_CONSISTENCY_001.md`
- `docs/core/DOCTOR_COVERAGE_MAP_001.md`
- `docs/core/OBSERVABILITY_001.md`
- `docs/core/REPRODUCIBILITY_TEST_001.md`
- `docs/core/SECOND_OPERATOR_TEST_001.md`
- `docs/core/REPRODUCIBILITY_TEST_002.md`
- `docs/core/SECOND_OPERATOR_TEST_002.md`
- `docs/core/OPERATOR_BRIEF_001.md`
- `docs/core/OPERATOR_BRIEF_RUN_002.md`
- `docs/core/OPERATOR_BRIEF_CHAIN_001.md`
- `docs/core/OPERATOR_BRIEF_CHAIN_RUN_002.md`
- `docs/core/OPERATOR_RENDER_001.md`
- `docs/boundary/SUBSTITUTE_KILL_TEST_002.md`
- `docs/boundary/SUBSTITUTE_KILL_TEST_003.md`

## Current State

This is the first bounded extraction move, now hardened into a private-stable review surface.

It is meant to establish identity and boundary clearly before any broader packaging, repo publishing, or integration work.

The current working mode is:

- private executable pressure-testing before any public release pressure
- kernel hardening first, with secondary layers frozen unless they directly support the core

The current proof reading is:

- one economics-aware strong-path comparison now says `SYNRAIL_BETTER`
- one economics-aware weak-path comparison now says `BASELINE_GOOD_ENOUGH`
- one economics-aware hybrid comparison still says `UNCLEAR`
- one uglier hybrid pressure-test now also says `SYNRAIL_BETTER`
- one further hybrid pressure-test now says `BASELINE_GOOD_ENOUGH`
- one ugly compound run now also says `SYNRAIL_BETTER`
- the current pressure-testing tranche now has one aggregate cost-of-control surface and one explicit hybrid-secondary status
- doctor now also has one targeted false-readiness pressure-test slice for broken credential paths and exact task identity mismatch
- doctor now also has one targeted wrong-target-surface pressure-test slice
- the repo now also has one cost-aware mode selector that can steer weak and demoted-hybrid paths back to baseline before entering a heavier contour
- the repo now also has one operator-facing selection receipt showing that a demoted-hybrid path stayed on baseline and skipped the heavier contour
- the repo now also has a second operator-facing selection receipt showing that a weak low-risk path stayed on baseline and skipped the heavier contour
- the repo now also has a third operator-facing selection receipt showing that the strong expensive-wrong-closure path explicitly entered the governed contour
- the repo now also has a fourth operator-facing selection receipt showing that the strong path now explicitly enters the prepared governed contour when bounded cost evidence supports it
- the repo now also has one governed-path preparation plan and receipt showing that the planned proof surface can reach a complete first bundle pass before closure starts
- the repo now also has one canonical prepared governed-path run showing that preparation now lives inside the runtime contour, not only beside it
- the repo now also has one canonical selected-prepared governed-path run showing that a strong selection receipt can now hand off directly into that prepared runtime contour
- the repo now also has one canonical selection-blocked run showing that a lighter receipt now stops governed orchestration at `selection`
- the repo now also has one canonical runtime-resume run showing that a partial-proof state can now continue through a named `resume` path instead of only through a generic re-entry fixture
- the repo now also has one second canonical runtime-resume run showing that a degraded recovery state can now continue through that same named `resume` path
- the repo now also has one third canonical runtime-resume run showing that a true `DOCTOR_BLOCKED` readiness contour can now continue through that same named `resume` path
- the repo now also has one first-class repair-handoff slice that tells the operator and the runtime which continuation inputs are still missing before resume can proceed honestly
- the repo now also has one richer repair-packet slice that carries continuation context, continuation plan, repair inputs, and runtime output defaults in one machine-readable bundle
- the repo now also auto-synthesizes that richer repair packet from current runtime truth, so the operator no longer has to assemble most continuation context by hand
- the repo now also lets that richer repair packet carry explicit resumability family, active repair pressures, and repair order so runtime continuation can distinguish repairable contours from terminal ones more honestly
- the repo now also lets that richer repair packet point to which existing artifact surface is still stale, not only which next input is missing
- the repo now also lets that richer repair packet point to narrower stale sub-surfaces inside those artifacts, so continuation can name exactly what is stale instead of only naming a broader artifact shell
- the repo now also has one canonical blocked repair-handoff run showing that `resume` now stops explicitly at `repair_handoff` when the continuation contract is still incomplete
- the repo now also has one canonical runtime non-resumable run showing that a lighter-mode selection block now stops governed continuation at `resume` with `STATE_NOT_RESUMABLE`
- the repo now also has one second canonical runtime non-resumable run showing that accepted terminal closure is now its own explicit non-resumable continuation family
- the repo now also has one third canonical runtime non-resumable run showing that rejected terminal closure is now its own explicit non-resumable continuation family
- the repo now also has one fourth canonical runtime non-resumable run showing that a fresh governed `READY` state now stops `resume` with one explicit forward-orchestration non-resumable family
- the repo now also has one fourth canonical runtime-resume run showing that sibling artifact auto-discovery now lets packet-first `resume` reach accepted closure with much less manual replay
- the repo now also has one bounded governed-path cost delta showing that preparation can reduce operator tax inside the winning contour without weakening closure safety
- the repo now also has one canonical ugly compound continuation run showing that two staged repair handoffs plus named `resume` can cross doctor-blocked, partial-proof, and degraded-recovery pressure on the same runtime surface
- the repo now also has one second uglier compound continuation run showing that richer repair packets plus named `resume` can cross blocked readiness, invalid proof, degraded recovery, and accepted closure on the same runtime surface
- the repo now also has one third uglier packet-first compound continuation run showing that selection/preparation handoff, auto-synthesized repair packets, and named `resume` can now cross invalid proof and degraded recovery on the same runtime surface
- the repo now also has one fourth uglier packet-first compound continuation run showing that selection/preparation handoff, packet-first `resume`, repair-handoff blocking, degraded recovery, and a final explicit terminal not-resumable reading can now live on the same runtime surface
- the repo now also has one fifth uglier packet-first compound continuation run showing that selection/preparation handoff, stale-artifact hints, explicit repair order, one mid-continuation readiness failure, and accepted closure can now live on the same runtime surface
- the repo now also has one first-class artifact repair receipt layer showing which repair step actually completed and which narrower artifact sub-surfaces are still stale afterward
- the repo now also has one sixth uglier packet-first compound continuation run showing that repair receipts, packet carry-over, explicit step order, and final truthful terminal packet emission can all now live on the same runtime surface
- the repo now also has one seventh uglier packet-first compound continuation run showing that invalid proof, recovery repair, doctor target-identity pressure, and accepted closure can now all live on the same runtime surface
- the repo now also has one eighth uglier packet-first compound continuation run showing that doctor target-identity pressure, partial proof pressure, recovery pressure, and accepted closure can now all live on the same runtime surface with one packet-native repair-history chain

The current wedge reading is:

- `Synrail` is strongest on proof-sensitive closure paths where false completion is expensive
- it is not yet justified as a full governed path for every small incident
- the hybrid subset now has both a stronger win and a baseline-sufficient medium-risk case, so it is demoted from default policy status

The current executable output reading is:

- the spine can now emit one primary canonical run artifact
- the repo now carries canonical accepted, blocked, blocked-reentry, partial-reentry, and degraded-reentry fixtures on that same artifact surface
- the repo now also carries one canonical prepared governed-path fixture on that same artifact surface
- the repo now also carries one canonical selected-prepared governed-path fixture on that same artifact surface
- the repo now also carries one canonical selection-blocked fixture on that same artifact surface
- the repo now also carries one canonical runtime-resume fixture on that same artifact surface
- the repo now also carries one second canonical runtime-resume fixture on that same artifact surface
- the repo now also carries one third canonical runtime-resume fixture on that same artifact surface
- the repo now also carries one fourth canonical runtime-resume fixture on that same artifact surface
- the repo now also carries one canonical repair-packet blocked fixture on that same artifact surface
- the repo now also carries one canonical repair-handoff blocked fixture on that same artifact surface
- the repo now also carries one canonical runtime non-resumable fixture on that same artifact surface
- the repo now also carries one second canonical runtime non-resumable fixture on that same artifact surface
- the repo now also carries one third canonical runtime non-resumable fixture on that same artifact surface
- the repo now also carries one fourth canonical runtime non-resumable fixture on that same artifact surface
- the repo now also carries one canonical ugly compound repair fixture on that same artifact surface
- the repo now also carries one canonical ugly compound continuation fixture on that same artifact surface
- the repo now also carries one second canonical ugly compound continuation fixture on that same artifact surface
- the repo now also carries one third canonical ugly compound continuation fixture on that same artifact surface
- the repo now also carries one fourth canonical ugly compound continuation fixture on that same artifact surface
- the repo now also carries one fifth canonical ugly compound continuation fixture on that same artifact surface
- the repo now also carries one sixth canonical ugly compound continuation fixture on that same artifact surface
- the repo now also carries one seventh canonical ugly compound continuation fixture on that same artifact surface
- the repo now also carries one eighth canonical ugly compound continuation fixture on that same artifact surface
- the repo now also carries one canonical hybrid pressure fixture on that same artifact surface
- the repo now also has one explicit outcome lattice across accepted, partial, degraded, and blocked contours
- the repo now also has one explicit re-entry reading for blocked-to-accepted, partial-to-accepted, and degraded-to-accepted repair
- the repo now also has one first compound economics comparison record on a proof-sensitive ugly path
- the repo now also has one second hybrid pressure-test with a `SYNRAIL_BETTER` economics verdict
- the repo now also has one third hybrid pressure-test with a `BASELINE_GOOD_ENOUGH` economics verdict
- the repo now also has one aggregate machine-readable cost-of-control record across strong, weak, hybrid, compound, and two hybrid-pressure paths
- that artifact is now the best single machine-readable entrypoint into a bounded internal run
- the trio now also has first `comparison_economics` records with simple operator-cost and false-green metrics

## Contributing

For active contribution shape, start here:

- `CONTRIBUTING.md`
- `ROADMAP.md`
- `docs/boundary/KILLER_PATH_001.md`
- `docs/boundary/WEDGE_STATEMENT_001.md`
- `docs/boundary/APPLICATION_POLICY_001.md`
- `docs/boundary/HYBRID_SUBSET_001.md`
- `docs/boundary/HYBRID_STATUS_001.md`
- `docs/boundary/BASELINE_COMPARISON_RECORD_001.md`
- `docs/boundary/BASELINE_COMPARISON_RECORD_002.md`
- `docs/boundary/MINIMUM_UNDENIABLE_CORE_001.md`
- `docs/boundary/SYNRAIL_NOT_FOR_001.md`

Secondary repo-history and hardening context remains available in `docs/boundary/`, but it is not the first route through the project anymore.

- the repo now also carries one ninth canonical ugly compound continuation fixture on that same artifact surface
- primary run artifacts now also carry one first-class repair-history summary instead of burying that truth only inside repair packets
- packet-first continuation now defaults to fewer root-level side artifacts when packet truth is already sufficient
- the repo now also carries one first low-friction minimal-continuation run proving that one repaired `DOCTOR_BLOCKED` contour can now continue from just `state + repair_packet`
- the repo now also carries one tenth ugly compound continuation run proving that repeated doctor pressure can now survive packet-chained minimal-core continuation with lower visible side-file tax
- the repo now also has one continuation-adoption pressure slice showing that this compressed continuation model reduced root side-file tax without losing repeated doctor pressure or accepted closure
- the repo now also has one first reproducibility pressure slice showing that a stalled repair-loop contour now preserves the same key blocking and termination truth across repeated runs
- the repo now also has one first second-operator pressure slice showing that the compressed `state + repair_packet` continuation entry is now followable without hidden author memory on one repaired `DOCTOR_BLOCKED` path
- the repo now also has one second substitute-kill pressure slice showing that the tightened kernel now wins more clearly on stalled repair-loop convergence control and packet-first second-operator continuation, while the weak path still remains non-decisive against a lighter substitute stack
- the repo now also has one second less-curated reproducibility pressure slice showing that an uglier repeated-doctor continuation step now preserves the same bounded block and termination truth across repeated replays
- the repo now also has one second less-curated second-operator pressure slice showing that packet-first continuation is still followable on a repeated-doctor contour that returns to bounded doctor pressure instead of clean acceptance
- the repo now also has one third harsher substitute-kill pressure slice showing that the tightened kernel now also wins on one repeated doctor-return continuation stack and one less-curated stage-level continuation stack, while the weak path still remains non-decisive
- the repo now also has one first broader operator-layer slice that compresses runtime truth into one operator brief and, on one ugly repeated-doctor contour, correctly tells the operator to stop replaying the same contour and start a new run instead
- the repo now also has one second canonical operator-brief slice showing that the same operator layer can preserve honest repairability on a `RECOVERY_PENDING` contour and point directly at the current repair step, required inputs, and next bounded `resume`
- the repo now also has one first multi-stage operator-brief chain showing the whole repair sequence across an ugly continuation contour, from partial proof to doctor block to recovery repair to terminal accepted boundary
- the repo now also has one second canonical operator-brief chain showing the complementary ugly ending: repair proof, repair doctor pressure, then stop replaying the contour and start a new run when bounded repair termination is reached
- the repo now also has one first strictly derived human-readable operator render for both single briefs and chain summaries, so the operator layer is easier to scan without adding a new control surface

- the repo now also carries one first substitute-kill pressure slice against concrete substitute stacks instead of only one abstract baseline
- that pressure slice currently shows two substitute-stack wins for Synrail and one still-unclear weak-path comparison
- the repo now also has one first-class checkpoint contract plus one canonical happy-path checkpoint run proving create, verify, and restore on an accepted contour
- the repo now also has one failed-restore checkpoint run proving restore verification can fail honestly and roll back checkpoint-owned artifacts
- repair termination is now explicit kernel truth instead of one future continuation concern
- the repo now also has one canonical repair-convergence run proving that repeated no-progress now terminates packet-first `resume` before the next blind retry
- the repo now also has one first explicit artifact-consistency model treating `state_file` as source of truth and one paired proof slice for consistent vs stale derived artifacts
- doctor now also has one tighter helper-integrity pressure-test proving that a parse-broken helper entrypoint no longer counts as green readiness
- the runtime now also emits one bounded observability artifact with state-transition, repair-attempt, rejection, and sanitized session-export truth
