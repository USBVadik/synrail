# Technical Map 001

## System shape

At a high level, `Synrail` has six layers.

### 1. Thin alpha shell

Purpose:

- present one small human-usable CLI over the kernel

Main file:

- `alpha.py`
- `tools/reference/synrail_cli_v0.py`

Current primary user-facing commands include:

- `synrail`
- `start`
- `check`
- `status`
- `explain-proof`
- `save`
- `restore --preview`
- `restore`

Current helper, compatibility, or advanced surfaces still include:

- `repair-step`
- `retry`
- `confirm-restore`
- `telemetry export`
- `bug-packet`
- `session-export`

The default `synrail --help` keeps helper and dev surfaces out of the first operator view even though those compatibility paths still exist underneath.

Repo-native agent policy files also stay portable-first now: committed workflow examples use `synrail`, while any exact machine-local binary is surfaced only as a fallback note for that checkout.

### 2. Runtime spine

Purpose:

- own the run state machine and allowed transitions

Main file:

- `tools/reference/synrail_spine_v0.py`

This is the core execution contour.

It tracks:

- target surface state
- doctor state
- integrity state
- execution state
- proof bundle state
- closure state
- recovery state
- next safe step

### 3. Truth surfaces

These are the main kernel truth anchors.

Doctor:

- `tools/reference/synrail_doctor_v1.py`

Proof bundle:

- `tools/reference/synrail_bundle_v0.py`

Closure:

- `tools/reference/synrail_closure_v0.py`

Refresh/recovery:

- `tools/reference/synrail_refresh_v0.py`

### 4. Continuation / repair layer

Purpose:

- capture non-green continuation as explicit machine-readable contract

Main files:

- `tools/reference/synrail_repair_handoff_v0.py`
- `tools/reference/synrail_repair_packet_v0.py`
- `tools/reference/synrail_continuation_arbiter_v0.py`
- `tools/reference/synrail_second_operator_v0.py`

### 5. Hardening layers added after critique pressure

Acceptance independence:

- `tools/reference/synrail_acceptance_criteria_v0.py`

Doctor measured coverage:

- `tools/reference/synrail_doctor_coverage_v0.py`
- `tools/reference/doctor_coverage_profile_v0.json`
- `tools/reference/doctor_coverage_corpus_v0.json`

Continuation arbitration:

- `tools/reference/synrail_continuation_arbiter_v0.py`

### 6. Observability / export

Purpose:

- capture bounded replay/debug information for alpha failures

Main files:

- `tools/reference/synrail_observability_v0.py`
- `tools/reference/synrail_alpha_telemetry_v0.py`
- `tools/reference/synrail_bug_packet_v0.py`

## Main runtime flow

### Init

`init` creates:

- `state.json`
- `project_profile.json`
- `acceptance_criteria.json`
- optional telemetry config
- optional `task_identity.txt` and `prompt_identity.txt`

### Check

`check` is the main runtime contour.

It can perform:

1. project/profile default resolution
2. acceptance validation
3. doctor
4. spine orchestration
5. bundle evaluation
6. closure evaluation
7. refresh invalidation and recovery reconciliation when refresh input is present
8. thin output rendering, including stale-obligation guidance when refresh invalidation matches the active run
9. compact bounded repair summary when non-green

Main outputs under the artifact root typically include:

- `state.json`
- `report.json`
- `doctor.json`
- `bundle.json`
- `closure.json`
- `refresh.json`
- `thin_output.json`
- `prompt.json` when repair-step materializes a bounded instruction
- `repair_packet.json`
- `observability.json`

### Repair-step

`repair-step` reads the current repair packet and renders a bounded next-agent instruction.

This is not a general orchestration planner or the preferred first-run command.

It is a constrained bridge from current non-green truth to one next attempt.

### Retry

`retry` is a compatibility alias for continuation on a repairable contour.

It still goes through the same kernel continuation logic.

### Save / restore

`save` creates and confirms a restore point.

`restore --preview` shows whether the current restore contour is full, limited, or unsupported before mutating the workspace.

`restore` rehydrates it.

`confirm-restore` explicitly re-checks it.

The current local matrix is intentionally narrow but explicit:

- clean git workspace
- dirty tracked git workspace
- dirty untracked git workspace via file-copy fallback
- mixed tracked + untracked git workspace via file-copy fallback
- git workspace without a committed HEAD via file-copy fallback
- non-git file-copy restore
- unsupported contours that fail early and honestly

### Telemetry export / bug packet

These do not replace runtime truth.

They package it for outside review.

## Important runtime artifacts

### `state.json`

Canonical state-machine artifact.

Use it to answer:

- what state is the run in now?
- what is the next safe step?
- what is blocked?

### `report.json`

Compact orchestration result.

Use it to answer:

- where did the run stop?
- what is the dominant blocker?
- what resumability reading did the runtime compute?

### `doctor.json`

Readiness gate plus measured coverage truth.

Use it to answer:

- did doctor pass?
- if yes, under what coverage assumptions?
- if blocked, why exactly?

### `bundle.json`

Proof bundle verdict.

Use it to answer:

- is the bundle missing, invalid, structurally complete, or semantically sufficient?
- which sections are missing or too thin?

### `closure.json`

Acceptance verdict.

Use it to answer:

- accepted or not?
- if not, why not?
- which transition is allowed next?

### `repair_packet.json`

Machine-readable continuation contract.

Use it to answer:

- what is the current repair step?
- what is stale?
- what are the required inputs?
- what is the current repairability reading?

### `prompt.json`

Human/agent bridge built from the repair packet.

Use it to answer:

- what exactly should the next attempt do?
- what is forbidden?
- what must pass afterwards?

### `observability.json`

Small bounded runtime observability record.

### `telemetry/session_replay.json`

Compact export for external alpha analysis.

## Current hardening status by weak spot

Semantic proof:

- bundle now separates structural completeness from semantic sufficiency
- closure blocks on semantically thin proof

Acceptance truth:

- explicit criteria record
- explicit validation record
- explicit refresh path

Doctor truth:

- explicit measured coverage gate over declared profile

Continuation:

- explicit arbiter with resolution trace

Regression discipline:

- automated `unittest` suite on truth-critical cases

## Test and fixture strategy

Two main test layers now exist.

### Regression harness

File:

- `tests/test_truth_regressions.py`

Covers:

- false accept
- false reject
- degraded after accepted
- repair no-progress
- checkpoint restore integrity
- packet/state conflict
- doctor false-ready boundary
- semantically thin proof

### Current tester-pack smoke

File:

- `tests/test_alpha_test_pack_smoke.py`
- `tests/test_claim_validation_pack.py`

Covers the current outside-facing first-run contour plus bounded helper and review surfaces:

- `start`
- `check`
- `repair-step`
- `telemetry export`
- `bug-packet`

The companion claim-validation pack now also checks that:

- the canonical alpha second-operator contour remains followable without author intuition
- one uglier repeated-doctor continuation contour remains followable even when the loop has already hit its bounded stop condition
- one non-resumable fresh-orchestration contour remains followable without inviting a false resume path
- the current evidence-ownership split excludes harness-only runs from kernel roadmap decisions
- only explicitly strong mixed reports are allowed to count as kernel roadmap evidence with caution
- roadmap moves should now be gated on the classified evidence set, not justified from a single noisy report in isolation

Fresh unseen validation now also lives beside those pack checks:

- measured strict proof lanes must still accept concrete terse evidence on new task shapes
- measured strict proof lanes must still reject narrative-only readback and scenario assertions on new task shapes
- unknown task classes must not inherit strict hostile proof guards automatically

## Current external review contour

See:

- `fixtures/alpha_test_pack_run_004/`

This is the current handoff-quality proof for the outside alpha pack.
