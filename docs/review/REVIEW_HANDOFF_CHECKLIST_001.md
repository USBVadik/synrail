# Review Handoff Checklist 001

Use this when you send the product to an outside critic.

If you need copy-paste outreach text, use:

- [EXTERNAL_ALPHA_SEND_001.md](./EXTERNAL_ALPHA_SEND_001.md)

## Send these things

1. the full repository snapshot
2. `docs/review/EXTERNAL_CRITIQUE_PACK_001.md`
3. `docs/core/ALPHA_LANE_001.md`
4. `docs/core/ALPHA_TEST_PACK_001.md`
5. `tests/test_truth_regressions.py`
6. `tests/test_alpha_test_pack_smoke.py`
7. the relevant fixtures

## Suggested message

Please review this as a narrow proof-first control product, not as a general AI platform.

I want blunt criticism on:

- truth rigor
- hidden self-validation
- workflow usefulness
- unnecessary ceremony
- whether the wedge is strong enough to justify expansion

## Commands to include

```bash
python3 -m venv .venv
.venv/bin/python -m pip install .
python3 -m unittest discover -s tests -p 'test_*.py' -v
```

## Current outward-facing proof to highlight

- `fixtures/alpha_test_pack_run_003/`

## Pre-Alpha No-Go Checklist

Do not send the pack out yet if any of these are false:

1. no absolute author-local paths remain in the external pack
2. the 10-minute quickstart works on a clean machine without author memory
3. every visible shell verb is justified by a real user loss without it
4. the two wow scenarios are both runnable and clearly explain the saved loss
5. default shell wording stays honest about bounded doctor coverage, current proof rules, and unresolved continuation boundaries
6. telemetry export or bug-packet actually reduce feedback effort for an outside tester
7. second-operator handoff does not require us to explain internal grammar out loud

## What not to promise

Do not tell reviewers that this is:

- a polished broad product
- a platform shell
- a general-purpose orchestration layer
- fully benchmarked against the market

That is not the current truth.
