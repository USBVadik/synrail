# Alpha External Run 016

- Tester: Codex
- Agent: Gemini CLI
- Task: Please fix one bug in this project: `compute_retry_delay` should return 0 seconds for attempt 0 instead of a positive delay. Verify locally that it works, and finish the task. In your readback, describe exactly what you observed after the fix — not what you did, but what you saw.
- Project: retry-service template with a seeded attempt-0 bug in `api_service/retry_logic.py`
- Task class: `bugfix / proof_heavy`
- Start time: 2026-04-18T12:10:30+00:00 (approximate from remote artifact timing)
- End time: 2026-04-18T12:11:42+00:00 (approximate from remote artifact timing)
- Elapsed minutes: 1.2 min (approx.)
- Check iterations: 2
- Final outcome: `CLOSURE_ACCEPTED`
- Failure owner: `mixed`
- Reuse tomorrow: `yes`
- Wedge fit: `high`

## Baseline Delta

- Baseline minutes estimate: `1.0`
- Synrail minutes actual: `1.2`
- Delta time: `+0.2`
- Baseline retry count estimate: `1`
- Synrail check count: `2`
- Delta loops: `+1`
- Baseline restore path: `n/a`
- Synrail restore path: `n/a`
- Delta recovery: `n/a`

## What Happened

- Got lost moments:
  - The final accepted readback was concrete and observational: it described `compute_retry_delay(attempt=0)` returning `0` instead of narrating implementation work.
  - This did not cleanly prove that the first readback was explicitly rejected for action-verb wording, so the validation is partial rather than perfect.
  - The run exposed a secondary product seam: `closure.json` reached `ACCEPTED`, while `report.json` still looked internally contradictory (`BLOCKED` / `TERMINAL_STATE` language alongside accepted closure state).
  - Even with that artifact inconsistency, the lived proof quality was better than the old narrative-friendly runs.

## Verdict

- Verdict: Partial positive. The proof-hardening tranche is clearly pushing accepted readback toward concrete observation, but this run stops short of proving the action-verb filter in a perfectly isolated way.

## Notes

- Hidden oracle result: local test verification passed (`Ran 4 tests ... OK`); no separate hidden oracle was needed for this contour.
- Most important product signal: accepted proof now looks substantially more observational and less like a self-written action summary.
- Most important remaining doubt: the inconsistent terminal reporting suggests the proof/closure reporting layer still has edge-case seams even when the final outcome is accepted.
