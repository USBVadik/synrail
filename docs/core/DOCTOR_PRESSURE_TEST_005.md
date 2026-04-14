# DOCTOR_PRESSURE_TEST_005

Run one short doctor pressure-test against an obvious placeholder credential env.

## Purpose

This is a bounded false-ready fix.
We do not want the doctor to treat a merely present env var as enough readiness truth when the value is still an obvious placeholder like `CHANGE_ME`.

## Canonical artifacts

- `tools/reference/synrail_doctor_v1.py`
- `fixtures/doctor_pressure_test_005/doctor.json`

## Expected reading

The doctor record should say:
- `final_verdict = NOT_ACCEPTABLE_CREDENTIAL_SURFACE`
- blocking failure remains on the credential surface
- next safe step is still to restore real provider credentials

This keeps the doctor narrow, but makes one cheap and expensive false green much harder to miss.
