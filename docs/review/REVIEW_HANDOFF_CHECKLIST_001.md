# Review Handoff Checklist 001

Use this when you send the product to an outside critic.

If you need copy-paste outreach text, use:

- [EXTERNAL_ALPHA_SEND_001.md](./EXTERNAL_ALPHA_SEND_001.md)

## Send these things

1. the exact repository snapshot selected for review
2. `docs/review/EXTERNAL_CRITIQUE_PACK_001.md`
3. `docs/review/CRITIC_REVIEW_BRIEF_2026-04-19.md`
4. `docs/core/ALPHA_LANE_001.md`
5. `docs/core/ALPHA_TEST_PACK_001.md`
6. `tests/test_truth_regressions.py`
7. `tests/test_alpha_test_pack_smoke.py`
8. `tests/test_claim_validation_pack.py`
9. the relevant fixtures

Use one explicitly selected snapshot for docs, tests, fixtures, and message. Do not assemble the packet from a drifting local working tree.

## Suggested message

Please review this as a narrow proof-first control product, not as a general AI platform.

I want blunt criticism on:

- where the everyday lane still feels heavier than the loss it prevents
- which proof artifact or shell claim still feels self-issued
- whether restore, re-entry, or handoff value is strong enough to justify the control mass
- what they would cut first if that value is still too weak

## Commands to include

```bash
make install-dev
python3 -m unittest discover -s tests -p 'test_*.py' -v
```

## Current outward-facing proof to highlight

- `fixtures/alpha_test_pack_run_004/`

## Pre-Alpha No-Go Checklist

Do not send the pack out yet if any of these are false:

1. no absolute author-local paths remain in the external pack
2. the 10-minute quickstart works on a clean machine without author memory
3. every visible shell verb is justified by a real user loss without it
4. the two wow scenarios are both runnable and clearly explain the saved loss
5. default shell wording stays honest about bounded doctor coverage, current proof rules, unresolved continuation boundaries, and the current narrow restore/path-trust boundary
6. telemetry export or bug-packet actually reduce feedback effort for an outside tester
7. second-operator handoff does not require us to explain internal grammar out loud
8. the docs, tests, fixtures, message, and reviewer return templates all match the exact selected snapshot rather than a drifting local working tree
9. restore wording stays exact: path-trust-hardened on a narrow local matrix, with direct target-path rechecks before restore and rollback writes, not broad restore maturity
10. the outgoing packet includes `docs/review/FEEDBACK_INTAKE_001.md` and `docs/review/ALPHA_SIGNAL_SCORECARD_001.md` so the first outside signal comes back in one explicit shape

## What not to promise

Do not tell reviewers that this is:

- a polished broad product
- a platform shell
- a general-purpose orchestration layer
- fully benchmarked against the market

That is not the current truth.
