# Alpha External Run 032

- Tester: Codex
- Agent: Gemini CLI
- Task: Please make a very small change in this project: add a one-line docstring to the `repo_root_from_script` function in `tools/reference/synrail_install_v0.py`. Do not change anything else. Then verify locally that the docstring is really there, and finish the task as correctly as you can in the current workflow. At the end briefly say which files you changed, how you checked it, what final status you reached, and if you did not finish, what blocker remained.
- Project: `synrail` fresh remote workspace from current pushed build `8967d8f`
- Task class:
  - `trivial / additive_change`
- Start time: `2026-04-21T17:48:23+00:00`
- End time: `2026-04-21T17:49:29+00:00` (from accepted `closure.json` mtime on the remote host)
- Elapsed minutes: `1.1`
- Check iterations: `1`
- Final outcome: `CLOSURE_ACCEPTED`
- Failure owner:
  - `none`
- Reuse tomorrow:
  - `unclear`
- Wedge fit:
  - `low`

## Baseline Delta

- Baseline minutes estimate: `0.3`
- Synrail minutes actual: `1.1`
- Delta time: `+0.8`
- Baseline retry count estimate: `0`
- Synrail check count: `1`
- Delta loops: `+1`
- Baseline restore path: `n/a`
- Synrail restore path: `n/a`
- Delta recovery: `n/a`

## What Happened

- Got lost moments:
  - Gemini again found the checkout-local entrypoint instead of getting stuck on a missing host-level `synrail` binary.
  - The proof path stayed materially cheaper than older mixed-positive trivial runs: `final_result.json` carried the trust path, `cleanup_status` came from doctor fallback, and neither `readback.txt` nor `scenario_proof.txt` was created.
  - The code change itself landed correctly: only `tools/reference/synrail_install_v0.py` changed, and the docstring is present in the expected function.
  - The accepted closure was real:
    - `closure.json` was last written at `17:49:29+00:00` with `closure_status = "ACCEPTED"`
    - Gemini's final text also reported `Accepted`
  - The later `DOCTOR_BLOCKED` state was created by operator follow-up, not by the agent run itself:
    - a manual post-run `synrail check` was executed after the accepted closure
    - that rerun happened on the already modified workspace without `--clean-surface`
    - it rewrote `state.json`, `report.json`, and `summary.txt` at `17:49:53+00:00`
  - So this run improves the cheapened proof behavior on a second trivial task shape. The apparent accepted-vs-blocked contradiction was measurement contamination from post-run operator inspection, not a product-side false acceptance.

## Verdict

- Verdict: positive moderate evidence. `032` extends the new cheapened proof behavior to a second trivial task shape: the agent used the local wrapper, reached accepted closure in one governed pass, left optional prose surfaces absent, and relied on doctor-derived cleanup truth instead of manually authoring extra proof files.

## Notes

- Hidden oracle result: `n/a`
- Most important product signal: the recent cheapening work is now visibly changing live agent behavior on more than one trivial contour, not just the original `alpha.py` docstring lane.
- Most important remaining doubt: the lane is still slower than baseline and still not operationally boring enough to call the trivial contour won overall.
- Important measurement note: the previously observed `DOCTOR_BLOCKED` state on this run was caused by a post-run operator re-check after acceptance and should not be counted as product evidence against the run itself.
