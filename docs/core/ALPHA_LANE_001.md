# Alpha Lane 001

This is the first narrow alpha lane for `Synrail`.

It is intentionally one contour, not a broad product shell:

1. install one local `synrail` command
2. initialize one artifact root
3. let `Synrail` auto-detect one sane project profile
4. create and verify one working checkpoint when a verified working state exists
5. run one bounded change/check contour
6. generate one bounded follow-up prompt
7. restore the verified working state if the contour is blocked

The lane exists to prove one user value clearly:

- an agent can hit a non-green outcome
- `Synrail` does not accept false success
- the operator gets one bounded next step
- one verified working state can be restored without replaying the whole run by hand

Optional alpha telemetry can now be turned on for the same artifact root:

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
synrail continue --artifact-root "$ARTIFACT_ROOT"
synrail restore --artifact-root "$ARTIFACT_ROOT"
```

This contour assumes the artifact root already reflects one verified working state.

### Fresh first-run contour

On a fresh `init`, `Synrail` can still give bounded value immediately:

```bash
synrail init --artifact-root "$ARTIFACT_ROOT"
# write final_result.json or final_result.txt under the artifact root or project root
synrail check --artifact-root "$ARTIFACT_ROOT"
synrail next-step --artifact-root "$ARTIFACT_ROOT"
```

That fresh contour does not yet guarantee `restore_available`, because no verified checkpoint exists yet.

On the current onboarding smoke in [alpha_onboarding_run_005](/Users/usbdick/Documents/New%20project/synrail/fixtures/alpha_onboarding_run_005):

- `next-step` before any `check` now returns one bounded human-readable next step instead of a raw missing-artifact failure
- `restore` without any checkpoint now says how to create the safe point first through `synrail save`
- `checkpoint verify` without any checkpoint now returns bounded guidance instead of a traceback and points to `synrail save`

On the current shell smoke in [alpha_shell_run_006](/Users/usbdick/Documents/New%20project/synrail/fixtures/alpha_shell_run_006):

- `init` auto-detects `project_type = python`
- `check` runs without explicit identity flags once one `final_result.txt` appears under the artifact root
- `check` now names one explicit next command: `synrail next-step`
- `check` now also prints one bounded repair summary directly in the same shell output
- `next-step` produces one bounded next-agent instruction without asking the operator to reconstruct packet internals by hand
- `next-step` now says `After this repair, run: synrail continue`
- `continue` is now a thin human-facing alias for the existing `resume` path
- `save` now creates and confirms the default working safe point in one shell action
- `check` now says `Workspace Not Trusted` instead of leaking `Working Surface` wording
- `prompt-followup` confirms that the generated next-agent instruction preserves the bounded current step

## What This Lane Returns

On the current verified smoke contour in [alpha_lane_run_003](/Users/usbdick/Documents/New%20project/synrail/fixtures/alpha_lane_run_003):

- `init` returns `INITIALIZED`
- `save` returns `OK`
- `check` blocks on `EXACT_TASK_IDENTITY_NOT_CONFIRMED`
- thin output translates that into:
  - `NON_RESUMABLE`
  - verified checkpoint available
  - run the next bounded attempt only after restoring the original task request
- `next-step` keeps the next agent step bounded to:
  - prepare the next bounded attempt
  - restore the original task request and intended target
- `restore` returns `OK`

On the current fresh external contour in [ALPHA_EXTERNAL_RUN_001.md](/Users/usbdick/Documents/New%20project/synrail/docs/core/ALPHA_EXTERNAL_RUN_001.md):

- `check` returns `PROOF_INVALID`
- `next-step` stays bounded to `repair_final_result_artifact`
- `restore_available = false`, which is the correct reading for a fresh contour without one verified checkpoint

On the current accepted default output smoke in [thin_output_run_accepted_003](/Users/usbdick/Documents/New%20project/synrail/fixtures/thin_output_run_accepted_003):

- default mode says `ACCEPTED`
- it explains that the run reached accepted closure
- it makes clear that no repair step is required

On the current continuation-blocked output smoke in [thin_output_continue_run_002](/Users/usbdick/Documents/New%20project/synrail/fixtures/thin_output_continue_run_002):

- default mode says `Current Repair Step Still Incomplete`
- it tells the operator to finish only the current bounded repair before `synrail continue`
- it no longer falls back to the generic `Needs Review` bucket for this contour

Canonical artifacts:

- [shell init output](/Users/usbdick/Documents/New%20project/synrail/fixtures/alpha_shell_run_005/shell/init_stdout.txt)
- [shell check output with bounded repair summary](/Users/usbdick/Documents/New%20project/synrail/fixtures/alpha_shell_run_006/shell/check_stdout.txt)
- [self-contained safe point output](/Users/usbdick/Documents/New%20project/synrail/fixtures/alpha_safe_point_run_002/shell/save_stdout.txt)
- [shell next-step output](/Users/usbdick/Documents/New%20project/synrail/fixtures/alpha_shell_run_005/shell/next_step_stdout.txt)
- [shell continue output](/Users/usbdick/Documents/New%20project/synrail/fixtures/alpha_shell_run_005/shell/continue_stdout.txt)
- [shell project profile](/Users/usbdick/Documents/New%20project/synrail/fixtures/alpha_shell_run_006/lane/project_profile.json)
- [shell thin output](/Users/usbdick/Documents/New%20project/synrail/fixtures/alpha_shell_run_006/lane/thin_output.json)
- [shell prompt](/Users/usbdick/Documents/New%20project/synrail/fixtures/alpha_shell_run_006/lane/prompt.json)
- [shell prompt followup](/Users/usbdick/Documents/New%20project/synrail/fixtures/alpha_shell_run_006/lane/followup.json)
- [onboarding next-step-before-check output](/Users/usbdick/Documents/New%20project/synrail/fixtures/alpha_onboarding_run_005/shell/next_step_before_check_stdout.txt)
- [onboarding restore-without-checkpoint output](/Users/usbdick/Documents/New%20project/synrail/fixtures/alpha_onboarding_run_005/shell/restore_without_checkpoint_stdout.txt)
- [onboarding checkpoint-verify-without-checkpoint output](/Users/usbdick/Documents/New%20project/synrail/fixtures/alpha_onboarding_run_005/shell/checkpoint_verify_without_checkpoint_stdout.txt)
- [safe point save output](/Users/usbdick/Documents/New%20project/synrail/fixtures/alpha_safe_point_run_001/shell/save_stdout.txt)
- [continuation-blocked thin output](/Users/usbdick/Documents/New%20project/synrail/fixtures/thin_output_continue_run_002/thin_output.json)
- [init state](/Users/usbdick/Documents/New%20project/synrail/fixtures/alpha_lane_run_003/init/state.json)
- [working checkpoint verify](/Users/usbdick/Documents/New%20project/synrail/fixtures/alpha_lane_run_003/lane/checkpoints/working/checkpoint_verify.json)
- [thin output](/Users/usbdick/Documents/New%20project/synrail/fixtures/alpha_lane_run_003/lane/thin_output.json)
- [prompt](/Users/usbdick/Documents/New%20project/synrail/fixtures/alpha_lane_run_003/lane/prompt.json)
- [restore result](/Users/usbdick/Documents/New%20project/synrail/fixtures/alpha_lane_run_003/lane/checkpoint_restore.json)
- [accepted thin output](/Users/usbdick/Documents/New%20project/synrail/fixtures/thin_output_run_accepted_003/thin_output.json)

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
