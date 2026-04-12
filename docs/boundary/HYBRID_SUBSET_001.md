# Hybrid Subset 001

## Purpose

Define the smallest useful middle mode between the full `Synrail` governed path and the lightweight baseline, while keeping that middle mode explicitly secondary until the measured evidence improves.

This document exists because the current evidence suggests the full path is sometimes too expensive, while the lightweight baseline can sometimes be too loose.

## Why the hybrid mode exists

The current evidence now supports three truths at once:

- the full governed path is worth it on proof-sensitive closure work
- the lightweight baseline is often good enough on small low-risk incidents
- there is a real middle zone where some truth discipline is useful, but the full path is too expensive

The hybrid subset is for that middle zone.

But the measured evidence does **not** yet justify treating hybrid as a default middle mode.

Current status is:

- `DEMOTED`
- `DEMOTE_HYBRID_FROM_DEFAULT_POLICY`

## What the hybrid subset must preserve

The hybrid subset should preserve only the pieces most likely to improve truth without carrying the full coordination cost:

1. bounded task identity
2. one explicit artifact sanity check
3. one explicit stop/no-bluff rule when confidence is weak

These are the smallest currently credible hybrid elements.

## What the hybrid subset should not require

The hybrid subset should not require, by default:

- full attestation workflow
- full proof-bundle review
- full doctor/evaluation layering
- full exact-task closure semantics

If the scenario truly needs those, it probably belongs in the full governed path instead.

## Typical fit

The hybrid subset is most useful for:

- medium-risk incidents
- small fixes with some ambiguity
- cases where artifact truth matters, but not enough to justify the full governed path
- cases where “just eyeball it” feels too weak, but full `Synrail` feels too heavy

## Suggested hybrid flow

The current minimal hybrid flow is:

1. restate one bounded task
2. make one explicit check of the active artifact or active path
3. apply one bounded fix or bounded fallback
4. perform one explicit runtime or artifact sanity check
5. stop rather than bluff if confidence is still weak

## Expected value

Expected value of the hybrid subset:

- clearer truth than the lightweight baseline
- much lower overhead than the full governed path

## Current limitation

The hybrid subset is still less proven than the other two modes.

It is currently:

- still useful as a bounded exception pattern
- no longer strong enough to stand as a default policy tier
- not a standing third lane in the current default application policy

The current measured status artifact for this now lives at:

- `fixtures/hybrid_status_003.json`

That artifact currently says:

- do not treat hybrid as a default middle mode
- reach for baseline unless one explicit hybrid pressure-test justifies the extra control
- keep hybrid only as an explicit exception pattern

## Decision rule

Use the hybrid subset when:

- the scenario is too ambiguous for the lightweight baseline
- but not expensive enough to justify the full governed path

And only use it when you can name the specific ambiguity the lightweight baseline is failing to control.

If you cannot name that ambiguity clearly:

- stay lightweight by default

If you can name that ambiguity clearly, but the measured class still looks inconsistent:

- treat hybrid as an explicit exception, not as the default middle answer

If you keep adding steps to the hybrid subset, stop and reconsider.

You may be quietly rebuilding the full governed path.
