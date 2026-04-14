# DOCTOR_PRESSURE_TEST_006

Run one bounded doctor pressure-test against helper import drift.

## Purpose

This is the next narrow false-ready fix after syntax-only helper checks.
A helper should not count as ready merely because it parses if it already imports a missing module.

## Canonical artifacts

- `tools/reference/synrail_doctor_v1.py`
- `fixtures/doctor_pressure_test_006/broken_import_helper.py`
- `fixtures/doctor_pressure_test_006/doctor.json`

## Expected reading

The doctor record should say:
- `final_verdict = NOT_ACCEPTABLE_HELPER_INTEGRITY`
- helper note points at the missing imported module
- next safe step remains to repair, replace, or safely bypass the helper entrypoint
