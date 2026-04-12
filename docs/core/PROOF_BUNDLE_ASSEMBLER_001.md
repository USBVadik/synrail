# Proof Bundle Assembler 001

## Purpose

Define the first executable proof-bundle assembler for `Synrail`.

This document exists so proof-first acceptance depends less on manual operator stitching and more on one repeatable assembly step.

## Artifacts

The first assembler slice now lives at:

- `tools/reference/synrail_bundle_v0.py`
- `schemas/proof_bundle_v0.schema.json`

## What it does

The assembler v0 can:

1. read a machine-readable final result artifact
2. extract modified-files and diff/provenance presence
3. record readback presence
4. record scenario-proof presence
5. bind artifact identity fields
6. record cleanup status
7. emit one machine-readable bundle with:
   - `COMPLETE`
   - `PARTIAL`
   - `INVALID`

## Why this matters

Without automatic bundle assembly, proof-first discipline risks becoming:

- operator-heavy
- inconsistent
- easy to skip under pressure

The assembler is the first move toward making proof bundle construction a product capability rather than a ritual.

## v0 limitations

The assembler currently checks:

- section presence
- basic section extraction
- basic bundle status

It does not yet perform:

- deep semantic readback validation
- scenario-proof semantic validation
- full closure decisions

Those belong to the next layers.

## Decision rule

Future assembler work should improve:

- bundle completeness automation
- bundle validity checking
- closure-engine readiness

without turning v0 into a broad orchestration system.
