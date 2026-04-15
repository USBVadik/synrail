# ALPHA_EXTERNAL_RUN_001

Record one external-ish alpha run outside the curated fixture grammar.

This slice uses:

- one fresh artifact root in `/tmp`
- one plain-text `final_result.txt`
- one bounded change contour with explicit prompt/task identity

The key point is that this is not a pre-shaped canonical fixture path.

It asks one narrow question:

- when the agent leaves one human-readable result instead of one machine-readable final-result artifact, does the alpha lane still fail honestly and stay usable?

Artifacts:

- [external run 001 state](../../fixtures/alpha_external_run_001/state.json)
- [external run 001 report](../../fixtures/alpha_external_run_001/report.json)
- [external run 001 thin output](../../fixtures/alpha_external_run_001/thin_output.json)
- [external run 001 prompt](../../fixtures/alpha_external_run_001/prompt.json)
- [externality pressure](../../fixtures/alpha_externality_run_001/pressure.json)

Results:

- `reason = INVALID_PROOF_BUNDLE`
- `outcome_class = PROOF_INVALID`
- `current_step_id = repair_final_result_artifact`
- `externality verdict = SURVIVES_SHORT_EXTERNAL_PRESSURE`

What this run uncovered:

- before this tranche, a plain-text final result could crash the bundle helper instead of yielding one honest non-green contour

What changed:

- bundle assembly now treats non-JSON final-result artifacts as `INVALID` proof instead of crashing the runtime path

Failure inventory after the fix:

- Doctor coverage:
  - not the failing layer here; doctor still passes because the problem is proof-surface shape after execution
- Packet/history weight:
  - acceptable on this contour; the packet names one current step and one required input cleanly
- Output clarity:
  - acceptable; the operator gets `PROOF_INVALID` plus one bounded next step
- Restore/resume usability:
  - restore is not offered because no verified checkpoint exists on this fresh contour, which is the correct reading

Why this matters:

- the alpha lane now survives one real-ish, ugly, non-canonical mistake
- the operator still gets one bounded repair path instead of a runtime exception or silent false success
