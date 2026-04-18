# Alpha External Run 014

- Tester: Codex
- Agent: Codex manual restore probe
- Task: `synrail start` -> `synrail save` -> intentionally break the target file -> `synrail confirm-restore` -> `synrail restore` -> rerun local tests.
- Project: retry-service fixed template (`/root/alpha_retry_service_fixed_template`)
- Task class: `restore`
- Start time: 2026-04-18T12:00:46+00:00
- End time: 2026-04-18T12:00:48+00:00
- Elapsed minutes: 0.0 min (about 2 seconds; shell-driven manual probe)
- Check iterations: 0
- Final outcome: `RESTORE_REPORTED_BUT_STATE_NOT_RECOVERED`
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
- Delta recovery: `baseline still wins because Synrail can arm a snapshot but still cannot actually recover the broken file after restore reports success`

## What Happened

- Got lost moments:
  - The baseline was finally clean and green before mutation, so this was a valid restore round-trip rather than another invalid setup.
  - `synrail save` now clearly armed a fallback and reported `Fallback type: Pre-run workspace snapshot`, which confirms the pre-run save tranche is real.
  - `synrail confirm-restore` still said it could not find a restore point to confirm.
  - `synrail restore` then reported `RESTORED`, but `api_service/retry_logic.py` still contained literal `BROKEN` and the restored tests stayed red.

## Verdict

- Verdict: Strong negative confirmation. This run does not reverse the old restore failure; it sharpens it. `save` is now better than before, but the actual restore promise is still broken because lookup/accounting and workspace application do not line up.

## Notes

- Hidden oracle result: baseline unit tests were green before mutation, intentionally broken tests were red after mutation, and post-restore tests were still red.
- Most important product signal: pre-run snapshot arming is real now, but restore lookup/application is still not trustworthy.
- Most important remaining doubt: whether the remaining bug is primarily in restore-point discovery, snapshot materialization, or the final file-apply step.
