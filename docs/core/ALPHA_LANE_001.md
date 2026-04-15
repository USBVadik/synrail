# Alpha Lane 001

This is the first narrow alpha lane for `Synrail`.

It is intentionally one contour, not a broad product shell:

1. install one local `synrail` command
2. initialize one artifact root
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

Optional alpha feedback export can be turned on for the same artifact root:

```bash
synrail init --artifact-root "$ARTIFACT_ROOT" --telemetry-opt-in --tester-id your_name
synrail telemetry export --artifact-root "$ARTIFACT_ROOT"
```

That replay stays bounded to command sequence, error class, and next safe step.

## Verified Install Path

The currently verified alpha install path is:

```bash
python3 -m venv --system-site-packages .venv
.venv/bin/python -m pip install -e . --no-build-isolation
```

This is now the trusted local install path on the current toolchain. The older `setup.py install` route still works as a compatibility fallback, but the verified alpha lane now uses editable install.

The reference smoke for this document was run through the installed `synrail` console script, not by calling helper files directly.

`pip install . --no-build-isolation` is still not the trusted local alpha path here. The verified local route is editable install with `--system-site-packages` and `--no-build-isolation`.

## Verified Contours

Use one artifact root per run:

```bash
ARTIFACT_ROOT="$(pwd)/.synrail"
```

### Verified-working contour

This is the currently verified restore-capable alpha lane:

```bash
synrail init --artifact-root "$ARTIFACT_ROOT"
# once this root reflects one verified working state:
synrail save --artifact-root "$ARTIFACT_ROOT"
# after the agent writes final_result.json or final_result.txt:
synrail check --artifact-root "$ARTIFACT_ROOT"
# after applying only that bounded repair:
synrail retry --artifact-root "$ARTIFACT_ROOT"
synrail restore --artifact-root "$ARTIFACT_ROOT"
```

This contour assumes the artifact root already reflects one verified working state.
`save` already confirms the fallback when it can. `confirm-restore` is only an explicit re-check command, not part of the main path.

### Fresh first-run contour

On a fresh `init`, `Synrail` can still give bounded value immediately:

```bash
synrail init --artifact-root "$ARTIFACT_ROOT"
# write final_result.json or final_result.txt under the artifact root or project root
synrail check --artifact-root "$ARTIFACT_ROOT"
synrail repair-step --artifact-root "$ARTIFACT_ROOT"
```

That fresh contour does not yet guarantee `restore_available`, because no verified checkpoint exists yet.

On the current onboarding smoke in [`fixtures/alpha_onboarding_run_007/`](../../fixtures/alpha_onboarding_run_007/):

- `repair-step` before any `check` now returns one bounded human-readable next step instead of a raw missing-artifact failure
- `restore` without any checkpoint now says how to create the restore point first through `synrail save`
- `confirm-restore` without any checkpoint now returns bounded guidance instead of a traceback and points to `synrail save`

On the current shell smoke in [`fixtures/alpha_shell_run_008/`](../../fixtures/alpha_shell_run_008/):

- `init` auto-detects `project_type = python`
- `check` runs without explicit identity flags once one `final_result.txt` appears under the artifact root
- `check` now names one explicit next command: `synrail repair-step`
- `check` now also prints one bounded repair summary directly in the same shell output
- `repair-step` produces one bounded next-agent instruction without asking the operator to reconstruct packet internals by hand
- `repair-step` now says `After this repair, run: synrail retry`
- `retry` is now the preferred human-facing alias for the existing `resume` path
- `continue` remains a compatibility alias for the same path
- `save` now creates and confirms the default working restore point in one shell action
- `confirm-restore` remains available when you explicitly want to re-check a fallback, but it is not part of the default lane
- `check` now says `Workspace Not Trusted` instead of leaking `Working Surface` wording
- `prompt-followup` confirms that the generated next-agent instruction preserves the bounded current step

## What This Lane Returns

On the current verified smoke contour in [`fixtures/alpha_lane_run_003/`](../../fixtures/alpha_lane_run_003/):

- `init` returns `INITIALIZED`
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

On the current blocked-retry output smoke in [`fixtures/alpha_shell_run_008/`](../../fixtures/alpha_shell_run_008/):

- default mode now says `Repair Stopped` once the bounded retry path reaches its honest stop
- it tells the operator to restore a verified restore point or start a new run
- it no longer leaks an internal restore helper name in the user-facing shell path

Canonical artifacts:

- [shell init output](../../fixtures/alpha_shell_run_005/shell/init_stdout.txt)
- [shell check output with bounded repair summary](../../fixtures/alpha_shell_run_008/shell/check_stdout.txt)
- [self-contained restore point output](../../fixtures/alpha_safe_point_run_004/shell/save_stdout.txt)
- [shell repair-step output](../../fixtures/alpha_shell_run_008/shell/repair_step_stdout.txt)
- [shell retry output](../../fixtures/alpha_shell_run_008/shell/retry_stdout.txt)
- [shell project profile](../../fixtures/alpha_shell_run_008/lane/project_profile.json)
- [shell thin output](../../fixtures/alpha_shell_run_008/lane/thin_output.json)
- [shell prompt](../../fixtures/alpha_shell_run_008/lane/prompt.json)
- [shell prompt followup](../../fixtures/alpha_shell_run_008/lane/followup.json)
- [onboarding repair-step-before-check output](../../fixtures/alpha_onboarding_run_007/shell/repair_step_before_check_stdout.txt)
- [onboarding restore-without-checkpoint output](../../fixtures/alpha_onboarding_run_007/shell/restore_without_checkpoint_stdout.txt)
- [onboarding confirm-restore-without-checkpoint output](../../fixtures/alpha_onboarding_run_008/shell/confirm_restore_without_checkpoint_stdout.txt)
- [restore point save output](../../fixtures/alpha_safe_point_run_004/shell/save_stdout.txt)
- [confirm-restore output](../../fixtures/alpha_restore_point_confirm_run_001/shell/confirm_restore_stdout.txt)
- [blocked retry thin output](../../fixtures/alpha_shell_run_008/lane/thin_output.json)
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
