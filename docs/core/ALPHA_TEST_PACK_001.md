# Alpha Test Pack 001

This is the first minimal tester pack for `Synrail` alpha.

The goal is not broad product exploration.

The goal is to let 3-5 experienced operators run one real alpha lane and send back hard signal.

## Install

Verified local install path:

```bash
python3 -m venv --system-site-packages .venv
.venv/bin/python -m pip install -e . --no-build-isolation
```

## 10-Minute Quickstart

```bash
PROJECT_ROOT="$(pwd)"
ARTIFACT_ROOT="$PROJECT_ROOT/.synrail"
TASK_REQUEST="Reject a plain-text final result and keep the repair bounded."
synrail init --artifact-root "$ARTIFACT_ROOT" --project-root "$PROJECT_ROOT" --task-identity "$TASK_REQUEST" --telemetry-opt-in --tester-id your_name
synrail check --artifact-root "$ARTIFACT_ROOT"
synrail repair-step --artifact-root "$ARTIFACT_ROOT"
synrail telemetry export --artifact-root "$ARTIFACT_ROOT"
```

If you already have one verified working state, extend the lane with:

```bash
synrail save --artifact-root "$ARTIFACT_ROOT"
synrail confirm-restore --artifact-root "$ARTIFACT_ROOT"
synrail restore --artifact-root "$ARTIFACT_ROOT"
```

## Scenarios

### 1. Fresh invalid-proof path

Goal:

- verify that `Synrail` rejects one malformed or plain-text final result instead of accepting closure

Expected shape:

- `check` lands on `PROOF_INVALID`
- `repair-step` stays bounded to `repair_final_result_artifact`

Reference:

- [ALPHA_EXTERNAL_RUN_001.md](/Users/usbdick/Documents/New%20project/synrail/docs/core/ALPHA_EXTERNAL_RUN_001.md)

### 2. Verified working restore path

Goal:

- verify that one previously verified working contour can be restored without replaying the whole run by hand

Expected shape:

- `save` returns `OK`
- `confirm-restore` passes
- restore returns `OK`
- working state is recoverable without false acceptance

Reference:

- [ALPHA_LANE_001.md](/Users/usbdick/Documents/New%20project/synrail/docs/core/ALPHA_LANE_001.md)

### 3. Second-operator handoff

Goal:

- verify that another operator can pick up the lane from visible artifacts only

Expected shape:

- no author memory needed
- no hidden continuation guess

Reference:

- [ALPHA_SECOND_OPERATOR_001.md](/Users/usbdick/Documents/New%20project/synrail/docs/core/ALPHA_SECOND_OPERATOR_001.md)

### 4. Telemetry export after a non-green outcome

Goal:

- verify that one tester can export a useful replay and one GitHub-Issues-ready report without leaking file contents

Expected shape:

- `telemetry/session_replay.json` exists
- `telemetry/github_issue.md` exists
- replay includes command sequence, error class, and next safe step

Reference:

- [ALPHA_TELEMETRY_001.md](/Users/usbdick/Documents/New%20project/synrail/docs/core/ALPHA_TELEMETRY_001.md)

## Feedback Questions

1. where did Synrail make the wrong decision?
2. where did you stop knowing what to do next?
3. what felt unnecessary?
4. what exactly do you lose without Synrail?
5. would you use this in a real project?

## What to Send Back

Please send back:

- the scenario you ran
- the command where you got stuck
- the telemetry export, if enabled
- one blunt sentence saying whether `Synrail` helped or added ceremony

This pack is successful only if it produces hard external signal, not polite approval.

## Current Canonical Pack Run

Current tester-pack smoke on the preferred shell:

- [check output](/Users/usbdick/Documents/New%20project/synrail/fixtures/alpha_test_pack_run_001/shell/check_stdout.txt)
- [repair-step output](/Users/usbdick/Documents/New%20project/synrail/fixtures/alpha_test_pack_run_001/shell/repair_step_stdout.txt)
- [telemetry export output](/Users/usbdick/Documents/New%20project/synrail/fixtures/alpha_test_pack_run_001/shell/telemetry_export_stdout.txt)
- [thin output](/Users/usbdick/Documents/New%20project/synrail/fixtures/alpha_test_pack_run_001/lane/thin_output.json)
- [prompt](/Users/usbdick/Documents/New%20project/synrail/fixtures/alpha_test_pack_run_001/lane/prompt.json)
- [session replay](/Users/usbdick/Documents/New%20project/synrail/fixtures/alpha_test_pack_run_001/lane/telemetry/session_replay.json)
- [issue body](/Users/usbdick/Documents/New%20project/synrail/fixtures/alpha_test_pack_run_001/lane/telemetry/github_issue.md)
