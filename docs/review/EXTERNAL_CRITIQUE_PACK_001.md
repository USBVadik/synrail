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

The current product form is one narrow controlled-start alpha lane over that kernel.

## What to hand to a critic

Give them:

1. the exact selected repository snapshot at the commit you want reviewed
2. this review pack under `docs/review/`
3. the current alpha lane docs under `docs/core/`
4. the full source tree
5. the fixtures and tests

Use one explicitly selected snapshot for docs, tests, fixtures, and message. Do not assemble the review packet from a drifting local working tree.

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
- one narrow controlled-start workflow
- explicit acceptance criteria
- measured doctor coverage gate
- executable continuation arbiter
- regression tests for truth-critical failures
- a compact external tester pack plus claim-validation pack
- refresh-driven stale-obligation guidance in the default non-green shell
- one repeatable everyday benchmark pack whose broader class is still baseline-favorable overall
- one narrow focused `small_template_text_fix` family with two repeatable low-drag winners and a machine-readable split where the canonical pack reads `FOCUSED_CLASS_CHEAP_ENOUGH` plus `FOCUSED_CLASS_BEHAVIOR_CHEAP_BY_DEFAULT`, but same-family pressure can still keep kernel cheapness while dropping behavior cheapness to `FOCUSED_CLASS_BEHAVIOR_NOT_YET_CHEAP_BY_DEFAULT`

Read that as one narrow focused win, not as a class victory: the broader everyday lane is still `BASELINE_GOOD_ENOUGH`, and same-family pressure already shows behavior cheapness is not fully independent.

But it is still intentionally narrow:

- one alpha contour
- no broad product shell
- no hosted telemetry
- no broad packaging polish
- no claim of general domain correctness

## What we most want criticized

We do not want polite feedback.

We want pressure on:

1. whether the broader everyday lane beats simpler substitutes, or whether the current `small_template_text_fix` win is still too narrow to justify the control mass
2. which proof surface still feels self-issued or too author-shaped to trust
3. whether restore, re-entry, or handoff value is concrete enough to justify the ceremony
4. what you would cut first if that value is still too weak

## Current runnable review surfaces

Start here for live runnable and fixture-backed review:

- [../core/ALPHA_TEST_PACK_001.md](../core/ALPHA_TEST_PACK_001.md)
- [../core/ALPHA_LANE_001.md](../core/ALPHA_LANE_001.md)
- [../core/ALPHA_TELEMETRY_001.md](../core/ALPHA_TELEMETRY_001.md)
- [../../tests/test_truth_regressions.py](../../tests/test_truth_regressions.py)
- [../../tests/test_alpha_test_pack_smoke.py](../../tests/test_alpha_test_pack_smoke.py)
- [../../tests/test_claim_validation_pack.py](../../tests/test_claim_validation_pack.py)
- [../../tests/test_everyday_benchmark_pack.py](../../tests/test_everyday_benchmark_pack.py)
- `fixtures/repeatable_everyday_benchmark_pack_001.json`
- `fixtures/cost_of_control_everyday_001.json`

## Recommended review commands

Install:

```bash
python3 tools/reference/synrail_install_v0.py --venv .venv
```

Run the full current test suite:

```bash
python3 -m unittest discover -s tests -p 'test_*.py' -v
```

Run the current alpha tester-pack smoke only:

```bash
python3 -m unittest tests.test_alpha_test_pack_smoke -v
```

Run the current claim-validation pack:

```bash
python3 -m unittest tests.test_claim_validation_pack -v
```

## Questions we want answered

1. Which step in the everyday lane feels least worth its weight?
2. Which runtime artifact still feels self-issued or too hard to trust?
3. Where does the shell still ask for confidence the current proof does not earn?
4. In restore, re-entry, or handoff, what concrete value does `Synrail` create over a simpler substitute?
5. If that value is still weak, what would you freeze or remove before broader alpha?
