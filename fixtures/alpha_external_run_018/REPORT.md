# Alpha External Run 018

- Tester: Codex
- Agent: Gemini CLI + Gemini CLI
- Task: Session 1: start fixing the retry-delay cap bug, run `synrail check` once, and stop regardless of result. Session 2: continue from the current `.synrail` state, verify locally, and finish the run.
- Project: retry-service template with a cap-at-30-seconds handoff contour
- Task class: `handoff`
- Start time: 2026-04-18T12:23:30+00:00
- End time: 2026-04-18T12:25:20+00:00 (approximate from run id plus second-session artifact/log timing)
- Elapsed minutes: 1.8 min (approx.)
- Check iterations: 3
- Final outcome: `CLOSURE_ACCEPTED`
- Failure owner: `none`
- Reuse tomorrow: `yes`
- Wedge fit: `high`

## Baseline Delta

- Baseline minutes estimate: `2.0`
- Synrail minutes actual: `1.8`
- Delta time: `-0.2`
- Baseline retry count estimate: `3`
- Synrail check count: `3`
- Delta loops: `0`
- Baseline restore path: `n/a`
- Synrail restore path: `n/a`
- Delta recovery: `n/a`

## What Happened

- Got lost moments:
  - The first Gemini session left a real governed non-green state: code and tests looked good, but `synrail check` stopped on semantically insufficient readback.
  - That is exactly the kind of state handoff is supposed to preserve, because the second operator inherited a concrete proof-repair problem rather than vague chat memory.
  - The second Gemini session oriented on the existing `.synrail` artifacts, rewrote the readback with stronger verification detail, reran checks, and reached `Accepted`.
  - This was a cleaner product signal than the Claude-first handoff attempts, because harness approval noise did not dominate the lane.

## Verdict

- Verdict: Strong positive. This is now a second valid handoff success, and it reinforces that continuation/handoff honesty is currently the clearest wedge where `Synrail` looks materially stronger than baseline.

## Notes

- Hidden oracle result: second session confirmed local tests passing and hidden oracle passing before final accepted closure.
- Most important product signal: a second operator can inherit a semantically incomplete run, understand what remains, and close it without author memory.
- Most important remaining doubt: the handoff wedge is strong on Gemini-side evidence, but Claude-first handoff is still undercounted because the root/headless Claude harness remains noisy.
