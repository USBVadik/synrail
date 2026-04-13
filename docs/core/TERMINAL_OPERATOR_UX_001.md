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
   - can now absorb one `mode-selection receipt` so a prepared strong-path selection can enter the runtime contour directly
11. `resume`
   - run the same bounded runtime contour from an existing non-green state and record the starting state as runtime continuation truth
   - can now consume one repair handoff artifact and block at `repair_handoff` when the continuation contract is still incomplete
   - now auto-discovers one sibling `repair_packet.json` by default, so packet-first continuation becomes the normal operator path instead of an optional extra
   - can now consume one richer repair packet so the operator no longer has to replay the full runtime surface as raw flags on every continuation
   - now trusts embedded packet truth strongly enough that selection receipts, previous repair receipts, and repair handoffs no longer need to be unpacked into temporary side files in the normal continuation path
   - now also uses stage-aware sibling discovery, so `stage2_state.json` can naturally pair with `stage2_repair_packet.json`, `stage2_target_identity.txt`, and `stage2_resume_inputs.json`
   - now proven on:
     - `DOCTOR_BLOCKED`
     - `PROOF_BUNDLE_PARTIAL`
     - `PROOF_BUNDLE_INVALID`
     - `RECOVERY_PENDING`
12. `repair-handoff`
   - emit one machine-readable continuation contract naming the missing inputs and bounded runtime defaults for a non-green state
13. `repair-packet`
   - emit one richer machine-readable continuation packet carrying the handoff, resumability truth, continuation plan, repair inputs, and output defaults for a non-green state
14. `compare`
   - emit one machine-readable baseline comparison record through the CLI layer
   - route to the legacy comparison harness for `v0` inputs and the economics harness for `v1` inputs
15. `hybrid-status`
   - emit one machine-readable hybrid-mode status artifact from the current economics and hybrid evidence set
16. `recommend-mode`
   - emit one machine-readable cost-aware mode recommendation before the operator enters a heavier contour
17. `select-mode`
   - emit one machine-readable receipt that records whether the operator followed the recommendation and whether a heavier contour was skipped
18. `plan-proof`
   - emit one governed-path proof preparation plan before bundle assembly starts
19. `preparation-receipt`
   - emit one machine-readable receipt showing whether the planned proof surface reached a complete first bundle pass
20. `governed-cost`
   - emit one machine-readable cost delta between an unprepared and prepared governed path
21. `reproducibility`
   - compare two canonical run artifacts for one bounded reproducibility reading on key runtime truth
22. `second-operator`
   - inspect whether one packet-first continuation path is followable without hidden author memory
23. `operator-brief`
   - compress current runtime truth into one operator-facing brief naming the blocker, current repair step, required inputs, stale sub-surfaces, and primary next action
24. `operator-brief-chain`
   - compress multiple operator briefs into one stage-by-stage operator reading for an ugly continuation contour

The selection layer can now also carry one preparation-aware strong-path recommendation when bounded governed-path cost evidence exists.

The orchestration layer can now also absorb that preparation-aware strong-path receipt directly, instead of forcing the operator to restate preparation outputs manually.

The terminal layer now also exposes one named `resume` path plus one explicit `repair-handoff` path, so continuation from a doctor-blocked, partial, or degraded state no longer has to feel like a disguised replay of the base orchestration command.

It now also exposes one `repair-packet` path, so the operator can group:

- the continuation contract
- the resumability family
- the continuation plan
- the repair inputs
- the runtime output defaults

before handing the run back into `resume`.

That packet path is now more useful for:

- inspection
- explicit override
- artifact export
- checking whether the current contour is still repairable or now terminal

than for everyday authoring, because the runtime can now synthesize most continuation packets directly from current truth.

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

Its continuation surface is now stricter too:

- packet-first `resume` can auto-discover a sibling repair packet
- packet-first `resume` can now also auto-discover sibling prompt, task, proof, and final-result artifacts
- packet-first `resume` can now also auto-discover stage-aware sibling outputs and one narrow `resume_inputs.json` override file
- packet-first `resume` now also keeps more continuation truth inside the packet itself, so fewer continuation steps depend on extra sidecar coordination
- that packet can now carry current-step repair order plus artifact-quality hints
- that packet plus repair receipt can now tell the operator which exact stale sub-surfaces are still next in line
- the runtime now blocks explicitly when the operator tries to jump ahead of the current repair step
- and it can now say that a contour is not resumable at all and should follow either the lighter selected mode or a fresh new run instead

It is a small facade, not the final UX.

The first broader operator-layer move now also exists:

- `operator-brief` does not replace the runtime packet or report
- it compresses them into one smaller actionable surface when the operator needs a quick truthful handoff
- `operator-brief-chain` extends that same idea across multiple continuation stages when one snapshot is no longer enough to read the contour cleanly
- it is now proven on both honest endings:
  - follow the terminal boundary
  - stop replaying this contour and start a new run

## Decision rule

Future terminal UX work should improve:

- clarity of current state
- visibility of blocking reasons
- speed of next-safe-step execution

without turning the CLI into a broad orchestration shell too early.

- packet-first `resume` now leaves fewer default root-level side files behind when the packet already carries enough continuation truth
- packet-first `resume` now also trusts one compact embedded continuation core inside the packet, so the normal continuation path can start from `state + repair_packet` instead of reopening more side artifacts by default
- `repair-packet` can now also inherit context from one previous packet, so multi-step continuation no longer has to replay full doctor or execution context at every repair step
