# Private-Stable Target

## Purpose

Define the first credible `private-stable` target for the extracted `Synrail` repository.

This document exists to give the current hardening phase a finish line without pretending the project is already public-release mature.

## Meaning of private-stable

`Private-stable` does **not** mean:

- public-ready
- feature-complete
- polished for broad external adoption

It means:

- the extracted repo has a stable enough identity
- the boundary is clear enough to resist routine scope drift
- the repo is readable enough to support disciplined private review
- the remaining gaps are known, bounded, and do not invalidate the extraction itself

## Target criteria

The first private-stable target is reached when all of the following are true:

### 1. Repo identity is clear

Evidence should include:

- a top-level README that explains the wedge and scope
- a docs map
- a roadmap
- contributing guidance

### 2. Boundary is explicit and internally consistent

Evidence should include:

- product boundary docs
- extraction/boundary docs that no longer contradict the fact that extraction already happened
- clear separation between kernel, adapters, proving ground, and downstream capability layers

### 3. Helper framing is strong enough for private review

Evidence should include:

- helper README
- helper usage matrix
- explicit statements of what helpers do not prove

### 4. At least one closure-grade exact-task proof exists

Evidence should include:

- one accepted proof-complete exact-task success under kernel rules

This is the minimum proof floor for taking the extracted repo seriously.

### 5. A bounded hardening backlog exists

Evidence should include:

- a first product-review pass
- a post-critique hardening note
- a small next-step set rather than open-ended “keep improving”

## What is still allowed to remain unfinished

The repo may still be private-stable even if:

- examples and fixtures are still sparse
- repeatability is not yet as strong as structure
- licensing is still undecided
- public-release positioning is still intentionally deferred

These are important, but they do not block the first private-stable state.

## Current reading

Current reading:

- `Synrail` has now reached the first private-stable target

What now appears satisfied:

- repo identity
- explicit boundary
- helper framing
- closure-grade proof floor
- bounded hardening backlog
- initial repeatability signal

What still deserves strengthening even after private-stable is reached:

- repeatability confidence
- curated examples or fixtures
- later release hygiene

## Decision rule

Treat `private-stable` as reached when the repo can be reviewed privately as a coherent product surface without needing constant outside explanation to defend:

- what it is
- what it is not
- why it was extracted
- what still remains unfinished
