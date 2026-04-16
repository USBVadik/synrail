# Doctor Pressure Test 001

## Purpose

Record the first targeted doctor pressure-test slice for expensive false-readiness reduction.

This document exists so doctor sharpening stays tied to concrete bad-readiness failure modes instead of growing as a broad checklist.

## Focus

This slice targets two false-readiness modes that are easy to miss and expensive to carry forward:

1. credential env is present, but the referenced credential path is invalid
2. exact prompt identity artifact exists, but it does not match the expected task identity

## Artifacts

The current pressure-test artifacts now live at:

- `fixtures/doctor_pressure_test_001/credential_path_missing.json`
- `fixtures/doctor_pressure_test_001/task_identity_mismatch.json`
- `fixtures/doctor_pressure_test_001/exact_prompt_identity_mismatch.txt`

## What was tested

### 1. Credential path false-green

The support-doctor run used:

- `GOOGLE_APPLICATION_CREDENTIALS` present in env
- a missing credential file path
- trusted helper bypass
- viable artifact path

Observed result:

- `final_verdict = NOT_ACCEPTABLE_CREDENTIAL_SURFACE`
- credential gate note = `credential env points to a missing path`

Why it matters:

- this reduces a common false-green shape where presence of a credential env is mistaken for usable readiness

### 2. Exact task identity mismatch

The exact-retry doctor run used:

- a present prompt identity artifact
- an expected task identity of `EXACT_TASK_ALPHA`
- artifact contents that instead named `EXACT_TASK_BETA`

Observed result:

- `final_verdict = NOT_ACCEPTABLE_EXACT_PROMPT_MISSING`
- prompt/task gate note = `exact prompt identity artifact does not match the expected task identity`

Why it matters:

- this reduces a false-green shape where the operator has an exact artifact, but not the right exact artifact

## Current reading

The shortest honest reading is:

- doctor is still intentionally small
- but it now catches two more expensive readiness lies
- credential presence is no longer enough when the referenced path is broken
- exact-retry artifact presence is no longer enough when task identity does not actually match

That is the kind of sharpening the current phase needs.
