# Alpha External Run 012b

- Tester: Codex
- Agent: Claude Code (intended first operator) then Gemini CLI (intended second operator)
- Task: Same as run 012, but rerun with Claude in a more permissive mode to get past the shell gate.
- Project: synrail (server-side workspace assembled from the current synced worktree)
- Task class: `handoff`
- Start time: 2026-04-18T10:12:22+00:00
- End time: 2026-04-18T10:12:22+00:00
- Elapsed minutes: 0.0 min
- Check iterations: 0
- Final outcome: `INVALID_HARNESS_ROOT_BYPASS_BLOCKED`
- Failure owner: `harness`
- Reuse tomorrow: `no`
- Wedge fit: `high`

## Baseline Delta

- Baseline minutes estimate: `n/a`
- Synrail minutes actual: `0.0`
- Delta time: `n/a`
- Baseline retry count estimate: `n/a`
- Synrail check count: `0`
- Delta loops: `n/a`
- Baseline restore path: `n/a`
- Synrail restore path: `n/a`
- Delta recovery: `n/a`

## What Happened

- Got lost moments:
  - The rerun switched Claude to `--permission-mode bypassPermissions`.
  - Claude CLI immediately refused that mode under root/sudo privileges for security reasons.
  - As a result, the rerun never even reached the point where a governed handoff state could be created.

## Verdict

- Verdict: Also invalid as a product signal. The rerun is still dominated by Claude harness policy, just in a different way than run 012.

## Notes

- Hidden oracle result: none; no substantive governed work happened.
- Most important product signal: the current server-side Claude harness needs a non-root or differently brokered lane before we can honestly re-measure Claude→Gemini handoff.
- Most important remaining doubt: handoff is still a strong wedge in Gemini-only evidence, but the Claude first-operator lane is not yet testable enough to strengthen that claim.
