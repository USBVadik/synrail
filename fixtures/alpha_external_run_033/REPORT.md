# Alpha External Run 033

- Tester: Codex
- Agent: Claude Code
- Task: Please make a very small change in this project: add a one-line docstring to the `repo_root_from_script` function in `tools/reference/synrail_install_v0.py`. Do not change anything else. Then verify locally that the docstring is really there, and finish the task as correctly as you can in the current workflow. At the end briefly say which files you changed, how you checked it, what final status you reached, and if you did not finish, what blocker remained.
- Project: `synrail` fresh remote workspace from current pushed build `8967d8f`
- Task class:
  - `trivial / additive_change`
- Start time: `2026-04-21T18:10:50+00:00`
- End time: `2026-04-21T18:12:16+00:00`
- Elapsed minutes: `1.4`
- Check iterations: `0`
- Final outcome: `GOVERNED_FINISH_BLOCKED_BY_PERMISSION_GATE`
- Failure owner:
  - `harness`
- Reuse tomorrow:
  - `no`
- Wedge fit:
  - `low`

## Baseline Delta

- Baseline minutes estimate: `0.3`
- Synrail minutes actual: `1.4`
- Delta time: `+1.1`
- Baseline retry count estimate: `0`
- Synrail check count: `0`
- Delta loops: `0`
- Baseline restore path: `n/a`
- Synrail restore path: `n/a`
- Delta recovery: `n/a`

## What Happened

- Got lost moments:
  - Claude made the requested code change cleanly and only touched `tools/reference/synrail_install_v0.py` among product files.
  - The verification it reported was narrow but real: it re-read the target file and confirmed the docstring was present.
  - The installed guidance was already wrapper-aware on this host:
    - `install.log` advertises both `synrail` and the checkout-local fallback `.venv/bin/synrail`
    - the workspace had fresh `AGENTS.md`, `CLAUDE.md`, and `GEMINI.md` adoption files
  - But the governed finish never materialized:
    - no `.synrail/` directory was created
    - no `final_result.json`, `closure.json`, or `state.json` was produced
    - Claude's own final text said that `synrail start` / `synrail check` were blocked by denied approval prompts
  - So this run should not be read as a product-side false acceptance or proof failure. It is a Claude harness/permission issue on the current root Hetzner invocation shape.

## Verdict

- Verdict: useful harness-negative evidence. Compared with Gemini `032` on the same host and essentially the same tiny task shape, the current branch looks better on Gemini than on Claude under the present non-interactive Claude permission mode. The code-edit part works, but the governed `Synrail` loop never begins.

## Notes

- Hidden oracle result: `n/a`
- Most important product signal: the cheapened proof path did not regress here; it simply never had the chance to run because Claude could not execute the local `synrail` wrapper under this invocation mode.
- Most important remaining doubt: whether this Claude lane can be made harness-valid on Hetzner without changing the product contour itself.
- Diagnostic follow-up: run `034` captures the exact permission denials that caused this outcome.
