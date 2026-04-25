# Alpha External Run 011b

- Tester: Codex
- Agent: Codex manual restore probe
- Task: `synrail start` -> `synrail save` -> intentionally break the target file -> `synrail confirm-restore` -> `synrail restore`.
- Project: retry-service fixed template (`/root/alpha_retry_service_fixed_template`)
- Task class: `restore`
- Start time: 2026-04-18T10:05:10+00:00
- End time: 2026-04-18T10:05:11+00:00
- Elapsed minutes: 0.0 min (about 1 second; shell-driven manual probe)
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
- Synrail restore path: `save (fallback ready) -> confirm-restore -> restore`
- Delta recovery: `save is now materially better than run 007 because it arms a pre-run fallback, but restore still loses to baseline because the broken file remains broken after Synrail says RESTORED`

## What Happened

- Got lost moments:
  - The fixed template baseline was green, so this was finally a valid restore probe.
  - `synrail save` succeeded and explicitly reported `Fallback ready: working` with `Fallback type: Pre-run workspace snapshot`, which is real progress over run 007.
  - `synrail confirm-restore` immediately contradicted that success by saying it could not find a restore point to confirm.
  - `synrail restore` then reported `RESTORED`, but the broken retry logic stayed broken and all three tests still failed afterwards.

## Verdict

- Verdict: Mixed but still net negative. The pre-run snapshot fix clearly improved the `save` side of the story, but the product still fails the actual wedge promise because a broken workspace stays broken after restore claims success. This is still a restore bug, just a more precise one than run 007 exposed.

## Notes

- Hidden oracle result: baseline tests were green before mutation, broken tests were red after mutation, and restored tests stayed red after `synrail restore`.
- Most important product signal: pre-run snapshot arming is now real, but restore application and restore-point accounting are still inconsistent.
- Most important remaining doubt: we still need to know whether the bug lives in snapshot materialization, snapshot lookup, or the actual file-restore step.
