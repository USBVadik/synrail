# Alpha External Run 017

- Tester: Codex
- Agent: Gemini CLI
- Task: Please fix one bug in this project: `compute_retry_delay` should raise `ValueError` for negative attempts instead of returning a fractional delay. Verify locally that the fix works. Finish the task as correctly as you can.
- Project: retry-service fixed template with a fresh negative-attempt bug contour
- Task class: `bugfix`
- Start time: 2026-04-18T12:20:19+00:00
- End time: 2026-04-18T12:21:20+00:00 (approximate from remote artifact/log timing; `end.txt` did not land)
- Elapsed minutes: 1.0 min (approx.)
- Check iterations: 1
- Final outcome: `CLOSURE_ACCEPTED`
- Failure owner: `none`
- Reuse tomorrow: `yes`
- Wedge fit: `high`

## Baseline Delta

- Baseline minutes estimate: `0.8`
- Synrail minutes actual: `1.0`
- Delta time: `+0.2`
- Baseline retry count estimate: `1`
- Synrail check count: `1`
- Delta loops: `0`
- Baseline restore path: `n/a`
- Synrail restore path: `n/a`
- Delta recovery: `n/a`

## What Happened

- Got lost moments:
  - Gemini made the bounded code and test change directly, verified it with local unit tests, and reached accepted closure in a single check loop.
  - There was a late shell-confirmation warning in the headless harness after the accepted path had already landed, but it did not dominate the run or change the result.
  - Nothing in this run suggests trivial-task ceremony or restore semantics were the issue; this was a clean bounded bugfix contour.

## Verdict

- Verdict: Positive independent signal. This is another fresh accepted Gemini bugfix on a different contour, and it strengthens the claim that bounded bugfix closure is becoming repeatable rather than one-off.

## Notes

- Hidden oracle result: local unit tests passed (`Ran 4 tests ... OK`).
- Most important product signal: one-check accepted closure on a distinct bugfix contour is a strong sign that the current proof/closure path is credible on the intended wedge.
- Most important remaining doubt: proof is still not fully machine-independent in untracked-template scenarios, even when the contour itself behaves well.
