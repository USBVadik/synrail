# SYNRAIL_TRANSITION_GATE_STANDARD

## Purpose

Define how `Synrail` evaluates whether a product-state transition is actually allowed.

This document exists so transitions between readiness, execution, proof, and closure states are governed by explicit gate checks rather than by narrative momentum.

## Core rule

A `Synrail` state transition is allowed only when:

- the source state is explicit
- the target state is explicit
- the transition conditions are explicit
- the evidence basis is explicit
- no active blocker contradicts the transition

## What a transition gate is

A transition gate is the product mechanism that answers:

- may this task move from its current state to the next state right now?

It does not answer by optimism.

It answers by checking the required evidence surfaces.

## Required inputs for a transition gate

A valid transition gate may depend on:

- doctor verdicts
- evaluation-lane state
- runtime truth surface
- closure state
- recovery protocol completion
- active blocker list

## Minimal gate questions

Every transition gate should answer:

1. what is the current source state?
2. what is the proposed target state?
3. what evidence is required for this transition?
4. which active blocker still prevents it, if any?
5. what is the narrow next safe step if the transition is denied?

## Allowed gate results

A transition gate should return one of:

- `ALLOW`
- `DENY`
- `DENY_WITH_RECOVERY_PATH`

## Decision rule

If the gate cannot prove the transition is allowed, it must deny it.

In `Synrail`, unknown transition status is not treated as soft approval.
