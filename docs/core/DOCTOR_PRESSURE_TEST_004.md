# DOCTOR_PRESSURE_TEST_004

## Purpose

Record one bounded doctor pressure-test where the credential path exists but the credential JSON is already invalid.

## Scenario

- doctor level: `SUPPORT_DOCTOR`
- helper integrity and clean surface are already acceptable
- credential env points to an existing `.json` file
- that JSON file is malformed

## Expected truth

The doctor must not return green readiness for a credential surface that only looks present on disk.

## Current reading

This closes one more expensive false-ready seam:

- `credential path exists` is no longer enough when the config surface is already invalid JSON
