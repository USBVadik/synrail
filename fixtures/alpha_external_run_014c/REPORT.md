# Alpha External Run 014c

- Tester: Codex
- Agent: Codex manual restore probe
- Task: Re-run the restore round-trip on the explicitly deployed current build with a correct local verification command and capture the restore trace.
- Project: retry-service fixed template (`/root/alpha_retry_service_fixed_template`)
- Task class: `restore`
- Start time: 2026-04-18T12:50:02+00:00
- End time: 2026-04-18T12:50:04+00:00
- Elapsed minutes: 0.0 min (about 2 seconds; shell-driven manual probe)
- Check iterations: 0
- Final outcome: `RESTORE_REPORTED_BUT_WORKSPACE_NOT_RESTORED`
- Failure owner: `product`
- Reuse tomorrow: `no`
- Wedge fit: `high`

## Baseline Delta

- Baseline minutes estimate: `0.3`
- Synrail minutes actual: `0.0`
- Delta time: `-0.3`
- Baseline retry count estimate: `0`
- Synrail check count: `0`
- Delta loops: `0`
- Baseline restore path: `manual revert of the changed file or copy back from the known-good baseline`
- Synrail restore path: `save (pre-run snapshot armed) -> confirm-restore -> restore`
- Delta recovery: `baseline still wins because Synrail now confirms the restore point correctly but still leaves the broken file in place after reporting RESTORED`

## What Happened

- Got lost moments:
  - This rerun used the correct baseline verification command: `PYTHONPATH=. python3 tests/test_retry_logic.py`, and baseline tests were green before mutation.
  - `synrail save` armed `Fallback type: Pre-run workspace snapshot`, which confirms the pre-run snapshot tranche is deployed.
  - `synrail confirm-restore` now passed, which confirms the earlier artifact-root/parser gap is fixed on the deployed build.
  - `synrail restore` still reported `RESTORED`, but `api_service/retry_logic.py` remained literal `BROKEN` and the post-restore tests stayed red.
  - The decisive trace is in `.synrail/checkpoint_restore.json`: `workspace_restored` is explicitly `false`, even though the overall restore result is `OK` / `RESTORED`.

## Verdict

- Verdict: Strong negative confirmation on the current deployed build. The parser/default-path fixes are real, but the actual restore promise is still broken because restore only replays Synrail state artifacts and does not restore the workspace file for this pre-run snapshot contour.

## Notes

- Hidden oracle result: baseline tests were green before mutation; broken tests were red after mutation; post-restore tests were still red.
- Most important product signal: restore is now instrumented enough to explain its own failure mode: `workspace_restored: false`.
- Most important remaining doubt: whether the remaining bug is a deliberate omission of workspace snapshot materialization for `PRE_RUN_SNAPSHOT`, or a narrower bug in how workspace restoration is gated/applied.
