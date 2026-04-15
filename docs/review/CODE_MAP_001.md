# Code Map 001

This is the shortest useful code-reading guide for an outside technical reviewer.

## If you only read 12 files

1. `alpha.py`
2. `tools/reference/synrail_cli_v0.py`
3. `tools/reference/synrail_spine_v0.py`
4. `tools/reference/synrail_doctor_v1.py`
5. `tools/reference/synrail_bundle_v0.py`
6. `tools/reference/synrail_closure_v0.py`
7. `tools/reference/synrail_acceptance_criteria_v0.py`
8. `tools/reference/synrail_doctor_coverage_v0.py`
9. `tools/reference/synrail_repair_packet_v0.py`
10. `tools/reference/synrail_continuation_arbiter_v0.py`
11. `tests/test_truth_regressions.py`
12. `tests/test_alpha_test_pack_smoke.py`

## Entry points

### Installable CLI

- `alpha.py`

### Main shell facade

- `tools/reference/synrail_cli_v0.py`

### Core state machine

- `tools/reference/synrail_spine_v0.py`

## Truth-critical modules

### Doctor and coverage

- `tools/reference/synrail_doctor_v1.py`
- `tools/reference/synrail_doctor_coverage_v0.py`
- `tools/reference/doctor_coverage_profile_v0.json`
- `tools/reference/doctor_coverage_corpus_v0.json`

### Proof and closure

- `tools/reference/synrail_bundle_v0.py`
- `tools/reference/synrail_closure_v0.py`
- `tools/reference/synrail_refresh_v0.py`

### Acceptance truth

- `tools/reference/synrail_acceptance_criteria_v0.py`

### Continuation

- `tools/reference/synrail_repair_handoff_v0.py`
- `tools/reference/synrail_repair_packet_v0.py`
- `tools/reference/synrail_continuation_arbiter_v0.py`
- `tools/reference/synrail_second_operator_v0.py`

### Export and observability

- `tools/reference/synrail_observability_v0.py`
- `tools/reference/synrail_alpha_telemetry_v0.py`
- `tools/reference/synrail_bug_packet_v0.py`

## Tests

Truth-critical regression suite:

- `tests/test_truth_regressions.py`

Current outside-facing smoke:

- `tests/test_alpha_test_pack_smoke.py`

## Best fixtures to inspect

### Current tester-pack contour

- `fixtures/alpha_test_pack_run_003/`

### Current shell contour

- `fixtures/alpha_shell_run_008/`

### Acceptance hardening

- `fixtures/acceptance_independence_run_001/`

### Semantic proof hardening

- `fixtures/semantic_proof_hardening_run_001/`

### Doctor measured coverage

- `fixtures/doctor_measured_coverage_run_001/`

### Continuation arbiter

- `fixtures/continuation_arbiter_run_001/`
- `fixtures/continuation_arbiter_conflict_run_001/`

## Commands a reviewer can run

Full suite:

```bash
python3 -m unittest discover -s tests -p 'test_*.py' -v
```

Current tester-pack smoke:

```bash
python3 -m unittest tests.test_alpha_test_pack_smoke -v
```

Validate one exported outward-facing contour:

```bash
python3 tools/reference/synrail_validate_v0.py --schema schemas/thin_output_record_v0.schema.json --document fixtures/alpha_test_pack_run_003/lane/thin_output.json
python3 tools/reference/synrail_validate_v0.py --schema schemas/repair_prompt_bridge_record_v0.schema.json --document fixtures/alpha_test_pack_run_003/lane/prompt.json
python3 tools/reference/synrail_validate_v0.py --schema schemas/alpha_session_replay_record_v0.schema.json --document fixtures/alpha_test_pack_run_003/lane/telemetry/session_replay.json
```

## Reading suggestion by concern

If you care most about false accept:

- `synrail_bundle_v0.py`
- `synrail_closure_v0.py`
- `tests/test_truth_regressions.py`

If you care most about readiness honesty:

- `synrail_doctor_v1.py`
- `synrail_doctor_coverage_v0.py`
- `doctor_coverage_corpus_v0.json`

If you care most about continuation:

- `synrail_repair_packet_v0.py`
- `synrail_continuation_arbiter_v0.py`
- `synrail_second_operator_v0.py`

If you care most about product usefulness:

- `synrail_cli_v0.py`
- `tests/test_alpha_test_pack_smoke.py`
- `docs/core/ALPHA_TEST_PACK_001.md`
