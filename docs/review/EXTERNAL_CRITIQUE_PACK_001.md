# External Critique Pack 001

This pack exists so an outside reviewer can attack `Synrail` without first reconstructing the project from scattered internal docs.

It is not a marketing shell.

It is a review handoff.

## What Synrail is

`Synrail` is a proof-first control kernel for agent execution.

Its core claim is simple:

- claimed done is not accepted done

The product tries to make agent work reviewable and recoverable by forcing execution through explicit truth surfaces:

- target surface / baseline identity
- doctor readiness
- proof bundle quality
- closure acceptance
- restore and continuation rules

The current product form is one narrow alpha lane over that kernel.

## What to hand to a critic

Give them:

1. the repository snapshot at the commit you want reviewed
2. this review pack under `docs/review/`
3. the current alpha lane docs under `docs/core/`
4. the full source tree
5. the fixtures and tests

If you want a send-ready reviewer message and exact handoff packet, use:

- [EXTERNAL_ALPHA_SEND_001.md](./EXTERNAL_ALPHA_SEND_001.md)

Do not send only a pitch.

The code is part of the review surface.

## Reading order

Fast path, 15-20 minutes:

1. [../core/ALPHA_TEST_PACK_001.md](../core/ALPHA_TEST_PACK_001.md)
2. [PRODUCT_MEMO_001.md](./PRODUCT_MEMO_001.md)
3. [KNOWN_WEAKNESSES_001.md](./KNOWN_WEAKNESSES_001.md)
4. [PITCH_DECK_001.md](./PITCH_DECK_001.md)

Real review path, 45-90 minutes:

1. [PRODUCT_MEMO_001.md](./PRODUCT_MEMO_001.md)
2. [TECHNICAL_MAP_001.md](./TECHNICAL_MAP_001.md)
3. [ROADMAP_STATUS_001.md](./ROADMAP_STATUS_001.md)
4. [CODE_MAP_001.md](./CODE_MAP_001.md)
5. [CRITIC_GUIDE_001.md](./CRITIC_GUIDE_001.md)

Deep technical review path:

1. [TECHNICAL_MAP_001.md](./TECHNICAL_MAP_001.md)
2. [CODE_MAP_001.md](./CODE_MAP_001.md)
3. [KNOWN_WEAKNESSES_001.md](./KNOWN_WEAKNESSES_001.md)
4. [../core/ACCEPTANCE_HARDENING_001.md](../core/ACCEPTANCE_HARDENING_001.md)
5. [../core/DOCTOR_HARDENING_001.md](../core/DOCTOR_HARDENING_001.md)
6. [../core/CONTINUATION_AUTONOMY_001.md](../core/CONTINUATION_AUTONOMY_001.md)
7. [../core/ALPHA_LANE_001.md](../core/ALPHA_LANE_001.md)

## Current status in one paragraph

`Synrail` is no longer just a conceptual kernel. It now has:

- one installable alpha shell
- one narrow first-run workflow
- explicit acceptance criteria
- measured doctor coverage gate
- executable continuation arbiter
- regression tests for truth-critical failures
- a compact external tester pack

But it is still intentionally narrow:

- one alpha contour
- no broad product shell
- no hosted telemetry
- no broad packaging polish
- no claim of general domain correctness

## What we most want criticized

We do not want polite feedback.

We want pressure on:

1. whether the truth surfaces are actually strict enough
2. whether the kernel still self-validates in hidden ways
3. whether the first alpha contour still has unnecessary ceremony
4. whether the default shell says something useful or just translates internal jargon
5. whether the system wins against simpler substitutes in enough real situations

## Current runnable review surfaces

Start here for live runnable and fixture-backed review:

- [../core/ALPHA_TEST_PACK_001.md](../core/ALPHA_TEST_PACK_001.md)
- [../core/ALPHA_LANE_001.md](../core/ALPHA_LANE_001.md)
- [../core/ALPHA_TELEMETRY_001.md](../core/ALPHA_TELEMETRY_001.md)
- [../../tests/test_truth_regressions.py](../../tests/test_truth_regressions.py)
- [../../tests/test_alpha_test_pack_smoke.py](../../tests/test_alpha_test_pack_smoke.py)

## Recommended review commands

Install:

```bash
python3 -m venv --system-site-packages .venv
.venv/bin/python -m pip install -e . --no-build-isolation
```

Run the full current test suite:

```bash
python3 -m unittest discover -s tests -p 'test_*.py' -v
```

Run the current alpha tester-pack smoke only:

```bash
python3 -m unittest tests.test_alpha_test_pack_smoke -v
```

## Questions we want answered

1. What part of the kernel still looks strict by form but weak by substance?
2. Where would you expect false accept or false reject to still leak through?
3. Which runtime artifact is still too self-issued or too hard to trust?
4. Which part of the alpha lane still feels like operator ceremony instead of workflow?
5. If you were going to cut scope harder before broader alpha, what would you freeze or remove?
