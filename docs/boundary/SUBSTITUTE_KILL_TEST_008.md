# SUBSTITUTE_KILL_TEST_008

Pressure-test the bounded helper-drift retry stop against a simple manual "keep trying" substitute.

This slice asks one narrow question:
- does Synrail materially improve truth and repair discipline when the substitute path would keep retrying the same helper-drift repair without an explicit no-progress cutoff?

Artifacts:
- `fixtures/substitute_kill_test_008/input_helper_retry_substitute_v2.json`
- `fixtures/substitute_kill_test_008/input_helper_retry_synrail_v2.json`
- `fixtures/substitute_kill_test_008/record_helper_retry.json`
- `fixtures/substitute_kill_test_008/substitute_pressure.json`
