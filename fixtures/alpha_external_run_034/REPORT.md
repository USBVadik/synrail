# Alpha External Run 034

- Tester: Codex
- Agent: Claude Code
- Task: Please make a very small change in this project: add a one-line docstring to the `repo_root_from_script` function in `tools/reference/synrail_install_v0.py`. Do not change anything else. Then verify locally that the docstring is really there, and finish the task as correctly as you can in the current workflow. At the end briefly say which files you changed, how you checked it, what final status you reached, and if you did not finish, what blocker remained.
- Project: `synrail` fresh remote workspace from current pushed build `8967d8f`
- Task class:
  - `trivial / additive_change / trace_probe`
- Start time: `2026-04-21T18:15:57+00:00`
- End time: `2026-04-21T18:16:35+00:00`
- Elapsed minutes: `0.6`
- Check iterations: `0`
- Final outcome: `HARNESS_PERMISSION_DENIAL_CONFIRMED`
- Failure owner:
  - `harness`
- Reuse tomorrow:
  - `no`
- Wedge fit:
  - `low`

## Baseline Delta

- Baseline minutes estimate: `0.3`
- Synrail minutes actual: `0.6`
- Delta time: `+0.3`
- Baseline retry count estimate: `0`
- Synrail check count: `0`
- Delta loops: `0`
- Baseline restore path: `n/a`
- Synrail restore path: `n/a`
- Delta recovery: `n/a`

## What Happened

- Got lost moments:
  - This was a diagnostic rerun of the same tiny task on the same host, but with Claude output switched to `stream-json` so the tool trace would be preserved.
  - Claude again edited only `tools/reference/synrail_install_v0.py` and confirmed the docstring by rereading the file.
  - The trace captured the real blocker directly:
    - `permission_denials` includes a Bash call to `/root/alpha_external_run_034/workspace/.venv/bin/synrail 2>&1 | head -40`
    - and then a second denial on plain `/root/alpha_external_run_034/workspace/.venv/bin/synrail`
  - No `.synrail/` directory or governed artifacts were produced, which matches the denied-wrapper explanation exactly.

## Verdict

- Verdict: diagnostic confirmation, not a new product negative. `034` shows that the Claude failure on Hetzner is currently caused by the non-interactive permission gate around the checkout-local `synrail` wrapper, not by a false `Accepted` or by a broken cheapened proof path inside `Synrail`.

## Notes

- Hidden oracle result: `n/a`
- Most important product signal: the current root-host Claude harness cannot exercise the wrapper-based first loop reliably enough to compare product behavior against Gemini on equal terms.
- Most important remaining doubt: whether a different Claude invocation mode can make this lane harness-valid without changing the product itself.
