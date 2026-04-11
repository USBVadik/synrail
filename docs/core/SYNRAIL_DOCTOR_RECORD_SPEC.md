# SYNRAIL_DOCTOR_RECORD_SPEC

## Purpose

Define the minimal machine-readable and operator-readable record format for a `Synrail Doctor` run.

This spec exists so doctor verdicts are:

- comparable across cycles
- promotable into failure memory
- usable before support runs and exact retries

## Required fields

A doctor record must include:

- `doctor_run_id`
- `doctor_level`
- `target_execution_surface`
- `trusted_baseline`
- `intended_run_class`
- `gate_results`
- `blocking_failure_classes`
- `final_verdict`
- `recommended_next_safe_step`
- `timestamp`

## Field meanings

### `doctor_run_id`

A stable named identifier for the doctor cycle.

Example:

- `SYNRAIL_DOCTOR_SUPPORT_READINESS_001`

### `doctor_level`

One of:

- `CORE_DOCTOR`
- `SUPPORT_DOCTOR`
- `EXACT_RETRY_DOCTOR`

### `target_execution_surface`

Must identify:

- path
- runtime role
- whether the surface is:
  - trusted clean
  - live observed
  - dirty observed

### `trusted_baseline`

Must identify the trusted artifact for comparison.

At minimum:

- trusted path or artifact
- commit or named artifact identity when known

### `intended_run_class`

One of:

- `core_probe`
- `support_run`
- `exact_retry`

### `gate_results`

Each doctor record must report these gates:

- `baseline_identity`
- `clean_execution_surface`
- `helper_integrity`
- `credential_surface`
- `artifact_viability`
- `prompt_task_identity`

Each gate must be one of:

- `PASS`
- `FAIL`
- `NOT_APPLICABLE`

Each gate should also contain a short note.

### `blocking_failure_classes`

Must list any currently active failure classes that block the intended run.

### `final_verdict`

Must be one of the verdict classes defined in `docs/core/SYNRAIL_DOCTOR.md`.

### `recommended_next_safe_step`

Must name one narrow next action.

It must not be a broad roadmap item.

## Minimal example

```yaml
doctor_run_id: SYNRAIL_DOCTOR_SUPPORT_READINESS_001
doctor_level: SUPPORT_DOCTOR
target_execution_surface:
  path: /tmp/usbagent_clean_clone
  classification: trusted_clean_path
trusted_baseline:
  path: /tmp/usbagent_clean_clone
  head: 3cc13f6f80378ed303797393f2fe47299780f8a4
intended_run_class: support_run
gate_results:
  baseline_identity:
    status: PASS
    note: trusted clean path is named
  clean_execution_surface:
    status: PASS
    note: support path is trusted clean, not dirty live repo
  helper_integrity:
    status: PASS
    note: direct aider invocation bypasses contaminated helper
  credential_surface:
    status: FAIL
    note: no Bedrock credential surface found
  artifact_viability:
    status: PASS
    note: timeout and failure paths now return JSON artifacts
  prompt_task_identity:
    status: NOT_APPLICABLE
    note: support doctor, not exact retry doctor
blocking_failure_classes:
  - credential-surface missing
final_verdict: NOT_ACCEPTABLE_CREDENTIAL_SURFACE
recommended_next_safe_step: restore Bedrock credentials on the intended support surface
timestamp: 2026-04-11
```

## Decision rule

If a required gate is not explicitly evaluated, the doctor record is incomplete.

An incomplete doctor record must not be treated as a green preflight.
