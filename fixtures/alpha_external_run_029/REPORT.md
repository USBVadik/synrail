# Alpha External Run 029

- Tester: Codex
- Agent: Gemini CLI
- Task: Please make a very small change in this project: add a one-line docstring to the main function in `alpha.py`. Do not change anything else. Then verify locally that the docstring is really there, and finish the task as correctly as you can in the current workflow. At the end briefly say which files you changed, how you checked it, what final status you reached, and if you did not finish, what blocker remained.
- Project: `synrail` fresh remote workspace from current build `5b0b467`, reusing the prior working `.venv` from the unattended Gemini lane
- Task class:
  - `trivial / additive_change`
- Start time: `2026-04-18T22:30:10Z`
- End time: `2026-04-18T22:31:22Z`
- Elapsed minutes: `1.2`
- Check iterations: `1`
- Final outcome: `CLOSURE_ACCEPTED_WITH_STARTER_PROSE_LEFT_UNTOUCHED`
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
- Synrail check count: `1`
- Delta loops: `+1`
- Baseline restore path: `n/a`
- Synrail restore path: `n/a`
- Delta recovery: `n/a`

## What Happened

- Got lost moments:
  - Gemini again reached `Accepted` in one pass on the unattended lane with `final_result.status = "PROVEN"`.
  - The runtime-backed contour stayed strong:
    - `normalized_method = "direct_file_observation"`
    - `runtime_verification_sufficient = true`
    - `readback_waived = true`
    - `scenario_waived = true`
  - This is the first live run where the agent also leaves the starter prose surfaces untouched:
    - `readback_unchanged = true`
    - `scenario_unchanged = true`
  - The raw artifacts confirm the product meaning of that signal:
    - `readback.txt` still contains the starter note telling the agent to leave it alone unless `synrail check` asks for it
    - `scenario_proof.txt` also remains in its starter form
  - So `029` is stronger than `027`: the prose files are not only semantically waived, they are operationally skipped by the live agent.

## Verdict

- Verdict: strong positive evidence. `029` is the first unattended Gemini trivial run where `Synrail` both semantically waives the prose proof surfaces and causes the agent to leave them untouched in practice.

## Notes

- Hidden oracle result: `n/a`
- Most important product signal: the cheapened evidence-first contour now changes agent behavior, not just bundle semantics.
- Most important remaining doubt: the lane is still not a clean baseline win on time, even though the trust path is now much cheaper in substance.
