# DOCTOR_PRESSURE_TEST_003

## Purpose

Record one bounded doctor pressure-test where the helper entrypoint exists but is already broken.

## Scenario

- doctor level: `SUPPORT_DOCTOR`
- helper path exists
- helper path is a Python entrypoint with invalid syntax

## Expected truth

The doctor must not return green readiness for a helper surface that only looks present.

## Current reading

This is one small but important false-readiness reduction:

- `helper exists` is no longer enough when the helper entrypoint is already parse-broken
