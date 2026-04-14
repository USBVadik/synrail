# Alpha Lane 001

This is the first narrow alpha lane for `Synrail`.

It is intentionally one contour, not a broad product shell:

1. install one local `synrail` command
2. initialize one artifact root
3. create and verify one working checkpoint when a verified working state exists
4. run one bounded change/check contour
5. generate one bounded follow-up prompt
6. restore the verified working state if the contour is blocked

The lane exists to prove one user value clearly:

- an agent can hit a non-green outcome
- `Synrail` does not accept false success
- the operator gets one bounded next step
- one verified working state can be restored without replaying the whole run by hand

## Verified Install Path

The currently verified alpha install path is:

```bash
python3 -m venv .venv
.venv/bin/python setup.py install
```

The reference smoke for this document was run through the installed `synrail` console script, not by calling helper files directly.

`pip install . --no-build-isolation` is not yet the trusted local alpha path on the current toolchain because the local venv lacked `bdist_wheel` during smoke.

## Verified Contours

Use one artifact root per run:

```bash
ARTIFACT_ROOT="$(pwd)/.synrail"
```

### Verified-working contour

This is the currently verified restore-capable alpha lane:

```bash
synrail init --artifact-root "$ARTIFACT_ROOT"
synrail checkpoint create --artifact-root "$ARTIFACT_ROOT" --checkpoint-id working
synrail checkpoint verify --artifact-root "$ARTIFACT_ROOT" --checkpoint-id working
synrail check --artifact-root "$ARTIFACT_ROOT" \
  --target-path "$ARTIFACT_ROOT/final_result.txt" \
  --baseline-identity trusted_clean \
  --execution-surface-identity clean-clone \
  --final-result "$ARTIFACT_ROOT/final_result.txt" \
  --clean-surface \
  --artifact-viable \
  --helper-ok \
  --credentials-ok \
  --prompt-identity-ok
synrail generate-prompt --artifact-root "$ARTIFACT_ROOT"
synrail restore --artifact-root "$ARTIFACT_ROOT" --checkpoint-id working
```

This contour assumes the artifact root already reflects one verified working state.

### Fresh first-run contour

On a fresh `init`, `Synrail` can still give bounded value immediately:

```bash
synrail init --artifact-root "$ARTIFACT_ROOT"
synrail check --artifact-root "$ARTIFACT_ROOT" ...
synrail generate-prompt --artifact-root "$ARTIFACT_ROOT"
```

That fresh contour does not yet guarantee `restore_available`, because no verified checkpoint exists yet.

## What This Lane Returns

On the current verified smoke contour in [alpha_lane_run_003](/Users/usbdick/Documents/New%20project/synrail/fixtures/alpha_lane_run_003):

- `init` returns `INITIALIZED`
- `checkpoint create` returns `OK`
- `checkpoint verify` returns `PASSED`
- `check` blocks on `EXACT_TASK_IDENTITY_NOT_CONFIRMED`
- thin output translates that into:
  - `NON_RESUMABLE`
  - verified checkpoint available
  - continue through governed forward path, not named `resume`
- `generate-prompt` keeps the next agent step bounded to:
  - `continue_forward_orchestration`
  - restore exact prompt and task identity
- `restore` returns `OK`

On the current fresh external contour in [ALPHA_EXTERNAL_RUN_001.md](/Users/usbdick/Documents/New%20project/synrail/docs/core/ALPHA_EXTERNAL_RUN_001.md):

- `check` returns `PROOF_INVALID`
- `generate-prompt` stays bounded to `repair_final_result_artifact`
- `restore_available = false`, which is the correct reading for a fresh contour without one verified checkpoint

Canonical artifacts:

- [init state](/Users/usbdick/Documents/New%20project/synrail/fixtures/alpha_lane_run_003/init/state.json)
- [working checkpoint verify](/Users/usbdick/Documents/New%20project/synrail/fixtures/alpha_lane_run_003/lane/checkpoints/working/checkpoint_verify.json)
- [thin output](/Users/usbdick/Documents/New%20project/synrail/fixtures/alpha_lane_run_003/lane/thin_output.json)
- [prompt](/Users/usbdick/Documents/New%20project/synrail/fixtures/alpha_lane_run_003/lane/prompt.json)
- [restore result](/Users/usbdick/Documents/New%20project/synrail/fixtures/alpha_lane_run_003/lane/checkpoint_restore.json)

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
