# Protected Admission Shadow

Protected admission is Synrail's experimental GitHub-facing lane. It applies the
same false-green principle at a different boundary:

> The actor authoring a change should not also control the policy and evidence
> used to admit it.

The first release is deliberately observation-only. It does not accept, reject,
or merge a pull request, and it does not replace CI or code review.

## What It Observes

Given exact base and head commit object IDs, Synrail computes the merge base and
classifies paths introduced by the pull request. The built-in
`authority_paths_v0` policy currently observes changes to:

- tests and common test-runner configuration
- GitHub workflows, local actions, and common CI configuration
- Synrail, CODEOWNERS, Rego, Sentinel, and conventional policy paths
- conventional IAM, RBAC, permission, and authorization paths
- conventional deployment, Kubernetes, Helm, Terraform, and infrastructure paths

This is a path-rules classifier, not a semantic security scanner. A generic
source file can still change authorization or deployment behavior without
matching a conventional path.

## Run It

Both commit objects must exist in one non-bare Git checkout, and
`--project-root` must identify that checkout's top-level directory.

```bash
synrail protected-admission \
  --project-root . \
  --base-sha "$BASE_SHA" \
  --head-sha "$HEAD_SHA"
```

For machine-readable output:

```bash
synrail protected-admission \
  --project-root . \
  --base-sha "$BASE_SHA" \
  --head-sha "$HEAD_SHA" \
  --json
```

Synrail accepts only full lowercase SHA-1 or SHA-256 object IDs. It resolves both
as commits, computes their merge base, and evaluates
`merge-base -> head` with rename detection disabled. A rename is therefore
observed deterministically as a deletion plus an addition, so moving into or out
of an authority path checks both names.

## Result Contract

A complete result uses
[`protected_admission_shadow_v0.schema.json`](../../schemas/protected_admission_shadow_v0.schema.json)
and includes:

- exact `base_sha`, `head_sha`, and computed `merge_base_sha`
- `policy_revision: authority_paths_v0`
- `classifier_scope: PATH_RULES_ONLY`
- stable category and reason codes
- matched paths and change types
- a canonical SHA-256 evaluation fingerprint
- `mode: SHADOW` and `merge_blocking: false`

An observed authority change is not a process failure. Both
`AUTHORITY_CHANGE_OBSERVED` and `NO_AUTHORITY_CHANGE_OBSERVED` exit with code 0.
An invalid input, unavailable commit, unsafe Git condition, malformed diff, or
resource limit returns `NOT_EVALUATED`, `would_block: true`, and exit code 2.
The bundled workflow absorbs that exit code because this phase is explicitly
non-blocking.

`would_block` is a counterfactual observation for pilot measurement. It is not a
merge decision.

## GitHub Dogfood Workflow

[`.github/workflows/protected-admission-shadow.yml`](../../.github/workflows/protected-admission-shadow.yml)
runs on pull requests with read-only repository permissions. It checks out:

1. the pull-request graph as untrusted Git data; and
2. evaluator code from the exact base commit.

The evaluator reads the head tree through hardened Git commands; it does not
import or execute code from the pull-request head. The check is named
`[shadow] Protected admission`, always remains non-blocking, and publishes no
comments, artifacts, or external telemetry.

The in-repository workflow is dogfood, not a hostile security boundary by
itself: a pull request can propose changing the workflow that future runs use.
For an actual protected boundary, source the workflow and policy from a separate
trusted repository through an organization ruleset, or run a separately
controlled GitHub App. Pin the evaluator revision and keep it outside the worker
agent's write authority.

Do not use `pull_request_target` with a checkout of untrusted head code.

## Pilot Evidence

Shadow mode exists to measure the product hypothesis before imposing merge
friction. Record denominators, not only interesting examples:

- total evaluated pull requests and changed paths
- matched pull requests by category
- natural actionable catches, excluding seeded demos
- catches incremental to existing required checks and review
- evaluator errors, potential false blocks, and override reasons
- setup time and time added to pull-request feedback
- teams returning weekly and teams willing to enter a paid pilot

Blocking mode is intentionally absent from this contract. It should be designed
only after external pilots show incremental catches, acceptable setup cost, and
a low adjudicated false-block rate.
