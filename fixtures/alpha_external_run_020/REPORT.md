# Alpha External Run 020

- Tester: Codex
- Agent: Claude Code
- Task: `Привет. Что это за проект и где мы на нём остановились?`
- Project: `warroom_probe_after_7f3f1a3`
- Task class:
  - `orientation`
- Start time: `2026-04-18T15:19:07+00:00`
- End time: `2026-04-18T15:19:23+00:00`
- Elapsed minutes: `0.3`
- Check iterations: `0`
- Final outcome: `ORIENTATION_SUMMARIZED`
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
  - The first harness attempt failed because `claude --output-format stream-json` requires `--verbose`.
  - The authoritative rerun stayed read-only and completed cleanly.
  - Claude did not invoke the `synrail` binary literally; instead it read `.synrail/state.json`, `task_identity.txt`, `acceptance_criteria.json`, and `final_result.json` directly.
  - Claude answered accurately and did not search parent directories or propose any writes.

## Verdict

- Verdict: Strong partial success. Claude stayed inside the governed root and used `.synrail` artifacts directly to answer the question with low noise, but the entry path is still not a visible literal `synrail status` habit.

## Notes

- Hidden oracle result: `n/a`
- Most important product signal: Claude can answer “what is this project / where did we leave off?” from governed artifacts alone in a short read-only run.
- Most important remaining doubt: The lane is still governed-artifact-first rather than explicitly CLI-first.
