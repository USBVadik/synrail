# TARGET_SURFACE_ATTESTATION

## Purpose

Prevent agents from claiming they inspected, patched, tested, or deployed on the intended target surface when that surface has not been proven.

This slice exists because the latest Gemini incident showed a basic control failure:

- the agent operated on the Hetzner copy
- the agent claimed Node 2 / Google VM verification
- the claim was stronger than the available environment proof

That is not a semantic problem.

It is an execution-truth problem.

## Core rule

No agent may claim any of the following without prior target-surface attestation:

- `I checked the bot on Node 2`
- `I tested the fix on Google VM`
- `I changed the active runtime repo`
- `I deployed the patch to the live target`

If attestation is missing, the correct behavior is:

- stop
- downgrade the claim
- state that the active execution surface is not yet proven

## Minimum attestation proof

For the Node 2 bot path, attestation must prove:

- the current controller surface
- the target host identity
- the target repo path
- the target repo identity on that host

Helpful but secondary signals:

- target repo branch
- target repo dirtiness
- target runtime process presence

## What attestation is not

The following are not enough by themselves:

- a remembered host name
- a context note
- a deploy intention
- the presence of an SSH key
- a local repo copy that resembles the target repo

Host assumption is not execution truth.

Repo resemblance is not target proof.

Deployment intent is not runtime verification.

## Minimal practical helper

The current minimal helper is:

- `tools/reference/attest_target_surface.sh`
- `tools/reference/require_attested_target_surface.sh`

It attests:

- controller host identity on Hetzner
- nested reachability to Node 2
- target repo presence on Node 2
- target repo branch and head on Node 2
- whether runtime-like bot processes are observed on Node 2

## Mandatory pre-step

Before any bugfix, test, or deploy run that claims Node 2 truth, run:

- `tools/reference/require_attested_target_surface.sh`

If that command does not end in:

- `attested_target_surface=PASS`

the run must not be treated as a valid Node 2 bugfix/test/deploy action.

In the standard incident workflow, this step now comes immediately after any bounded incident-hypothesis intake and before any bounded probe, patch review, bugfix run, or deploy claim.

## Acceptance rule

A Node 2 diagnosis/fix/test/deploy claim may be treated as reviewable only if:

- `attestation_result=PASS`

If attestation returns `FAIL`, the claim must not be accepted as target-surface truth.

This does not remove the separate production-confirmation rule.

Even after `attestation_result=PASS`, a production fix still requires one post-deploy external runtime confirmation before it can be accepted as repaired behavior.

## Why this stays in minimal kernel scope

This is not broad ontology growth.

This is a narrow closure-economics control because it prevents:

- wrong-surface edits
- fake runtime verification
- false deploy confidence
- noisy retries caused by environment confusion

That makes it part of the active minimal kernel rather than a future nice-to-have.
