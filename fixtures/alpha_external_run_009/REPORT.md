# Alpha External Run 009

- Tester: Codex
- Agent: Gemini CLI
- Task: Please make a very small change in this project: add a one-line docstring to the main function in alpha.py. Do not change anything else. Then verify locally that the docstring is really there, and finish the task as correctly as you can in the current workflow. At the end briefly say which files you changed, how you checked it, what final status you reached, and if you did not finish, what blocker remained.
- Project: synrail (fresh remote clone from `/root/synrail`, live tranche with pre-run snapshot / anti-narrative / ceremony-compression worktree synced but not yet committed)
- Task class: `trivial / additive_change`
- Start time: 2026-04-18T09:46:32+00:00
- End time: 2026-04-18T09:47:32+00:00 (approximate from remote artifact mtimes; `end.txt` was not emitted)
- Elapsed minutes: 1.0 min (approx. 60s)
- Check iterations: 4
- Final outcome: `DOCTOR_BLOCKED` / not accepted
- Failure owner: `product`
- Reuse tomorrow: `no`
- Wedge fit: `low`

## Baseline Delta

- Baseline minutes estimate: `0.3`
- Synrail minutes actual: `1.0`
- Delta time: `+0.7`
- Baseline retry count estimate: `0`
- Synrail check count: `4`
- Delta loops: `+4`
- Baseline restore path: `n/a`
- Synrail restore path: `n/a`
- Delta recovery: `n/a`

## What Happened

- Got lost moments:
  - Gemini did the tiny code change immediately, but then fell into a visible `check -> repair-step -> check -> retry/check --clean-surface` loop.
  - The run still surfaced `--clean-surface` as required trust ceremony on a trivial task, which is exactly the behavior this tranche was meant to compress.
  - The agent also wrote a structurally weak `final_result.json` (`changed_files` instead of `modified_files`, vague `diff_provenance`, no real `cleanup_status`) and `Synrail` blocked closure rather than silently accepting it.
  - The Gemini tool lane itself said `retry --clean-surface` errored, which kept the run in a messy trust/proof state even after the actual code change was correct.

## Verdict

- Verdict: Strong negative signal for cheap-task overhead, but also a useful proof/trust honesty signal. `Synrail` did not false-green the run; instead it forced the trivial task into a still-too-visible trust/proof burden. This means the product stayed honest, but the first-loop compression is still not good enough for this contour.

## Notes

- Hidden oracle result: `n/a`; manual surface inspection and artifact inspection confirmed the docstring exists, but the run did not reach accepted closure.
- Most important product signal: trivial tasks are still paying too much visible control tax, especially around workspace trust and final-result structure.
- Most important remaining doubt: the current auto clean-surface / compressed-loop tranche did not yet remove `--clean-surface` pain from a live Gemini trivial run.
