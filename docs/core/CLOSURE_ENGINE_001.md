# Closure Engine 001

## Purpose

Define the first executable closure engine for `Synrail`.

This document exists so the product can emit a machine-readable closure decision that says not only "accepted" or "not accepted", but also what is minimally missing before accepted state.

## Artifacts

The first closure-engine slice now lives at:

- `tools/reference/synrail_closure_v0.py`
- `schemas/closure_verdict_v0.schema.json`

## What it does

The closure engine v0 can:

1. read one run-state artifact
2. read one proof-bundle artifact
3. emit a machine-readable closure verdict with:
   - `ACCEPTED`
   - `CLAIMED_NOT_ACCEPTED`
   - `REJECTED`
4. identify the current blocking reason
5. emit the next allowed transition
6. emit one narrow next safe step
7. optionally write the verdict back into the run-state artifact

## Why this matters

Without a closure engine, `Synrail` risks becoming stronger at denial than at honest completion guidance.

The closure engine is the first step toward making closure guidance:

- explicit
- machine-readable
- enforceable
- reviewable

## v0 limitations

The closure engine currently evaluates:

- target-surface attestation
- doctor readiness
- exact-task integrity
- execution completion
- proof-bundle completeness
- recovery reverification

It does not yet perform:

- deep semantic validation of scenario proof
- richer recovery branching
- full refresh-chain automation

Those belong to the next layers.

## Decision rule

Future closure-engine work should strengthen:

- honest accepted vs claimed-not-accepted decisions
- better missing-evidence guidance
- deterministic next-safe-step emission

without turning the engine into a broad orchestration shell.
