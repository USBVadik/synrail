# Baseline Harness 001

## Purpose

Define the first executable baseline comparison harness for `Synrail`.

This document exists so comparison with a simpler stack can move from hand-written interpretation toward one repeatable machine-readable record.

## Artifacts

The first baseline-harness slice now lives at:

- `tools/reference/synrail_baseline_harness_v0.py`
- `tools/reference/synrail_baseline_harness_v1.py`
- `tools/reference/synrail_cli_v0.py`
- `schemas/comparison_input_v0.schema.json`
- `schemas/comparison_input_v1.schema.json`
- `schemas/baseline_comparison_record_v0.schema.json`
- `schemas/baseline_comparison_record_v1.schema.json`

## What it does

The harness v0 can:

1. read one baseline comparison input
2. read one `Synrail` comparison input
3. compare a small fixed metric set
4. emit one machine-readable comparison record
5. classify the result as:
   - `SYNRAIL_BETTER`
   - `BASELINE_GOOD_ENOUGH`
   - `UNCLEAR`

The active economics slice now adds a `v1` path that can:

1. compare one baseline path against one `Synrail` path
2. retain the earlier qualitative metrics
3. add simple economic counters
4. emit one machine-readable why-verdict plus one economics summary

## Why this matters

Without a harness, baseline comparison risks staying:

- prose-heavy
- inconsistent
- easy to bias after the fact

The harness is the first move toward making comparison a product self-check rather than a narrative judgment.

## v0 metric set

The current harness compares:

- false-success risk
- proof completeness
- recovery cost
- coordination overhead
- blocker-to-closure cycles are retained in the input artifact for traceability

## v1 metric set

The active economics harness now also records:

- scenario class
- path identity
- operator minutes
- intervention count
- repair cycles
- invalidation count
- closure latency in minutes
- false-green exposure
- artifact completeness percent
- mandatory mental steps
- trust-bearing artifact count
- visible surface count
- skippable visible surface count

It also emits one compact economics summary:

- added operator minutes
- added interventions
- added repair cycles
- added invalidations
- added closure latency
- reduced false-green exposure
- gained artifact completeness
- added mandatory mental steps
- added trust-bearing artifacts
- added required visible surfaces
- added skippable visible surfaces
- added fixed control mass

The repo now also has one bounded repeatable everyday benchmark class built on top of the same comparison and cost artifacts:

- `fixtures/repeatable_everyday_benchmark_pack_001.json`
- `fixtures/cost_of_control_everyday_001.json`
- `tests/test_everyday_benchmark_pack.py`

That pack is intentionally narrow.
It exists to pressure-test whether the cheapened contour is becoming everyday-cheap,
not to widen the harness into a broad benchmark platform.

## Current limitations

The harness currently still does not perform:

- deep scenario normalization
- repeated-run statistical comparison
- automatic live capture of operator effort from runtime sessions
- a full economic model of when extra control is worth paying for

That is intentional. The near-term job is to make comparison less descriptive and more falsifiable, not to turn it into a broad benchmarking platform.

## Decision rule

Future harness work should strengthen:

- faithful comparison against simpler baselines
- traceable verdict logic
- lower prose-dependence in product claims
- clearer economics around where `Synrail` earns or fails to earn its extra control cost

without turning the harness into a broad benchmarking platform too early.

## v2 substitute-pressure slice

The active comparison layer now also has one `v2` path that can:

1. compare `Synrail` against one named substitute stack
2. keep the same bounded economics counters
3. emit one substitute-specific machine-readable record
4. aggregate several substitute records into one pressure reading

The current substitute stacks are intentionally simple:

- `temp_clone_strict_validation`
- `ci_approval_checklist`
- `bounded_patch_validation_loop`
