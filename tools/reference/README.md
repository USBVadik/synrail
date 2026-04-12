# Reference Helpers

These scripts are intentionally small.

They are included to show narrow `Synrail` control behaviors clearly.

They are **not** a full orchestration platform.

For the quickest helper-selection view, start with:

- `USAGE_MATRIX.md`

## What these helpers are for

Use them as:

- reference implementations
- operator-facing examples
- small boundary-preserving utilities

Do not treat them as:

- the full product
- a complete deployment system
- a generic automation framework

## Included helpers

### `attest_target_surface.sh`

Purpose:

- collect enough evidence to say whether the intended target surface is actually the one being inspected

Useful when:

- a fix, test, or deploy claim depends on the truth of the target environment

Guarantees:

- emits an explicit pass/fail attestation result
- records concrete surface facts

Does not guarantee:

- that the target is healthy
- that a fix is correct
- that production behavior is repaired

### `require_attested_target_surface.sh`

Purpose:

- enforce attestation as a gate before a target-surface claim is treated as reviewable

Guarantees:

- blocks the next step if attestation did not pass

Does not guarantee:

- quality of the patch or test
- correctness of the target repo contents

### `intake_incident_hypothesis.sh`

Purpose:

- capture one narrow runtime clue as a bounded hypothesis

Guarantees:

- records a search-space reducer explicitly

Does not guarantee:

- diagnosis truth
- fix proof
- runtime confirmation

### `confirm_live_production_fix.sh`

Purpose:

- record one post-deploy runtime check against an expected outcome

Guarantees:

- compares observed external behavior to an expected result
- emits an explicit confirmation result

Does not guarantee:

- full feature completeness
- broad system health

### `incident_operator_flow.sh`

Purpose:

- preserve the intended incident order:
  - intake
  - attestation
  - confirmation

Guarantees:

- makes the basic flow harder to skip accidentally

Does not guarantee:

- good diagnosis
- good patches
- closure on its own

### `synrail_spine_v0.py`

Purpose:

- provide a minimal executable spine prototype with machine-readable state and hard transition gates
- hold the current bounded orchestration contour directly

Guarantees:

- can initialize a run state
- can deny disallowed transitions
- can emit one structured blocked-transition report with explicit blocker precedence
- can apply doctor records back into the state machine
- can apply bundle and closure artifacts back into the state machine
- can run one bounded `doctor -> bundle -> closure` contour with optional `refresh`, `compare`, and worked-envelope emission
- can carry one blocked-readiness contour back into accepted closure when the missing identity and proof inputs are repaired
- can carry one partial-proof contour back into accepted closure when the missing proof sections are supplied
- can carry one degraded recovery contour back into accepted closure through refresh reconciliation
- can emit one primary canonical run artifact from the spine-owned contour
- can emit machine-readable state

Does not guarantee:

- full product orchestration
- complete schema validation
- final operator UX

### `synrail_bundle_v0.py`

Purpose:

- assemble a minimal machine-readable proof bundle from a final result artifact plus bundle inputs

Guarantees:

- emits one normalized bundle artifact
- classifies it as `COMPLETE`, `PARTIAL`, or `INVALID`

Does not guarantee:

- semantic closure acceptance
- deep scenario validation
- full closure-engine behavior

### `synrail_proof_plan_v0.py`

Purpose:

- name the governed-path proof surface before bundle assembly starts

Guarantees:

- emits the seven required proof sections
- emits one named artifact path set for bundle-related outputs

Does not guarantee:

- that the planned artifacts are semantically correct
- closure acceptance on its own

### `synrail_preparation_receipt_v0.py`

Purpose:

- record whether the planned governed-path proof surface reached a complete first bundle pass

Guarantees:

- compares one proof plan to one assembled bundle
- records whether the bundle is closure-ready on the first pass

Does not guarantee:

- closure acceptance on its own
- deep semantic proof validation

### `synrail_closure_v0.py`

Purpose:

- emit a machine-readable closure verdict from run state plus proof bundle

Guarantees:

- identifies accepted vs claimed-not-accepted state
- emits a blocking reason when closure is not accepted
- emits one narrow next safe step

Does not guarantee:

- deep semantic scenario validation
- full refresh-chain automation
- full orchestration behavior

### `synrail_refresh_v0.py`

Purpose:

- refresh state after doctor, proof, closure, or recovery changes in deterministic order

Guarantees:

- updates machine-readable state
- emits a machine-readable refresh report
- invalidates over-green closure state when lower-level evidence worsens
- can reconcile one repaired recovery contour back into accepted closure after completed reverification

Does not guarantee:

- full dependency discovery
- broad orchestration behavior
- rich multi-run coordination

### `synrail_cli_v0.py`

Purpose:

- provide one small terminal-first operator entrypoint for the executable slices

Guarantees:

- exposes compact state reading
- exposes bundle, closure, and refresh commands through one CLI
- exposes one bounded orchestration path for `doctor -> bundle -> closure`
- exposes baseline comparison through the same CLI layer

Does not guarantee:

- full orchestration coverage
- interactive UX
- broad product shell behavior

### `synrail_mode_selector_v0.py`

Purpose:

- emit one cost-aware mode recommendation before the operator enters a heavier contour

Guarantees:

- can recommend `FULL_GOVERNED_PATH`, `LIGHTWEIGHT_BASELINE`, or `HYBRID_EXCEPTION`
- can expose one short measured reason and one narrow next safe step

Does not guarantee:

- full policy automation
- deep runtime execution
- automatic mode enforcement

### `synrail_mode_receipt_v0.py`

Purpose:

- emit one machine-readable receipt recording whether the operator followed the mode recommendation

Guarantees:

- records the recommended mode
- records the selected mode
- records whether the heavier contour was entered or skipped

Does not guarantee:

- runtime correctness on its own
- economic correctness beyond the supplied recommendation artifact

### `synrail_runtime_v0.py`

Purpose:

- preserve compatibility for the bounded runtime contour while the contour itself moves closer to the spine

Guarantees:

- forwards to the spine-owned orchestration contour
- keeps older runtime-shaped entry usage compatible

Does not guarantee:

- ownership of the orchestration loop itself
- broad orchestration coverage
- multi-run scheduling

### `synrail_baseline_harness_v0.py` and `synrail_baseline_harness_v1.py`

Purpose:

- compare one baseline artifact against one Synrail artifact and emit a machine-readable verdict
- add a second comparison path that includes simple economics rather than only qualitative comparison

Guarantees:

- produces one repeatable comparison record
- avoids purely prose-based comparison outcomes
- `v1` also emits operator-cost and false-green-exposure deltas in machine-readable form

Does not guarantee:

- statistical proof
- deep scenario normalization
- broad benchmarking behavior

### `synrail_hybrid_status_v0.py`

Purpose:

- read the current economics aggregate plus hybrid comparison records and emit one explicit hybrid-mode status

Guarantees:

- emits one machine-readable `JUSTIFIED`, `PROVISIONAL`, or `DEMOTED` reading
- keeps hybrid policy tied to measured evidence rather than only to prose

Does not guarantee:

- final product economics
- broad policy discovery
- more hybrid evidence than the repo already has

### `synrail_cost_of_control_v0.py`

Purpose:

- aggregate multiple economics-aware comparison records into one cost-of-control reading

Guarantees:

- emits one machine-readable aggregate artifact
- names justified-cost, baseline-sufficient, and under-proven path buckets
- surfaces the current cost hotspots

Does not guarantee:

- live operator telemetry
- a complete economic model
- automatic CLI integration

### `synrail_validate_v0.py`

Purpose:

- validate one Synrail JSON artifact against one local schema

Guarantees:

- catches basic structural mismatches
- emits an explicit valid or invalid result

Does not guarantee:

- full JSON Schema coverage
- semantic correctness
- broad enforcement by itself

### `synrail_doctor_v1.py`

Purpose:

- emit one machine-readable readiness verdict for the intended run class

Guarantees:

- evaluates a narrow gate set
- can probe git cleanliness on a target surface
- can probe artifact-path parent existence
- can probe helper entrypoint presence
- can probe credential env presence
- can probe whether a path-based credential env points at something real
- can probe exact prompt identity file presence
- can probe expected exact task identity mismatch
- can probe expected target-surface identity mismatch
- emits a doctor record with blocking failure classes
- can write doctor status back into the run state

Does not guarantee:

- deep environment probing
- provider reachability validation
- full diagnostics coverage

### `synrail_mode_selector_v0.py`

Purpose:

- recommend the cheapest honest mode before the operator enters a heavier contour

Guarantees:

- reads current cost-of-control evidence
- can incorporate current hybrid-status demotion
- emits one machine-readable mode recommendation
- can steer weak or demoted-hybrid paths back to baseline by default

Does not guarantee:

- perfect scenario classification
- replacement of human judgment on novel scenarios
- automatic enforcement by itself

### `synrail_mode_receipt_v0.py`

Purpose:

- record one machine-readable receipt showing whether the operator followed a mode recommendation

Guarantees:

- records selected mode
- records whether a heavier contour was entered
- records estimated avoided operator cost when baseline is selected

Does not guarantee:

- that the recommendation itself was correct
- that the baseline path was executed well

## Operating rule

If a helper starts accumulating broad product logic, large orchestration behavior, or environment-specific sprawl, it should probably stop living under `tools/reference/` in this repo shape.
