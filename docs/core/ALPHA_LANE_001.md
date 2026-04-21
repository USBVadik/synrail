# Alpha Lane 001

This is the first narrow alpha lane for `Synrail`.

Current support boundary:

- supported: one local trusted worktree on the same machine where the agent acts
- not yet supported: remote host / ops / production-target execution as a first-class alpha lane
- supported integration pattern: external deploy or restart scripts may enforce `synrail deploy` plus guard-first side effects after a local accepted run

It is intentionally one contour, not a broad product shell:

1. install one local `synrail` command
2. start one controlled run at one artifact root
3. let `Synrail` auto-detect one sane project profile
4. optionally save one verified fallback when a working state already matters
5. run one bounded change/check contour
6. generate one bounded follow-up prompt
7. restore the verified working state if the contour is blocked

The lane exists to prove one user value clearly:

- an agent can hit a non-green outcome
- `Synrail` does not accept false success
- the operator gets one bounded next step
- one verified working state can be restored without replaying the whole run by hand

Optional alpha feedback export can be turned on for the same controlled run:

```bash
TASK_REQUEST="Reject a plain-text final result and keep the repair bounded."
synrail start --artifact-root "$ARTIFACT_ROOT" --project-root "$(pwd)" --task-identity "$TASK_REQUEST" --telemetry-opt-in --tester-id your_name
synrail telemetry export --artifact-root "$ARTIFACT_ROOT"
```

That replay stays bounded to command sequence, error class, and next safe step.

If you need a bounded deploy or restart integration after local acceptance, use the pattern in [DEPLOY_GUARD_INTEGRATION_001.md](./DEPLOY_GUARD_INTEGRATION_001.md).

## Verified Install Path

The currently verified alpha install path is:

```bash
python3 tools/reference/synrail_install_v0.py --venv .venv
```

This is now the trusted tester path on the current toolchain. It links the repo into a local venv without depending on setuptools or network access.

The reference smoke for this document was run through the installed `synrail` console script, not by calling helper files directly.

## Verified Contours

Use one artifact root per controlled run:

```bash
ARTIFACT_ROOT="$(pwd)/.synrail"
```

### Verified-working contour

This is the currently verified restore-capable alpha lane:

```bash
synrail start --artifact-root "$ARTIFACT_ROOT" --project-root "$(pwd)" --task-identity "Preserve one verified fallback before a bounded change."
# once this root reflects one verified working state:
synrail save --artifact-root "$ARTIFACT_ROOT"
# synrail start already creates starter proof files under $ARTIFACT_ROOT; edit them in place, then:
synrail check --artifact-root "$ARTIFACT_ROOT"
# after applying only that bounded repair:
synrail retry --artifact-root "$ARTIFACT_ROOT"
synrail restore --artifact-root "$ARTIFACT_ROOT"
```

This contour assumes the artifact root already reflects one verified working state.
`save` already confirms the fallback when it can. `confirm-restore` is only an explicit re-check command, not part of the main path.

### Fresh first-run contour

On a fresh controlled start, `Synrail` can still give bounded value immediately:

```bash
synrail start --artifact-root "$ARTIFACT_ROOT" --project-root "$(pwd)" --task-identity "Reject a plain-text final result and keep the repair bounded."
# synrail start already creates .synrail/final_result.json on the default path; strengthen it first, then:
synrail check --artifact-root "$ARTIFACT_ROOT"
# optional standalone bounded prompt after a non-green check:
synrail repair-step --artifact-root "$ARTIFACT_ROOT"
```

That fresh contour does not yet guarantee `restore_available`, because no verified checkpoint exists yet.

On the current onboarding smoke in [`fixtures/alpha_onboarding_run_007/`](../../fixtures/alpha_onboarding_run_007/):

- `repair-step` before any `check` now returns one bounded human-readable next step instead of a raw missing-artifact failure
- `restore` without any checkpoint now says how to create the restore point first through `synrail save`
- `confirm-restore` without any checkpoint now returns bounded guidance instead of a traceback and points to `synrail save`

On the current canonical first-run pack contour in [`fixtures/alpha_test_pack_run_004/`](../../fixtures/alpha_test_pack_run_004/):

- `start` opens with one explicit `Do this now` instruction on the starter proof files
- `check` blocks the plain-text false-success contour as `PROOF_INVALID`
- `check` now leads with one explicit bounded action and repair target instead of only a diagnosis
- the default non-green path now stays on `synrail check` for the first bounded fix
- `repair-step`, when requested, produces one bounded next-agent instruction without asking the operator to reconstruct packet internals by hand
- `operator render` keeps that same `Do this now` instruction readable for a second operator
- `telemetry export` now rides the same contour without leaking tmp or author-local paths

## What This Lane Returns

On the current verified restore-capable smoke contour in [`fixtures/alpha_lane_run_003/`](../../fixtures/alpha_lane_run_003/):

- `start` returns `INITIALIZED` with controlled bootstrap provenance
- `save` returns `OK`
- `check` blocks on `EXACT_TASK_IDENTITY_NOT_CONFIRMED`
- thin output translates that into:
  - `NON_RESUMABLE`
  - verified checkpoint available
  - run the next bounded attempt only after restoring the original task request
- `repair-step` keeps the next agent step bounded to:
  - prepare the next bounded attempt
  - restore the original task request and intended task target
- `restore` returns `OK`

On the current fresh external contour in [ALPHA_EXTERNAL_RUN_001.md](./ALPHA_EXTERNAL_RUN_001.md):

- `check` returns `PROOF_INVALID`
- `repair-step` stays bounded to `repair_final_result_artifact`
- `restore_available = false`, which is the correct reading for a fresh contour without one verified checkpoint

On the current accepted default output smoke in [`fixtures/thin_output_run_accepted_003/`](../../fixtures/thin_output_run_accepted_003/):

- default mode says `ACCEPTED`
- it explains that the run reached accepted closure
- it makes clear that no repair step is required

On the secondary blocked-retry output smoke in [`fixtures/alpha_shell_run_008/`](../../fixtures/alpha_shell_run_008/):

- default mode now says `Repair Stopped` once the bounded retry path reaches its honest stop
- it tells the operator to restore a verified restore point or start a new run
- it no longer leaks an internal restore helper name in the user-facing shell path

Canonical artifacts:

- [shell start output](../../fixtures/alpha_test_pack_run_004/shell/start_stdout.txt)
- [shell check output with bounded repair summary](../../fixtures/alpha_test_pack_run_004/shell/check_stdout.txt)
- [self-contained restore point output](../../fixtures/alpha_safe_point_run_004/shell/save_stdout.txt)
- [shell repair-step output](../../fixtures/alpha_test_pack_run_004/shell/repair_step_stdout.txt)
- [secondary blocked-retry output](../../fixtures/alpha_shell_run_008/shell/retry_stdout.txt)
- [shell thin output](../../fixtures/alpha_test_pack_run_004/lane/thin_output.json)
- [shell prompt](../../fixtures/alpha_test_pack_run_004/lane/prompt.json)
- [shell operator render](../../fixtures/alpha_test_pack_run_004/lane/operator_render.md)
- [shell second operator](../../fixtures/alpha_test_pack_run_004/lane/second_operator.json)
- [shell operator reading](../../fixtures/alpha_test_pack_run_004/lane/operator_reading.json)
- [onboarding repair-step-before-check output](../../fixtures/alpha_onboarding_run_007/shell/repair_step_before_check_stdout.txt)
- [onboarding restore-without-checkpoint output](../../fixtures/alpha_onboarding_run_007/shell/restore_without_checkpoint_stdout.txt)
- [onboarding confirm-restore-without-checkpoint output](../../fixtures/alpha_onboarding_run_008/shell/confirm_restore_without_checkpoint_stdout.txt)
- [restore point save output](../../fixtures/alpha_safe_point_run_004/shell/save_stdout.txt)
- [confirm-restore output](../../fixtures/alpha_restore_point_confirm_run_001/shell/confirm_restore_stdout.txt)
- [secondary blocked-retry thin output](../../fixtures/alpha_shell_run_008/lane/thin_output.json)
- [init state](../../fixtures/alpha_lane_run_003/init/state.json)
- [working checkpoint verify](../../fixtures/alpha_lane_run_003/lane/checkpoints/working/checkpoint_verify.json)
- [thin output](../../fixtures/alpha_lane_run_003/lane/thin_output.json)
- [prompt](../../fixtures/alpha_lane_run_003/lane/prompt.json)
- [restore result](../../fixtures/alpha_lane_run_003/lane/checkpoint_restore.json)
- [accepted thin output](../../fixtures/thin_output_run_accepted_003/thin_output.json)

## Alpha Rules

This lane is intentionally thin:

- no new continuation families
- no richer operator evidence layer
- no hybrid branch expansion
- no broad packaging shell

If the second operator gets stuck here, the next fix should simplify:

- command defaults
- output wording
- restore/resume guidance
- artifact discovery

not add new vocabulary.
