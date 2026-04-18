# Alpha External Run 023

- Tester: Codex
- Agent: Gemini CLI
- Task: Please make a very small change in this project: add a one-line docstring to the main function in `alpha.py`. Do not change anything else. Then verify locally that the docstring is really there, and finish the task as correctly as you can in the current workflow. At the end briefly say which files you changed, how you checked it, what final status you reached, and if you did not finish, what blocker remained.
- Project: `synrail` fresh remote workspace from current build `3839fe7`, reusing the prior working `.venv` from the unattended Gemini lane
- Task class:
  - `trivial / additive_change`
- Start time: `2026-04-18T20:26:52Z`
- End time: `2026-04-18T20:29:41Z`
- Elapsed minutes: `2.8`
- Check iterations: `1` (inferred from accepted closure plus zero repairs/rejections)
- Final outcome: `CLOSURE_ACCEPTED_WITH_PROVEN_STATUS_BUT_NO_WAIVER`
- Failure owner:
  - `mixed`
- Reuse tomorrow:
  - `unclear`
- Wedge fit:
  - `low`

## Baseline Delta

- Baseline minutes estimate: `0.3`
- Synrail minutes actual: `2.8`
- Delta time: `+2.5`
- Baseline retry count estimate: `0`
- Synrail check count: `1`
- Delta loops: `+1`
- Baseline restore path: `n/a`
- Synrail restore path: `n/a`
- Delta recovery: `n/a`

## What Happened

- Got lost moments:
  - Gemini again reached accepted closure on the unattended lane and emitted `final_result.status = "PROVEN"`.
  - This run is stronger than `022` on one narrow point: `diff_provenance` now includes both `verification_command` and `verification_result` instead of leaving `verification_result` blank.
  - But the new evidence-first cheapening did **not** actually trigger the readback/scenario waiver path on this real run. `bundle.json` still reports `readback.waived_by_runtime_corroboration = false` and `scenario_proof.waived_by_runtime_corroboration = false`.
  - The reason is concrete: Gemini still omitted `diff_provenance.method`, so the structured runtime verification record was not strong enough to count as `has_structured_runtime_verification`.
  - The agent therefore still filled both `readback.txt` and `scenario_proof.txt`, and acceptance continued to depend on labeled scenario verification rather than on a fully sufficient structured provenance record alone.
  - Two harness seams also showed up: Gemini first hit a bare `synrail` permission problem and recovered by switching to the full `.venv/bin/synrail` path, and the remote post-run collector failed to finish, so the final artifacts had to be recovered manually from the workspace after closure was already accepted.

## Verdict

- Verdict: mixed-positive evidence. The new kernel remains compatible with a real unattended Gemini trivial run and now captures richer `diff_provenance` than `022`, but the cheaper evidence-first contour still was not realized in practice because the agent did not complete the structured provenance record strongly enough to waive `readback` and `scenario_proof`.

## Notes

- Hidden oracle result: `n/a`
- Most important product signal: stronger real-world `PROVEN` proof survives on the unattended Gemini lane, and `verification_result` now appears inside `diff_provenance` on a live run.
- Most important remaining doubt: the actual operator-tax win still has not materialized, because the live agent kept both prose proof surfaces and the run still paid a noticeable harness detour before reaching closure.
