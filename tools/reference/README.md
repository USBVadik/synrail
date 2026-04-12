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

Guarantees:

- can initialize a run state
- can deny disallowed transitions
- can apply doctor records back into the state machine
- can apply bundle and closure artifacts back into the state machine
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

### `synrail_baseline_harness_v0.py`

Purpose:

- compare one baseline artifact against one Synrail artifact and emit a machine-readable verdict

Guarantees:

- produces one repeatable comparison record
- avoids purely prose-based comparison outcomes

Does not guarantee:

- statistical proof
- deep scenario normalization
- broad benchmarking behavior

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

### `synrail_doctor_v0.py`

Purpose:

- emit one machine-readable readiness verdict for the intended run class

Guarantees:

- evaluates a narrow gate set
- emits a doctor record with blocking failure classes
- can write doctor status back into the run state

Does not guarantee:

- deep environment probing
- provider reachability validation
- full diagnostics coverage

## Operating rule

If a helper starts accumulating broad product logic, large orchestration behavior, or environment-specific sprawl, it should probably stop living under `tools/reference/` in this repo shape.
