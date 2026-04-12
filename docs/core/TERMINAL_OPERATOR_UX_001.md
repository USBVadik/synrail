# Terminal Operator UX 001

## Purpose

Define the first terminal-first operator surface for `Synrail`.

This document exists so the executable kernel slices can be used through one small operator-facing command entry instead of only as disconnected scripts.

## Artifact

The first terminal UX slice now lives at:

- `tools/reference/synrail_cli_v0.py`

## What it does

The CLI v0 currently exposes:

1. `init`
   - initialize one machine-readable run state
2. `status`
   - show the compact current run state
3. `bundle-check`
   - assemble and classify a proof bundle
4. `apply-bundle`
   - apply a proof-bundle artifact back into the state machine
5. `closure`
   - compute the closure verdict
6. `apply-closure`
   - apply a closure verdict back into the state machine
7. `refresh`
   - refresh state after a doctor, bundle, closure, or recovery event
8. `validate`
   - validate one machine-readable artifact against one schema
9. `doctor`
   - emit one machine-readable doctor record and optionally write it back into the run state
10. `orchestrate`
   - run one bounded `doctor -> optional preparation -> bundle -> closure` contour, optionally apply `refresh` and `compare`, and emit one machine-readable orchestration report plus an optional worked run envelope
11. `compare`
   - emit one machine-readable baseline comparison record through the CLI layer
   - route to the legacy comparison harness for `v0` inputs and the economics harness for `v1` inputs
12. `hybrid-status`
   - emit one machine-readable hybrid-mode status artifact from the current economics and hybrid evidence set
13. `recommend-mode`
   - emit one machine-readable cost-aware mode recommendation before the operator enters a heavier contour
14. `select-mode`
   - emit one machine-readable receipt that records whether the operator followed the recommendation and whether a heavier contour was skipped
15. `plan-proof`
   - emit one governed-path proof preparation plan before bundle assembly starts
16. `preparation-receipt`
   - emit one machine-readable receipt showing whether the planned proof surface reached a complete first bundle pass

## Why this matters

Without a small operator-facing entrypoint, the kernel still feels more like a collection of internal prototypes than a usable tool.

The terminal UX is the first move toward:

- one practical entry layer
- lower operator friction
- clearer current-state reading

The bounded orchestration command is the first move from:

- many cooperating commands

to:

- one smaller runtime contour

That contour can now also carry one optional governed-path preparation step instead of leaving preparation entirely outside the runtime path.

## v0 limitations

The CLI currently does not provide:

- rich status rendering
- interactive flows
- multi-run coordination

It now provides one bounded orchestration path, but not a broad runtime shell.

It is a small facade, not the final UX.

## Decision rule

Future terminal UX work should improve:

- clarity of current state
- visibility of blocking reasons
- speed of next-safe-step execution

without turning the CLI into a broad orchestration shell too early.
