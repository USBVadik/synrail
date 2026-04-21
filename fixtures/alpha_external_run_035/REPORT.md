# Alpha External Run 035

- Tester: Codex
- Agent: Claude Code
- Task: Please make a very small change in this project: add a one-line docstring to the `repo_root_from_script` function in `tools/reference/synrail_install_v0.py`. Do not change anything else. Then verify locally that the docstring is really there, and finish the task as correctly as you can in the current workflow. At the end briefly say which files you changed, how you checked it, what final status you reached, and if you did not finish, what blocker remained.
- Project: `synrail` fresh remote workspace from current pushed build `8967d8f`
- Task class:
  - `trivial / additive_change`
- Start time: `2026-04-21T18:28:34+00:00`
- End time: `2026-04-21T18:29:53+00:00`
- Elapsed minutes: `1.3`
- Check iterations: `1`
- Final outcome: `CLOSURE_ACCEPTED`
- Failure owner:
  - `none`
- Reuse tomorrow:
  - `unclear`
- Wedge fit:
  - `low`

## Baseline Delta

- Baseline minutes estimate: `0.3`
- Synrail minutes actual: `1.3`
- Delta time: `+1.0`
- Baseline retry count estimate: `0`
- Synrail check count: `1`
- Delta loops: `+1`
- Baseline restore path: `n/a`
- Synrail restore path: `n/a`
- Delta recovery: `n/a`

## What Happened

- Got lost moments:
  - This rerun used the same tiny `tools/reference` contour as `032` and `033`, but it pre-approved the checkout-local `synrail` wrapper in Claude's `allowedTools` list.
  - That removed the earlier harness wall cleanly:
    - Claude read the local dashboard
    - started a controlled run
    - edited the target file
    - updated `final_result.json`
    - ran `synrail check`
    - and reached accepted closure
  - The trust path stayed materially cheapened:
    - `final_result.status = "PROVEN"`
    - `.synrail/closure.json` = `ACCEPTED`
    - `.synrail/state.json` = `CLOSURE_ACCEPTED`
    - `readback.txt` absent
    - `scenario_proof.txt` absent
    - `cleanup_status` absent
  - The remaining denials were non-blocking and diagnostic-only:
    - Claude was denied an AST verification shell command
    - and denied a `git diff` shell command
    - but it still verified the docstring via `grep` and finished green under `synrail check`

## Verdict

- Verdict: strong positive evidence. Once the wrapper-level harness seam is removed, Claude reaches the same governed cheapened proof path that Gemini already showed on this branch. The lane is still slower than baseline, but it is now a real accepted cross-agent trivial contour rather than a Gemini-only win.

## Notes

- Hidden oracle result: `n/a`
- Most important product signal: the current branch now has both Gemini and Claude live evidence for the same tiny accepted contour with optional prose surfaces still absent.
- Most important remaining doubt: this Claude success still depends on a harness-side pre-approval of the local wrapper path, so the host-level default invocation is not yet boring enough on its own.
