# Alpha External Run 014d

- Tester: Codex
- Agent: Codex manual restore probe
- Task: Re-run the restore round-trip after the latest checkpoint honesty fix and capture both the checkpoint record and restore trace on the deployed build.
- Project: retry-service fixed template (`/root/alpha_retry_service_fixed_template`)
- Task class: `restore`
- Start time: 2026-04-18T13:04:54+00:00
- End time: 2026-04-18T13:04:56+00:00
- Elapsed minutes: 0.0 min (about 2 seconds; shell-driven manual probe)
- Check iterations: 0
- Final outcome: `RESTORE_FAILED_HONESTLY_FOR_UNSUPPORTED_WORKSPACE`
- Failure owner: `product`
- Reuse tomorrow: `unclear`
- Wedge fit: `high`

## Baseline Delta

- Baseline minutes estimate: `0.3`
- Synrail minutes actual: `0.0`
- Delta time: `-0.3`
- Baseline retry count estimate: `0`
- Synrail check count: `0`
- Delta loops: `0`
- Baseline restore path: `manual revert of the changed file or copy back from the known-good baseline`
- Synrail restore path: `save (pre-run snapshot armed) -> confirm-restore -> restore -> honest restore-failed rollback`
- Delta recovery: `Synrail is now more truthful than 014c because it no longer reports false success, but baseline still wins on actual recovery for no-commit workspaces`

## What Happened

- Got lost moments:
  - The workspace is inside a git work tree, but it has no commits yet: `git rev-parse --is-inside-work-tree` passed while `git rev-parse HEAD` failed.
  - `synrail save` still armed a pre-run snapshot, but the checkpoint record now honestly captured `workspace_snapshot.type = "none"` with the reason `project is not a git repository or has no commits`.
  - `synrail confirm-restore` still passed because the checkpoint record itself was structurally valid.
  - `synrail restore` no longer lied with a plain `RESTORED`; the restore trace recorded `RESTORE_FAILED`, `workspace_restored: false`, and an explicit failure reason saying workspace restore failed because the project is not a git repository or has no commits.
  - The file stayed `BROKEN` and tests stayed red, so actual recovery still did not happen on this contour.

## Verdict

- Verdict: Positive honesty fix, but not yet a recovery win. The false-green restore bug is now corrected: `Synrail` no longer claims success when it cannot restore the workspace. But the product still loses to baseline on no-commit workspaces because it cannot yet recover the broken file.

## Notes

- Hidden oracle result: baseline tests were green before mutation, broken tests were red after mutation, and remained red after restore because workspace recovery was unavailable.
- Most important product signal: the restore path now fails honestly with an explicit `workspace_snapshot.type = "none"` explanation instead of claiming a fake success.
- Most important remaining doubt: whether the next product move should be a file-copy fallback for non-git / no-commit workspaces, or a narrower restriction that clearly steers those contours away from restore.
