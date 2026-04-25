# Alpha External Run 014b

- Tester: Codex
- Agent: Codex manual restore probe
- Task: Re-run the restore round-trip on the explicitly deployed local tranche and capture raw `save` / `confirm-restore` / `restore` artifacts.
- Project: retry-service fixed template (`/root/alpha_retry_service_fixed_template`)
- Task class: `restore`
- Start time: 2026-04-18T12:49:00+00:00
- End time: 2026-04-18T12:49:02+00:00
- Elapsed minutes: 0.0 min (about 2 seconds; shell-driven manual probe)
- Check iterations: 0
- Final outcome: `PARTIAL_DIAGNOSTIC_ONLY`
- Failure owner: `operator`
- Reuse tomorrow: `unclear`
- Wedge fit: `high`

## Baseline Delta

- Baseline minutes estimate: `n/a`
- Synrail minutes actual: `0.0`
- Delta time: `n/a`
- Baseline retry count estimate: `n/a`
- Synrail check count: `0`
- Delta loops: `n/a`
- Baseline restore path: `n/a`
- Synrail restore path: `save -> confirm-restore -> restore`
- Delta recovery: `n/a`

## What Happened

- Got lost moments:
  - This rerun was useful as a parser/default-path diagnostic, not as a clean restore verdict.
  - `confirm-restore` now passed on the deployed build, which validates the parser/default artifact-root fix.
  - I used the wrong baseline test command in this rerun, so the baseline test step was already invalid before the deliberate break.
  - Even so, the file-level symptom still pointed in the same direction: after `restore`, `retry_logic.py` remained literal `BROKEN`.

## Verdict

- Verdict: Do not count this as the authoritative restore verdict. Keep it as a diagnostic bridge between `014` and `014c`: parser/default-path behavior improved, but the baseline verification path in this rerun was flawed.

## Notes

- Hidden oracle result: not applicable; this was a manual diagnostic rerun.
- Most important product signal: `confirm-restore` now passes on the deployed build.
- Most important remaining doubt: restore file application still looked broken, but the baseline test command in this rerun was not valid enough to close the case on its own.
