# DOCTOR_PRESSURE_TEST_007

This run checks one bounded expensive false-ready mode:
- the execution surface is marked explicitly observed-safe
- but the explicit changed-file set still contains one out-of-scope modification

Inputs:
- target surface: `fixtures/doctor_pressure_test_007`
- allowed scope: `allowed_scope/`
- changed files:
  - `allowed_scope/retry_helper.py`
  - `unrelated_policy.txt`

What we check:
- doctor must not treat explicit observed-safety as enough when the changed-file list already exceeds the allowed repair scope

Expected truth:
- `final_verdict = NOT_ACCEPTABLE_DIRTY_SURFACE`
- `clean_execution_surface.note = execution surface has out-of-scope modifications: unrelated_policy.txt`
