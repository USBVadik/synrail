# Alpha External Run 014e

- Tester: Codex
- Agent: Codex manual restore probe
- Task: Re-run the restore round-trip on the deployed file-copy build for the no-commit git workspace contour.
- Project: retry-service fixed template (`/root/alpha_retry_service_fixed_template`)
- Task class: `restore`
- Start time: 2026-04-18T14:34:28+00:00
- End time: 2026-04-18T14:34:30+00:00
- Elapsed minutes: 0.0 min (about 2 seconds; shell-driven manual probe)
- Check iterations: 0
- Final outcome: `RESTORED`
- Failure owner: `none`
- Reuse tomorrow: `yes`
- Wedge fit: `high`

## Baseline Delta

- Baseline minutes estimate: `0.3`
- Synrail minutes actual: `0.0`
- Delta time: `-0.3`
- Baseline retry count estimate: `0`
- Synrail check count: `0`
- Delta loops: `0`
- Baseline restore path: `manual revert of the changed file or copy back from the known-good baseline`
- Synrail restore path: `save (file-copy pre-run snapshot) -> confirm-restore -> restore`
- Delta recovery: `Synrail now matches or beats the baseline on this contour because it restores the broken file and returns the tests to green without manual intervention`

## What Happened

- Got lost moments:
  - The workspace is still a git work tree without commits: `git rev-parse --is-inside-work-tree` passed while `git rev-parse HEAD` failed.
  - On this updated build, `save --project-root .` no longer recorded `workspace_snapshot.type = "none"`; it created a `file_copy` snapshot with `file_count = 8`.
  - `confirm-restore` passed as expected.
  - `restore` now genuinely restored the workspace file instead of only replaying Synrail state: `retry_logic.py` returned to its original contents and post-restore tests were green.
  - The restore trace explicitly records `workspace_restored: true`.

## Verdict

- Verdict: Strong positive validation. The no-commit git restore contour is now actually working end to end, not just failing more honestly. This closes the specific gap that 014d still exposed.

## Notes

- Hidden oracle result: baseline tests were green before mutation, broken tests were red after mutation, and post-restore tests were green again.
- Most important product signal: the new `file_copy` fallback turned a previously unsupported restore contour into a successful recovery path.
- Most important remaining doubt: we now know restore works for no-commit git workspaces, but we still do not have an external run for a truly non-git project tree.
