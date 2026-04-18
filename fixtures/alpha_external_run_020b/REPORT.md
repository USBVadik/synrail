# Alpha External Run 020b

- Tester: Codex
- Agent: Claude Code
- Task: `Привет. Что это за проект и где мы на нём остановились?`
- Project: `warroom_probe_after_7f3f1a3`
- Task class:
  - `orientation`
- Start time: `2026-04-18T15:35:37+00:00`
- End time: `2026-04-18T15:35:56+00:00`
- Elapsed minutes: `0.3`
- Check iterations: `0`
- Final outcome: `ORIENTATION_SUMMARIZED_WITH_SYNRAIL_FIRST`
- Failure owner:
  - `none`
- Reuse tomorrow:
  - `yes`
- Wedge fit:
  - `medium`

## Baseline Delta

- Baseline minutes estimate: `0.4`
- Synrail minutes actual: `0.3`
- Delta time: `-0.1`
- Baseline retry count estimate: `0`
- Synrail check count: `0`
- Delta loops: `0`
- Baseline restore path: `n/a`
- Synrail restore path: `n/a`
- Delta recovery: `n/a`

## What Happened

- Got lost moments:
  - Claude's first action was the literal Synrail command: `/root/synrail/.venv/bin/synrail 2>&1`.
  - After reading the dashboard output, Claude used `.synrail/state.json`, `task_identity.txt`, and `final_result.json` to fill in the details of the last accepted run.
  - There was one non-blocking tool denial on a multi-operation Bash command (`python3 -m json.tool` inside a pipe), but the run recovered immediately by switching to `Read` and smaller commands.

## Verdict

- Verdict: Clear positive retest. The orientation guidance fix succeeded on Claude: the lane now starts with literal Synrail, stays read-only, and returns a concise governed summary.

## Notes

- Hidden oracle result: `n/a`
- Most important product signal: This is the first direct external signal that the orientation lane can start with an actual `synrail` command rather than only implicit `.synrail` reads.
- Most important remaining doubt: Claude still follows the dashboard call with direct artifact reads, so the lane is improved but not yet fully standardized to one tiny status-only flow.
