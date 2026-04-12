# Doctor Pressure Test 002

## Purpose

Record the first doctor pressure-test slice for wrong target-surface assumption.

This document exists so target-surface truth is not treated as an attestation-only concern while doctor still quietly assumes the operator is pointing at the right surface.

## Focus

This slice targets one expensive false-readiness mode:

- the execution surface exists and looks clean enough
- but the observed target identity does not match the expected target surface for the run

## Artifacts

The current pressure-test artifacts now live at:

- `fixtures/doctor_pressure_test_002/target_identity.txt`
- `fixtures/doctor_pressure_test_002/target_identity_mismatch.json`

## What was tested

### 1. Doctor record

The core-doctor run used:

- a real target path
- a trusted baseline identity
- an expected target identity of `TARGET_SURFACE_ALPHA`
- an observed target identity artifact that instead named `TARGET_SURFACE_BETA`

Observed result:

- `final_verdict = NOT_ACCEPTABLE_BASELINE_IDENTITY`
- baseline gate note = `target identity artifact does not match the expected target surface`

Why it matters:

- this reduces a false-green shape where the operator has a real execution surface but not the intended one

### 2. Operator-path block

The same mismatch was then run through `synrail_cli_v0.py orchestrate`.

Observed result:

- `BLOCKED | doctor | DOCTOR_NOT_GREEN | DOCTOR_BLOCKED | NOT_ACCEPTABLE_BASELINE_IDENTITY`

That matters because the signal is not trapped inside a doctor record.

It now participates in the same bounded runtime contour as the rest of the kernel.

### 3. Matching-path sanity check

When the target identity artifact was changed to `TARGET_SURFACE_ALPHA`, the same contour returned:

- `OK | ACCEPTED | NONE | CLOSURE_ACCEPTED | ACCEPTED`

That keeps the new signal honest.

It blocks mismatch without breaking the green path.

## Current reading

The shortest honest reading is:

- doctor now reduces one more expensive readiness lie
- a clean or existing surface is no longer enough when it is the wrong target surface
- target-surface mismatch now blocks the runtime contour before misleading execution begins
