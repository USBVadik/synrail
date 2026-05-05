# Contributing to Synrail

Thanks for helping shape `Synrail`.

This repository is still in an early extracted form, so the contribution bar is intentionally narrow:

- preserve the proof-first identity
- keep the boundary between kernel and downstream systems clean
- prefer small, reviewable changes over broad restructuring

## What belongs here

Good early contributions usually improve one of these areas:

- kernel contracts
- truth surfaces
- boundary clarity
- narrow reference helpers
- extracted-repo readability and repo hygiene

## What does not belong here

Please do not mix these into routine repo changes:

- downstream bot implementation logic
- downstream capability-layer work
- proving-ground incident dumps
- raw runtime artifacts
- one-off host archaeology
- broad productization work that hides the kernel cut

## Change shape

Prefer changes that are:

- narrow
- explicit
- reversible
- easy to review by artifact truth

Avoid changes that:

- widen scope silently
- rename large portions of the repo for aesthetics only
- blur the line between the kernel and one proving-ground environment

## Docs-first rule

If a change affects:

- acceptance semantics
- truth surfaces
- recovery behavior
- transition rules
- extraction boundary

then update the relevant docs in the same change.

## Helper script rule

When changing scripts under `tools/reference/`:

- keep defaults generic where possible
- prefer environment or argument driven behavior over hardcoded battlefield assumptions
- keep them as reference helpers, not an orchestration platform

## Pull request guidance

A good PR in this repo should say:

- what small slice changed
- why it belongs to Synrail itself
- what was intentionally left out

If a change mainly benefits one downstream agent or one proving-ground environment, call that out explicitly and reconsider whether it belongs in this repo at all.

## Issue guidance

Use the GitHub issue templates to keep bug reports and feature requests bounded.

- bug reports should name the observed status or misleading outcome and point to the smallest repro or artifact path
- feature requests should explain why the change belongs in Synrail itself and what should stay out of scope
- broad remote-host, downstream-agent, or production workflow asks should be labeled explicitly as outside the current support boundary unless the request is about tightening that boundary honestly

If the normal feedback export is not enough for a bug report, attach `synrail bug-packet --artifact-root .synrail`.
