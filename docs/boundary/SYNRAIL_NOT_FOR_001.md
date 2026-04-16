# Synrail Not For 001

## Purpose

State where the current evidence suggests `Synrail` should not be treated as the default full-path process.

This document exists so boundary discipline applies not only to code ownership, but also to when the kernel is worth using at all.

## Not for by default

`Synrail` should not currently be treated as the default full governed path for:

- small honesty-restoration incidents where a truthful fallback is cheap
- simple bounded fixes with low false-success risk
- scenarios where a disciplined lightweight operator loop already gives adequate truth at much lower cost
- downstream capability policy tuning
- broad process wrapping “just in case”

## Why

The current evidence shows:

- `Synrail` is strongest where proof sensitivity is high
- `Synrail` is weaker, relative to cost, where the scenario is small and the baseline is already likely adequate

That means misuse of `Synrail` is not just a stylistic problem.

It is an economics problem.

## Signs the full path may be overkill

These are current signs that the full governed path may be too expensive:

- the repair is small and local
- the runtime surface is not meaningfully ambiguous
- the artifact truth is easy to inspect directly
- the operator can cheaply validate the outcome
- false completion would be annoying but not expensive

## Better default in those cases

The better default in those cases is:

- a disciplined lightweight operator loop

Potentially with only a subset of `Synrail` ideas, such as:

- clearer task identity
- simple artifact sanity check
- explicit stop if confidence is weak

But not necessarily the full governed path.

## Decision rule

Do not apply `Synrail` everywhere to make the product feel bigger.

Apply it where the extra truth discipline is worth the extra coordination cost.
