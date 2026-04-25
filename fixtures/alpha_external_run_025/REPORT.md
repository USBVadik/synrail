# Alpha External Run 025

- Tester: Codex
- Agent: Gemini CLI
- Task: Please make a very small change in this project: add a one-line docstring to the main function in `alpha.py`. Do not change anything else. Then verify locally that the docstring is really there, and finish the task as correctly as you can in the current workflow. At the end briefly say which files you changed, how you checked it, what final status you reached, and if you did not finish, what blocker remained.
- Project: `synrail` fresh remote workspace from current build `7146297`, reusing the prior working `.venv` from the unattended Gemini lane
- Task class:
  - `trivial / additive_change`
- Start time: `2026-04-18T21:11:18Z`
- End time: `2026-04-18T21:11:40Z` (`closure.json` server mtime; post-run finalizer again did not persist `end.txt`)
- Elapsed minutes: `0.4`
- Check iterations: `1`
- Final outcome: `CLOSURE_ACCEPTED_WITH_INFERRED_METHOD_AND_RUNTIME_VERIFICATION`
- Failure owner:
  - `mixed`
- Reuse tomorrow:
  - `yes`
- Wedge fit:
  - `low`

## Baseline Delta

- Baseline minutes estimate: `0.3`
- Synrail minutes actual: `0.4`
- Delta time: `+0.1`
- Baseline retry count estimate: `0`
- Synrail check count: `1`
- Delta loops: `+1`
- Baseline restore path: `n/a`
- Synrail restore path: `n/a`
- Delta recovery: `n/a`

## What Happened

- Got lost moments:
  - Gemini again reached accepted closure on the unattended lane and emitted `final_result.status = "PROVEN"`.
  - This is the first live run where the new shaping tranche actually cashes in the inferred-method path: `bundle.json` records `normalized_method = "direct_file_observation"`, `method_inferred = true`, and `has_structured_runtime_verification = true`.
  - The run did this without a `git_diff`; `final_result.json` carried only a structured direct-observation record with `changed_file`, `added_line`, `verification_command`, and `verification_result`.
  - The lane also got materially cheaper: one `synrail check`, zero repairs, zero rejections, and roughly `0.4` minutes end-to-end, which is the closest Synrail has come yet to the `0.3` baseline estimate on this trivial contour.
  - The remaining gap is now narrower and clearer: Gemini still authored `readback.txt` and `scenario_proof.txt`, so this is not yet a full waiver win even though the trust-bearing runtime verification is already strong enough on its own.
  - Two smaller seams still showed up in the trace:
    - Gemini still had to probe the executable path instead of immediately using the intended `synrail` binary.
    - `git diff` again came back empty, so the lane is still leaning on direct observation rather than a clean patch-based provenance story.

## Verdict

- Verdict: strong positive evidence. This is the first unattended Gemini trivial run that reaches accepted closure with inferred direct-observation method and strong runtime verification in a single pass, pushing the trivial lane close to baseline cost even though the prose proof surfaces are still being authored.

## Notes

- Hidden oracle result: `n/a`
- Most important product signal: the live Gemini lane can now materialize the stronger structured `diff_provenance` contour on its own, with `git_diff` absent and without any repair loop.
- Most important remaining doubt: `readback` and `scenario_proof` are still present and semantically active, so the absolute cheapest evidence-first contour has not fully displaced prose proof yet.
