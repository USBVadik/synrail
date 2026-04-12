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
   - run one bounded `doctor -> bundle -> closure` contour and emit one machine-readable orchestration report

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
