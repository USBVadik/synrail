# Doctor Hardening 001

## Purpose

Make Doctor coverage an explicit runtime truth object instead of a doc-only claim.

This slice adds:

- one machine-readable doctor coverage profile
- one machine-readable doctor coverage record
- one coverage threshold policy
- one doctor gate that blocks green readiness if agreed critical fail modes are not covered

## What changed

Doctor now carries a `coverage` object in `doctor.json`.

That object records:

- covered fail modes
- partially covered fail modes
- uncovered fail modes
- agreed critical fail modes
- threshold policy
- whether the threshold is currently met

If the threshold is not met, Doctor does not emit an acceptable verdict even when the current bounded probes would otherwise pass.

## Proofs

### 1. Current coverage profile passes the gate

See:

- `../fixtures/doctor_hardening_run_001/coverage_default.json`
- `../fixtures/doctor_hardening_run_001/doctor_default.json`

Result:

- `gate_status = PASS`
- `gate_reason = CRITICAL_FAIL_MODE_COVERAGE_MET`
- `final_verdict = ACCEPTABLE_FOR_CORE_RUN`

### 2. Weakened critical coverage does not get a false READY

See:

- `../fixtures/doctor_hardening_run_001/coverage_profile_weakened.json`
- `../fixtures/doctor_hardening_run_001/coverage_blocked.json`
- `../fixtures/doctor_hardening_run_001/doctor_coverage_blocked.json`

Result:

- `gate_status = BLOCKED`
- `gate_reason = CRITICAL_FAIL_MODE_COVERAGE_INCOMPLETE`
- `final_verdict = NOT_ACCEPTABLE_DOCTOR_COVERAGE`
- `blocking_failure_classes = [doctor-coverage incomplete]`

This matters because Doctor can no longer look green just because the current narrow probes passed while the agreed critical fail-mode coverage has regressed.

### 3. Runtime `synrail check` now carries the doctor coverage truth

See:

- `../fixtures/doctor_runtime_check_run_001/lane/doctor.json`
- `../fixtures/doctor_runtime_check_run_001/check_stdout.txt`

This proves the new coverage gate is not only a helper-side artifact. It now flows through the normal alpha runtime contour.

## Boundary

This slice does not make Doctor broader on paper.

It makes Doctor more honest about what its current bounded coverage is allowed to claim.
