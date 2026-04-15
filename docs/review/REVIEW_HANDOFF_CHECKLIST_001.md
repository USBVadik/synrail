# Review Handoff Checklist 001

Use this when you send the product to an outside critic.

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
python3 -m venv --system-site-packages .venv
.venv/bin/python -m pip install -e . --no-build-isolation
python3 -m unittest discover -s tests -p 'test_*.py' -v
```

## Current outward-facing proof to highlight

- `fixtures/alpha_test_pack_run_001/`

## What not to promise

Do not tell reviewers that this is:

- a polished broad product
- a platform shell
- a general-purpose orchestration layer
- fully benchmarked against the market

That is not the current truth.
