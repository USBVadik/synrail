# External Alpha Ledger 2026-05

This ledger is the repeatable recording surface for the next ten empirical external alpha runs.

It exists to collect live outside-facing evidence about usefulness.
It is not a replacement for the older curated benchmark and comparison artifacts already in this repo.

## Scope Boundary

Use this ledger only for empirical external runs where a real operator used Synrail on a live task contour.
Do not record curated benchmark fixtures here.
Do not copy local synthetic or curated comparison inputs into this ledger and present them as external proof.

The following repo artifacts remain useful, but they are not empirical external measurements:

- `fixtures/repeatable_everyday_benchmark_pack_001.json`
- `fixtures/cost_of_control_everyday_001.json`
- `fixtures/small_template_text_fix_behavior_pressure_pack_001.json`
- `fixtures/cost_of_control_small_template_text_fix_behavior_pressure_001.json`
- `docs/core/REPEATABLE_EVERYDAY_BENCHMARK_001.md`
- `docs/core/BASELINE_HARNESS_001.md`

## What To Record

For each run, capture:

- task class
- repo type
- agent used
- whether Synrail was already installed before the run
- time to first blocker
- time to accepted closure
- whether false-done was prevented
- operator confusion moments
- manual interventions
- final verdict

Keep the per-run report in the run folder and use [EXTERNAL_ALPHA_RUN_TEMPLATE_001.md](./EXTERNAL_ALPHA_RUN_TEMPLATE_001.md).

## Decision Rule

This ledger should help answer two questions:

1. Is Synrail materially useful on real external task contours?
2. Where is current usefulness still being hidden by product, harness, or operator-tax problems?

Do not move product claims from curated benchmark confidence to empirical external proof until this ledger contains real external runs.

## Run Table

| Run | Date | Repo type | Agent | Task class | Synrail installed before | Time to first blocker | Time to accepted closure | False-done prevented | Operator confusion moments | Manual interventions | Final verdict | Report |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 01 |  |  |  |  |  |  |  |  |  |  |  |  |
| 02 |  |  |  |  |  |  |  |  |  |  |  |  |
| 03 |  |  |  |  |  |  |  |  |  |  |  |  |
| 04 |  |  |  |  |  |  |  |  |  |  |  |  |
| 05 |  |  |  |  |  |  |  |  |  |  |  |  |
| 06 |  |  |  |  |  |  |  |  |  |  |  |  |
| 07 |  |  |  |  |  |  |  |  |  |  |  |  |
| 08 |  |  |  |  |  |  |  |  |  |  |  |  |
| 09 |  |  |  |  |  |  |  |  |  |  |  |  |
| 10 |  |  |  |  |  |  |  |  |  |  |  |  |

## Reading Notes

- `Synrail installed before` should be `yes` or `no`.
- `Time to first blocker` should be the first point where the operator had to stop and react.
- `Time to accepted closure` should stay blank if the run never reached accepted closure.
- `False-done prevented` should be `yes`, `no`, or `unclear`.
- `Manual interventions` should stay short and factual.
- `Final verdict` should describe the actual run outcome, not a hopeful interpretation.
