# Alpha External Run 030

- Tester: Codex
- Agent: Gemini CLI
- Task: Please make a very small change in this project: add a one-line docstring to the main function in `alpha.py`. Do not change anything else. Then verify locally that the docstring is really there, and finish the task as correctly as you can in the current workflow. At the end briefly say which files you changed, how you checked it, what final status you reached, and if you did not finish, what blocker remained.
- Project: `synrail` fresh remote workspace from current build `94c50ae`, reusing the prior working `.venv` from the unattended Gemini lane
- Task class:
  - `trivial / additive_change`
- Start time: `2026-04-19T06:28:41Z`
- End time: `2026-04-19T06:29:54Z`
- Elapsed minutes: `1.2`
- Check iterations: `2`
- Final outcome: `CLOSURE_ACCEPTED_WITH_ENTRYPOINT_ARCHAEOLOGY_REMOVED_BUT_REGRESSED_CHEAPNESS`
- Failure owner:
  - `mixed`
- Reuse tomorrow:
  - `yes`
- Wedge fit:
  - `medium`

## Baseline Delta

- Baseline minutes estimate: `0.3`
- Synrail minutes actual: `1.2`
- Delta time: `+0.9`
- Baseline retry count estimate: `0`
- Synrail check count: `2`
- Delta loops: `+2`
- Baseline restore path: `n/a`
- Synrail restore path: `n/a`
- Delta recovery: `n/a`

## What Happened

- Got lost moments:
  - The new checkout-local fallback guidance changed the entry sequence in the intended direction.
  - Gemini still hit the same host-level `synrail` failure first, but it no longer reverse-engineered the entrypoint through `setup.py` or `python3 alpha.py`.
  - Instead, it moved straight to the local wrapper idea and started the governed run from there.
  - The trust path still stayed strong:
    - `final_result.status = "PROVEN"`
    - `normalized_method = "direct_file_observation"`
    - `readback_waived = true`
    - `scenario_waived = true`
  - But the overall lane did not get cheaper:
    - elapsed stayed effectively flat against `029` (`73s` vs `72s`)
    - Gemini re-authored `readback.txt` and `scenario_proof.txt` again even though the bundle did not need them for trust
    - and it fell into a cleanup mini-loop (`check -> explain-proof -> doctor -> check`) before reaching `Accepted`
  - So this run improves the diagnosis more than the headline:
    - entrypoint archaeology is no longer the main trivial-lane tax on this host
    - the next cost seam is now cleanup/second-check behavior plus unstable optional-prose skipping

## Verdict

- Verdict: mixed positive evidence. `030` confirms that the new fallback guidance removes the old `setup.py` / `python3 alpha.py` archaeology, but it does not yet translate into a faster or cleaner trivial lane because the agent still re-authors optional prose and burns a second check through cleanup handling.

## Notes

- Hidden oracle result: `n/a`
- Most important product signal: entrypoint discovery is no longer the dominant source of trivial-lane friction on the unattended Gemini host.
- Most important remaining doubt: the lane still has no clear baseline win because cleanup/doctor churn and optional-prose instability can eat the entrypoint savings immediately.
