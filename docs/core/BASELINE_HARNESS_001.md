# Baseline Harness 001

## Purpose

Define the first executable baseline comparison harness for `Synrail`.

This document exists so comparison with a simpler stack can move from hand-written interpretation toward one repeatable machine-readable record.

## Artifacts

The first baseline-harness slice now lives at:

- `tools/reference/synrail_baseline_harness_v0.py`
- `tools/reference/synrail_cli_v0.py`
- `schemas/comparison_input_v0.schema.json`
- `schemas/baseline_comparison_record_v0.schema.json`

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

## v0 limitations

The harness currently does not perform:

- deep scenario normalization
- operator-minute accounting
- repeated-run statistical comparison

Those belong to later layers.

## Decision rule

Future harness work should strengthen:

- faithful comparison against simpler baselines
- traceable verdict logic
- lower prose-dependence in product claims

without turning the harness into a broad benchmarking platform too early.
