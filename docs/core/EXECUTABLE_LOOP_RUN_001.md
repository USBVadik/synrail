# Executable Loop Run 001

## Purpose

Record the first internal end-to-end run through the current executable `Synrail` stack.

This document exists so the repo can point to one concrete internal proof run rather than only to isolated slice-level checks.

## Scenario

- run id: `EXECUTABLE_LOOP_RUN_001`
- task class: `bounded_router_trigger_fix`
- final-result source:
  - `/Users/usbdick/Documents/New project/docs/context/runtime_artifacts/NODE2_IMAGE_TRIGGER_FIX_001_CAMPAIGN_RUN_012.json`

## Artifacts

The run artifacts now live under:

- `fixtures/executable_loop_run_001/`

Included artifacts:

- `state.json`
- `doctor.json`
- `bundle.json`
- `closure.json`
- `refresh.json`
- `comparison.json`
- `orchestration.json`
- `readback.txt`
- `scenario.txt`

## What was executed

The run used the current executable stack:

1. `synrail_cli_v0.py init`
2. `synrail_cli_v0.py doctor`
3. `synrail_cli_v0.py bundle-check`
4. `synrail_cli_v0.py apply-bundle`
5. `synrail_cli_v0.py closure`
6. `synrail_cli_v0.py apply-closure`
7. `synrail_cli_v0.py refresh`
8. `synrail_baseline_harness_v0.py`

## Observed path

### 1. Closure path

Before proof assembly, the run emitted a green doctor record:

- verdict = `ACCEPTABLE_FOR_SUPPORT_RUN`

And the doctor reading now reflects bounded readiness probes rather than a purely flag-driven surface:

- observed execution surface
- viable artifact path
- helper entrypoint present
- required credential env present

With:

- attested target surface
- green doctor
- confirmed exact-task identity
- complete proof bundle

the run reached:

- `CLOSURE_ACCEPTED`

This confirms that the current stack can carry one internal run to accepted closure state.

### 2. Recovery invalidation path

After a simulated recovery-affecting event:

- `RECOVERY_EVENT`
- `recovery_status = PENDING`

the refresh layer downgraded the run to:

- closure status = `CLAIMED_NOT_ACCEPTED`
- blocking reason = `RECOVERY_REVERIFICATION_INCOMPLETE`
- next safe step = `run reverification against the attested target surface`

This confirms the anti-drift property:

- higher-level closure does not remain greener than lower-level recovery truth

### 3. Baseline comparison path

Using the strong comparison fixtures:

- `fixtures/comparison_input_strong_baseline_v0.json`
- `fixtures/comparison_input_strong_synrail_v0.json`

the harness emitted:

- verdict = `SYNRAIL_BETTER`

## Why this run matters

This is the first internal run where the repo can point to one connected chain of behaviors:

- state initialization
- proof bundle assembly
- closure decision
- recovery-driven invalidation
- baseline comparison

It is still sanitized and narrow.

But it is materially stronger than saying the kernel slices only work independently.

This run now also has one canonical worked orchestration envelope:

- `fixtures/executable_loop_run_001/orchestration.json`

That gives one compact machine-readable entrypoint for the full internal reading:

- doctor verdict
- bundle status
- closure result
- refresh invalidation
- comparison verdict
- resulting state

This envelope is now representable as a direct orchestration output, not only as a manually assembled repo artifact.

It also now reflects the final post-refresh reading rather than an earlier pre-refresh closure snapshot.

## What this does not prove

It does not prove:

- broad runtime readiness
- multi-run statistical superiority
- production-grade orchestration

It only proves that the current small kernel stack can already execute one coherent internal loop.
