# Alpha Test Pack 001

Review this as a narrow proof-first control product, not as a platform.

Current support boundary for this pack:

- supported: one local trusted worktree on the same machine where the agent acts
- not yet supported: remote host / ops / production-target execution as a first-class alpha lane
- supported integration pattern: deploy and restart scripts can enforce local Synrail authorization before side effects

The goal of this pack is simple:

- show one false-success contour that `Synrail` blocks honestly
- show one restore/re-entry contour that is cheaper than manual archaeology
- get blunt external signal in under 10 minutes

## Install

Preferred tester install path:

```bash
python3 tools/reference/synrail_install_v0.py --venv .venv
```

## 10-Minute Quickstart

This is the cheapest first-run contour we currently trust.

```bash
PROJECT_ROOT="$(pwd)"
ARTIFACT_ROOT=".synrail"
TASK_REQUEST="Reject a plain-text final result and keep the repair bounded."

synrail start --artifact-root "$ARTIFACT_ROOT" --project-root "$PROJECT_ROOT" --task-identity "$TASK_REQUEST" --telemetry-opt-in --tester-id your_name
# synrail start already creates starter proof files under $ARTIFACT_ROOT:
# - $ARTIFACT_ROOT/final_result.json
# - $ARTIFACT_ROOT/readback.txt
# - $ARTIFACT_ROOT/scenario_proof.txt
# do this now: edit only those starter proof files in place, then run synrail check
# or use Wow Scenario A below to see the false-success block
synrail check --artifact-root "$ARTIFACT_ROOT"
synrail repair-step --artifact-root "$ARTIFACT_ROOT"
synrail telemetry export --artifact-root "$ARTIFACT_ROOT"
```

What this should prove in minutes:

- a plausible plain-text result is not accepted as done
- the next repair stays bounded
- feedback export is one command, not manual archaeology

## Default Commands

These are the only outer verbs a first tester should care about.

- `synrail start`
  Why it exists: starts one controlled run and captures the minimum bootstrap provenance needed for the lane.
- `synrail save`
  Why it exists: only use it when a verified fallback is worth restoring quickly later.
- `synrail check`
  Why it exists: this is the truth gate that decides accepted, blocked, repairable, or restore-needed.
- `synrail repair-step`
  Why it exists: gives one bounded next repair instead of asking the operator to reverse-engineer artifacts.
- `synrail retry`
  Why it exists: reruns only the bounded repair contour, not a broader hopeful loop.
- `synrail restore`
  Why it exists: gets back to a verified fallback faster and more honestly than manual rollback archaeology.
- `synrail telemetry export`
  Why it exists: produces one replay and one issue-ready summary without hand-assembling artifacts.

Explicit but not default:

- `synrail confirm-restore`
  Use only if you explicitly want to re-check a saved fallback again.
- `synrail bug-packet`
  Use only when the normal feedback export is not enough for the bug report.

## Wow Scenario A — False Success Blocked

Question:

- what exactly would the operator lose without `Synrail`?

Answer:

- the agent leaves a plausible human-readable result
- a baseline path could treat that as “done enough”
- `Synrail` blocks acceptance, names the failure as proof-invalid, and gives one bounded next repair

Run:

```bash
synrail start --artifact-root ".synrail" --project-root "$(pwd)" --task-identity "Reject a plain-text final result and keep the repair bounded."
# synrail already created starter proof files under .synrail/ for the native path
# this scenario intentionally bypasses that path with a plain-text result:
printf 'Implemented the change and confirmed it locally.\n' > .synrail/final_result.txt
synrail check --artifact-root ".synrail"
synrail repair-step --artifact-root ".synrail"
```

Expected shape:

- `check` lands on `PROOF_INVALID`
- `repair-step` stays bounded to `repair_final_result_artifact`

Reference:

- [ALPHA_EXTERNAL_RUN_001.md](./ALPHA_EXTERNAL_RUN_001.md)

## Wow Scenario B — Restore / Re-entry Leverage

Question:

- what exactly would the operator lose without `Synrail`?

Answer:

- after a non-green or risky contour, the operator would need manual rollback archaeology
- with `Synrail`, one verified fallback can be restored directly and the re-entry path stays explicit

Run:

```bash
synrail start --artifact-root ".synrail" --project-root "$(pwd)" --task-identity "Preserve one verified fallback before a bounded change."
synrail save --artifact-root ".synrail"
synrail check --artifact-root ".synrail"
synrail restore --artifact-root ".synrail"
```

If the contour is repairable, continue with:

```bash
synrail repair-step --artifact-root ".synrail"
synrail retry --artifact-root ".synrail"
```

Expected shape:

- `save` finishes with one trusted fallback
- `restore` is available without replaying the whole run by hand
- `retry` stays bounded to the current repair step

Reference:

- [ALPHA_LANE_001.md](./ALPHA_LANE_001.md)

## Optional Deep-Dive Checks

Use these only if you want to push the current contour harder.

- second-operator handoff:
  - [ALPHA_SECOND_OPERATOR_001.md](./ALPHA_SECOND_OPERATOR_001.md)
- feedback export boundaries:
  - [ALPHA_TELEMETRY_001.md](./ALPHA_TELEMETRY_001.md)

## Feedback Questions

1. where did `Synrail` make the wrong decision?
2. where did you stop knowing what to do next?
3. which command felt like ceremony instead of leverage?
4. what exactly did `Synrail` save you from?
5. would you keep this in a real workflow with a costly false green?

## What to Send Back

Please send back:

- which scenario you ran
- the command where you got stuck
- the telemetry export, if you enabled it
- one blunt sentence saying whether `Synrail` prevented a real loss or just added process

This pack is successful only if it produces hard external signal, not polite approval.

If you specifically want to review the current deploy-side-effect boundary, use [DEPLOY_GUARD_INTEGRATION_001.md](./DEPLOY_GUARD_INTEGRATION_001.md). Review it as a narrow guard pattern, not as full remote lane support.

## Current Canonical Pack Run

Current tester-pack smoke on the preferred shell:

- [start output](../../fixtures/alpha_test_pack_run_004/shell/start_stdout.txt)
- [check output](../../fixtures/alpha_test_pack_run_004/shell/check_stdout.txt)
- [repair-step output](../../fixtures/alpha_test_pack_run_004/shell/repair_step_stdout.txt)
- [telemetry export output](../../fixtures/alpha_test_pack_run_004/shell/telemetry_export_stdout.txt)
- [thin output](../../fixtures/alpha_test_pack_run_004/lane/thin_output.json)
- [prompt](../../fixtures/alpha_test_pack_run_004/lane/prompt.json)
- [operator brief](../../fixtures/alpha_test_pack_run_004/lane/operator_brief.json)
- [operator render](../../fixtures/alpha_test_pack_run_004/lane/operator_render.md)
- [second operator](../../fixtures/alpha_test_pack_run_004/lane/second_operator.json)
- [operator reading](../../fixtures/alpha_test_pack_run_004/lane/operator_reading.json)
- [session replay](../../fixtures/alpha_test_pack_run_004/lane/telemetry/session_replay.json)
- [issue body](../../fixtures/alpha_test_pack_run_004/lane/telemetry/github_issue.md)

The current validation reading should now be interpreted as two linked checks, not one:

- the shell pack still has to prove the bounded non-green contour end-to-end
- the claim-validation pack must also prove that:
  - a second operator can follow the contour without author intuition
  - harness-owned reports are excluded from kernel roadmap decisions
  - only explicitly strong mixed reports are allowed to move kernel roadmap decisions with caution
