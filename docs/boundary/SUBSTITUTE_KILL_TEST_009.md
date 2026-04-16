# SUBSTITUTE_KILL_TEST_009

Pressure-test the alpha lane on one real painful scenario:

- the agent leaves one plain-text bounded change result
- the result is not machine-readable enough to support a proof bundle
- a manual operator could still be tempted to treat it as "looks fine enough"

This slice asks one narrow question:

- does `Synrail` beat one disciplined manual baseline by blocking false confidence and pointing to one bounded repair step?

Artifacts:

- [input_plaintext_invalid_proof_substitute_v2.json](/Users/usbdick/Documents/New%20project/synrail/fixtures/substitute_kill_test_009/input_plaintext_invalid_proof_substitute_v2.json)
- [input_plaintext_invalid_proof_synrail_v2.json](/Users/usbdick/Documents/New%20project/synrail/fixtures/substitute_kill_test_009/input_plaintext_invalid_proof_synrail_v2.json)
- [record_invalid_proof.json](/Users/usbdick/Documents/New%20project/synrail/fixtures/substitute_kill_test_009/record_invalid_proof.json)
- [substitute_pressure.json](/Users/usbdick/Documents/New%20project/synrail/fixtures/substitute_kill_test_009/substitute_pressure.json)

Winning phrase:

- `Synrail` is better than the disciplined manual baseline in this invalid-proof scenario because it converts one "looks fine enough" artifact into one explicit `PROOF_INVALID` contour with one bounded repair step instead of leaving the operator to infer proof truth by hand.
