# Synrail Roadmap

This roadmap is intentionally short-horizon.

`Synrail` has only recently been extracted into its own repository, so the next moves should strengthen identity and usability before expanding scope.

## Current phase

Current phase:

- establish the extracted repo as a clean, reviewable control-kernel surface

That means the near-term work is mostly about:

- repo-native clarity
- boundary integrity
- helper sanity
- small, disciplined follow-up improvements

## Near-term priorities

### 1. Tighten repo-native documentation

Goal:

- make the extracted repo readable without relying on external proving-ground memory

Examples:

- improve document cross-links
- smooth wording that still sounds like upstream battlefield residue
- add small orientation surfaces only where they reduce confusion

### 2. Keep the boundary clean

Goal:

- prevent downstream capability work from slipping into the kernel repo

Examples:

- reject changes that mainly belong to one downstream bot
- reject changes that mainly describe one proving-ground environment
- keep adapter references generic where possible

### 3. Stabilize reference helpers

Goal:

- keep `tools/reference/` useful as narrow examples rather than turning them into a sprawling framework

Examples:

- prefer generic defaults
- document required env inputs clearly
- keep helper behavior legible and bounded

### 4. Prepare merge-to-main quality

Goal:

- make the first extraction PR easy to review and safe to merge

Examples:

- resolve small wording inconsistencies
- keep commit history intentional
- avoid broad cleanup that changes repo identity mid-review

### 5. Strengthen post-extraction proof and examples

Goal:

- reduce the gap between strong structure and still-limited proving evidence

Examples:

- improve repeatability confidence for closure-grade exact-task runs
- add one or two sanitized examples or fixtures
- define a minimal private-stable target for the repo

## Explicitly not current priorities

These may matter later, but they are not the current focus:

- building a full UI or dashboard
- adding downstream agent capability logic
- importing historical incident archives
- broad packaging or automation layers
- turning reference helpers into a large orchestration product

## Decision rule

If a proposed change makes the repo:

- clearer
- narrower
- easier to review
- more faithful to the kernel boundary

it is likely on-roadmap.

If it mostly adds breadth, downstream behavior, or battlefield history, it is probably off-roadmap for this phase.

## Review anchor

The current product-review anchor for this phase is:

- `docs/boundary/FIRST_PRODUCT_REVIEW_PASS.md`
