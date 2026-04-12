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
2. `docs/boundary/OUTCOME_LATTICE_001.md`
3. `docs/boundary/TRANSITION_LATTICE_001.md`
4. `docs/boundary/REENTRY_LATTICE_001.md`
5. `docs/boundary/TRIO_READING_001.md`
6. `docs/boundary/COST_OF_CONTROL_001.md`
7. `docs/boundary/HYBRID_STATUS_001.md`
8. `docs/boundary/KILLER_PATH_001.md`
9. `docs/boundary/BASELINE_COMPARISON_RECORD_001.md`
10. `docs/boundary/MINIMUM_UNDENIABLE_CORE_001.md`
11. `docs/core/SYNRAIL_RUNTIME_TRUTH_SURFACE.md`
12. `docs/core/SYNRAIL_EXACT_TASK_CLOSURE_SPEC.md`

Read these next only if you need them:

- `docs/boundary/BASELINE_RUNBOOK_001.md`
- `docs/boundary/APPLICATION_POLICY_001.md`
- `docs/boundary/HYBRID_SUBSET_001.md`
- `docs/boundary/OVERHEAD_VS_VALUE_MAP_001.md`
- `docs/boundary/CORE_COMPRESSION_PASS_001.md`

## Current State

This is the first bounded extraction move, now hardened into a private-stable review surface.

It is meant to establish identity and boundary clearly before any broader packaging, repo publishing, or integration work.

The current working mode is:

- private executable pressure-testing before any public release pressure

The current proof reading is:

- one economics-aware strong-path comparison now says `SYNRAIL_BETTER`
- one economics-aware weak-path comparison now says `BASELINE_GOOD_ENOUGH`
- one economics-aware hybrid comparison still says `UNCLEAR`
- one ugly compound run now also says `SYNRAIL_BETTER`
- the current pressure-testing tranche now has one aggregate cost-of-control surface and one explicit hybrid-secondary status

The current wedge reading is:

- `Synrail` is strongest on proof-sensitive closure paths where false completion is expensive
- it is not yet justified as a full governed path for every small incident
- the hybrid subset remains promising, but it is now explicitly kept provisional and secondary until more measured wins exist

The current executable output reading is:

- the spine can now emit one primary canonical run artifact
- the repo now carries canonical accepted, blocked, blocked-reentry, partial-reentry, and degraded-reentry fixtures on that same artifact surface
- the repo now also carries one canonical ugly compound repair fixture on that same artifact surface
- the repo now also has one explicit outcome lattice across accepted, partial, degraded, and blocked contours
- the repo now also has one explicit re-entry reading for blocked-to-accepted, partial-to-accepted, and degraded-to-accepted repair
- the repo now also has one first compound economics comparison record on a proof-sensitive ugly path
- the repo now also has one aggregate machine-readable cost-of-control record across strong, weak, hybrid, and compound paths
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
