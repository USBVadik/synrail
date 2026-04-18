# Product Memo 001

## One-line thesis

`Synrail` is a control kernel that forces agent execution to earn acceptance instead of narrating success.

## Problem

In agentic workflows, the weak default is:

- the agent says it finished
- the operator sees a plausible narrative
- the system treats this as good enough
- real truth is delayed or lost

This creates several repeated failures:

- false success
- unclear next step after a non-green outcome
- expensive restore after drift
- hidden reliance on author memory
- weak handoff to a second operator

## Core idea

`Synrail` separates:

- execution
- proof
- acceptance

An agent may complete execution.

That does not mean the run is accepted.

Acceptance has to be earned through explicit runtime artifacts and gates.

## Product principles

1. claimed done is not accepted done
2. non-green is a real product state, not an embarrassment to hide
3. verified working state is worth preserving explicitly
4. continuation should be bounded and reviewable
5. truth should beat narrative convenience

## What the product does today

At the current alpha level, `Synrail` provides one narrow workflow:

1. start one controlled run with `synrail start`
2. auto-detect a minimal project profile
3. run doctor and execution checks
4. evaluate the resulting proof bundle
5. produce a closure reading
6. if non-green, produce one bounded repair instruction
7. if a trusted fallback exists, restore it explicitly
8. if the run fails in an interesting way, export one compact telemetry and bug packet

## Core user value

The narrow value proposition is not “general AI orchestration.”

The wedge is smaller and stronger:

- when an agent misses, `Synrail` does not let false success pass silently
- when a run is blocked, `Synrail` gives one bounded next repair step
- when a trusted working state exists, `Synrail` can restore it faster than manual archaeology
- when another operator takes over, continuation is less dependent on author memory

## What Synrail is not

It is not currently:

- a broad no-code automation platform
- a hosted observability product
- a general workflow engine
- a broad semantic layer for every agent stack
- a final novice-facing polished product shell

## Current product form

The current product form is:

- one proof-governed kernel
- one thin controlled-start alpha shell on top of that kernel
- one current tester pack for external critique and early alpha pressure

## Why this matters

The product exists for environments where “looks plausible” is too weak, but heavyweight process bureaucracy is also too expensive.

`Synrail` is trying to sit in the narrow but valuable middle:

- strong enough to block dishonest closure
- narrow enough to stay usable in the first real workflow

## Current alpha lane in plain language

Current support boundary:

- supported: one local trusted worktree on the same machine where the agent acts
- not yet supported: remote host / ops / production-target execution as a first-class alpha lane

Current first-run alpha lane:

1. `synrail start`
2. do the bounded change and update only the proof surfaces that reflect what was actually changed and verified
3. `synrail check`
4. if non-green: fix only the named blocker
5. `synrail check`
6. if a trusted fallback exists: `synrail restore`
7. if needed: `synrail telemetry export` or `synrail bug-packet`

Current restore-capable lane:

1. `synrail start`
2. `synrail save`
3. run the bounded change
4. `synrail check`
5. if repairable: fix only what `synrail check` named, then run `synrail check` again
6. if safer to return: `synrail restore --preview`
7. if still appropriate: `synrail restore`

## Product maturity today

What is already real:

- proof/closure separation
- default mode output layer
- bounded next-agent prompt generation
- explicit acceptance criteria
- measured doctor coverage gate
- executable continuation arbiter
- regression suite on truth-critical failures
- telemetry and bug-packet export

What is still intentionally narrow:

- one alpha contour, not ten
- one thin shell, not a platform shell
- local install path only
- local artifacts only
- no claim of broad domain completeness

## Honest risk summary

The current biggest risks are no longer “missing product ideas.”

They are about whether the current truth surfaces are strict enough under external pressure.

That is exactly why this pack exists.
