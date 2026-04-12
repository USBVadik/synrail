# Run State Schema 001

## Purpose

Define the first machine-readable run-state shape for `Synrail`.

This document exists so kernel state can move out of prose-first interpretation and into a canonical structured artifact.

## Artifact

The first schema artifact now lives at:

- `schemas/run_state_v0.schema.json`

## Why it exists

The current product risk is that state remains better described than enforced.

The run-state schema is the first corrective move toward:

- one canonical state artifact
- explicit gate inputs
- traceable transitions
- machine-readable closure status

## Minimum state fields

The first schema includes:

- run identity
- task class
- current state
- target surface state
- doctor state
- integrity state
- execution state
- proof-bundle state
- closure state
- recovery state
- next safe step

## Design rule

The schema is intentionally small.

It is not trying to encode every historical nuance.

It only carries the fields needed for:

- transition gating
- closure decisions
- next-step emission

## Current state model

The first state set is:

- `INITIALIZED`
- `TARGET_SURFACE_ATTESTED`
- `READY`
- `EXECUTION_COMPLETED`
- `PROOF_BUNDLE_COMPLETE`
- `CLOSURE_ACCEPTED`
- `CLOSURE_REJECTED`
- `RECOVERY_PENDING`

## Decision rule

If a state field is not needed for gating, closure, or next-safe-step emission, it should not automatically enter the v0 schema.
