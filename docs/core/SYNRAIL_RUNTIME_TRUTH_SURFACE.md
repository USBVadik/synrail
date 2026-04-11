# SYNRAIL_RUNTIME_TRUTH_SURFACE

## Purpose

Define the operator-facing runtime truth surface for `Synrail`.

This document exists so the current product state can be described without reconstructing it from scattered doctor records, evaluation lanes, and session notes.

## Core rule

`Synrail` should expose runtime truth as a compact fact surface, not as narrative confidence.

The runtime truth surface must answer:

- what is currently trusted
- what is currently observed
- which blocker class is active
- whether the next run class is acceptable
- what the next safe step is

## What runtime truth surface is

Runtime truth surface is the smallest product surface that lets an operator understand:

- baseline identity
- live artifact identity
- active blocker identity
- current run-class readiness
- next safe step

## What runtime truth surface is not

It is not:

- a general dashboard
- a verbose debugging log
- a replacement for doctor records
- a substitute for evaluation lanes

Doctor records and evaluation lanes remain the deeper evidence layers.

Runtime truth surface is the compact operational truth derived from them.

## Required dimensions

A valid runtime truth surface should include:

### 1. Trusted baseline

It must identify the currently trusted kernel surface.

### 2. Observed live surface

It must identify the currently observed live/runtime surface when relevant.

### 3. Active blocker

It must identify the narrowest currently active blocker class.

### 4. Current readiness state

It must identify whether the next intended run class is:

- acceptable
- not acceptable
- partially acceptable for a lower run class only

### 5. Proof state

It must say whether at least one proof-complete exact-task cycle exists under kernel rules.

### 6. Next safe step

It must name one narrow next safe step.

## Relation to other Synrail layers

Runtime truth surface should be derived from:

- `Synrail Doctor`
- `Synrail Evaluation Lane`
- `Synrail Extraction Readiness Checklist`
- active recovery protocols

It should never contradict those deeper artifacts.

## Minimal success condition

This layer is successful when an operator can answer, in under a minute:

- what is the trusted kernel state now
- why exact retry is still blocked or greenlit
- what the narrowest next move is

## Decision rule

If runtime truth surface cannot distinguish:

- trusted baseline vs live observed state
- active blocker vs historical blocker
- current next step vs broad roadmap

then the surface is too weak and must not be treated as a reliable operator view.
