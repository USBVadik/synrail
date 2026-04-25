# Alpha External Run 011

- Tester: Codex
- Agent: Codex manual restore probe
- Task: `synrail start` -> `synrail save` -> intentionally break the target file -> `synrail restore`.
- Project: retry-service template (`/root/alpha_retry_service_template`)
- Task class: `restore`
- Start time: 2026-04-18T09:46:59+00:00
- End time: 2026-04-18T09:47:10+00:00 (approximate; run aborted after baseline validation failed)
- Elapsed minutes: 0.2 min
- Check iterations: 0
- Final outcome: `INVALID_BASELINE`
- Failure owner: `operator`
- Reuse tomorrow: `unclear`
- Wedge fit: `high`

## Baseline Delta

- Baseline minutes estimate: `n/a`
- Synrail minutes actual: `0.2`
- Delta time: `n/a`
- Baseline retry count estimate: `n/a`
- Synrail check count: `0`
- Delta loops: `n/a`
- Baseline restore path: `n/a`
- Synrail restore path: `n/a`
- Delta recovery: `n/a`

## What Happened

- Got lost moments:
  - This probe was started against `/root/alpha_retry_service_template`, but baseline validation immediately showed the template was already failing two retry tests before any `save` or deliberate break happened.
  - Because the baseline was not known-good, any restore result from this run would have been meaningless and would have contaminated the ledger.
  - `synrail start` itself was fine; the invalidity came from the operator choosing the wrong baseline template for the restore probe.

## Verdict

- Verdict: Invalid run. This should not be counted as evidence for or against the current restore fix. The right move is to rerun the restore probe from a known-good baseline and only then compare against run 007.

## Notes

- Hidden oracle result: baseline tests failed before the restore scenario began (`8 != 6` and `27 != 9` in the retry logic tests).
- Most important product signal: none yet; this run only tells us the protocol needs a known-good baseline before judging restore.
- Most important remaining doubt: restore still has not been re-evaluated honestly after the pre-run snapshot tranche because this attempt was invalid.
