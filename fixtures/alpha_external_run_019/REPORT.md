# Alpha External Run 019

- Tester: Codex
- Agent: Gemini CLI
- Task: `Привет. Что это за проект и где мы на нём остановились?`
- Project: `warroom_probe_after_7f3f1a3`
- Task class:
  - `orientation`
- Start time: `2026-04-18T15:13:13+00:00`
- End time: `2026-04-18T15:14:04+00:00`
- Elapsed minutes: `0.9`
- Check iterations: `0`
- Final outcome: `ORIENTATION_SUMMARIZED_WITH_OVEREXPLORATION`
- Failure owner:
  - `mixed`
- Reuse tomorrow:
  - `unclear`
- Wedge fit:
  - `medium`

## Baseline Delta

- Baseline minutes estimate: `0.4`
- Synrail minutes actual: `0.9`
- Delta time: `+0.5`
- Baseline retry count estimate: `0`
- Synrail check count: `0`
- Delta loops: `0`
- Baseline restore path: `n/a`
- Synrail restore path: `n/a`
- Delta recovery: `n/a`

## What Happened

- Got lost moments:
  - Gemini oriented to the governed state successfully and summarized the previously accepted task correctly.
  - It did not drift into sibling probe directories or broad parent search.
  - After that it still over-explored: it re-verified the old UI change, opened extra template context, and probed the database schema.
  - It fell back to Python-based DB inspection after `sqlite3` was unavailable, which was too heavy for a simple orientation prompt.

## Verdict

- Verdict: Partial success. Governed context was used and the answer was correct, but the lane is still noisier than it should be and does not yet show a clean literal `synrail` CLI-first entry.

## Notes

- Hidden oracle result: `n/a`
- Most important product signal: Gemini can recover project context from governed state without drifting into sibling probe folders.
- Most important remaining doubt: The orientation path is still artifact-aware rather than visibly `synrail`-first, and it still encourages too much follow-on archaeology.
