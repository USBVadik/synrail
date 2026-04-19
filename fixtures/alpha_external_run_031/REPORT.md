# Alpha External Run 031

- Tester: Codex
- Agent: Gemini CLI
- Task: Please make a very small change in this project: add a one-line docstring to the main function in `alpha.py`. Do not change anything else. Then verify locally that the docstring is really there, and finish the task as correctly as you can in the current workflow. At the end briefly say which files you changed, how you checked it, what final status you reached, and if you did not finish, what blocker remained.
- Project: `synrail` fresh remote workspace from current build `a08a2ee`, reusing the prior working `.venv` from the unattended Gemini lane
- Task class:
  - `trivial / additive_change`
- Start time: `2026-04-19T06:42:38Z`
- End time: `2026-04-19T06:43:33Z`
- Elapsed minutes: `0.9`
- Check iterations: `1`
- Final outcome: `CLOSURE_ACCEPTED_WITH_SECOND_CHECK_REMOVED_BUT_PROSE_STILL_AUTHORED`
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
  - The new cleanup-status-absent starter guidance removed the second-check seam that showed up in `030`.
  - Gemini again used the local checkout entrypoint directly after the host-level `synrail` failure instead of reverse-engineering through `setup.py` or `python3 alpha.py`.
  - This time the run reached `Accepted` after a single `synrail check`, with no `explain-proof -> doctor -> check` detour.
  - Elapsed time dropped from `73s` in `030` to `55s` here.
  - The proof path stayed strong:
    - `final_result.status = "PROVEN"`
    - `normalized_method = "direct_file_observation"`
    - `method_inferred = true`
    - `readback_waived = true`
    - `scenario_waived = true`
  - But the lane is still not yet cheap enough:
    - Gemini still authored `cleanup_status` manually instead of relying on doctor fallback
    - and it still rewrote `readback.txt` and `scenario_proof.txt` even though the bundle did not need those files for trust

## Verdict

- Verdict: strong mixed-positive evidence. `031` shows that removing the controlled-run cleanup placeholder really does cut out the old second-check/doctor churn, but the remaining trivial-lane tax still comes from agent habit around manually filling optional proof surfaces.

## Notes

- Hidden oracle result: `n/a`
- Most important product signal: the cleanup-placeholder seam was real and removing it made the unattended Gemini trivial lane materially faster.
- Most important remaining doubt: the lane still does not beat baseline because the agent keeps doing unnecessary prose and cleanup authorship after the trust path is already sufficient.
