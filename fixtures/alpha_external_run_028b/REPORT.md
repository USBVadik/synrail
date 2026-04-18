# Alpha External Run 028b

- Tester: Codex
- Agent: Gemini CLI
- Task: Please make a very small change in this project: add a one-line docstring to the main function in `alpha.py`. Do not change anything else. Then verify locally that the docstring is really there, and finish the task as correctly as you can in the current workflow. At the end briefly say which files you changed, how you checked it, what final status you reached, and if you did not finish, what blocker remained.
- Project: `synrail` fresh remote workspace from current build `8202bf2`, reusing the prior working `.venv` from the unattended Gemini lane
- Task class:
  - `trivial / additive_change`
- Start time: `2026-04-18T21:50:47Z`
- End time: `2026-04-18T21:51:38Z`
- Elapsed minutes: `0.9`
- Check iterations: `1`
- Final outcome: `CLOSURE_ACCEPTED_WITH_FINAL_RESULT_FIRST_BUT_PROSE_STILL_AUTHORED`
- Failure owner:
  - `mixed`
- Reuse tomorrow:
  - `yes`
- Wedge fit:
  - `medium`

## Baseline Delta

- Baseline minutes estimate: `0.3`
- Synrail minutes actual: `0.9`
- Delta time: `+0.6`
- Baseline retry count estimate: `0`
- Synrail check count: `1`
- Delta loops: `+1`
- Baseline restore path: `n/a`
- Synrail restore path: `n/a`
- Delta recovery: `n/a`

## What Happened

- Got lost moments:
  - Gemini again reached `Accepted` in one pass on the unattended lane with `final_result.status = "PROVEN"`.
  - The new final-result-first guidance did change the agent's ordering: the live trace shows Gemini reading and strengthening `.synrail/final_result.json` before updating the prose proof surfaces.
  - The accepted bundle stayed on the strong runtime-backed contour:
    - `normalized_method = "direct_file_observation"`
    - `runtime_verification_sufficient = true`
    - `readback_waived = true`
    - `scenario_waived = true`
  - But the agent still edited both prose surfaces out of habit:
    - `readback_unchanged = false`
    - `scenario_unchanged = false`
  - So this run is a real cheapening step, but not the final one: the trust decision already lives in `final_result.json`, yet Gemini still spends extra effort on `readback.txt` and `scenario_proof.txt`.

## Verdict

- Verdict: useful mixed-positive evidence. `028b` proves that final-result-first guidance changes the live agent's ordering and preserves the waived runtime-backed contour, but it does not yet remove the extra prose work.

## Notes

- Hidden oracle result: `n/a`
- Most important product signal: the live agent now treats `final_result.json` as the primary proof surface before touching the prose files.
- Most important remaining doubt: Gemini still rewrites `readback/scenario` even though the bundle no longer needs them to carry trust.
