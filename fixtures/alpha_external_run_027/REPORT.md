# Alpha External Run 027

- Tester: Codex
- Agent: Gemini CLI
- Task: Please make a very small change in this project: add a one-line docstring to the main function in `alpha.py`. Do not change anything else. Then verify locally that the docstring is really there, and finish the task as correctly as you can in the current workflow. At the end briefly say which files you changed, how you checked it, what final status you reached, and if you did not finish, what blocker remained.
- Project: `synrail` fresh remote workspace from current build `1ea47d4`, reusing the prior working `.venv` from the unattended Gemini lane
- Task class:
  - `trivial / additive_change`
- Start time: `2026-04-18T21:25:31Z`
- End time: `2026-04-18T21:25:56Z` (`closure.json` server mtime; post-run finalizer again did not persist `end.txt`)
- Elapsed minutes: `0.4`
- Check iterations: `1`
- Final outcome: `CLOSURE_ACCEPTED_WITH_WAIVER_REALIZED`
- Failure owner:
  - `mixed`
- Reuse tomorrow:
  - `yes`
- Wedge fit:
  - `medium`

## Baseline Delta

- Baseline minutes estimate: `0.3`
- Synrail minutes actual: `0.4`
- Delta time: `+0.1`
- Baseline retry count estimate: `0`
- Synrail check count: `1`
- Delta loops: `+1`
- Baseline restore path: `n/a`
- Synrail restore path: `n/a`
- Delta recovery: `n/a`

## What Happened

- Got lost moments:
  - Gemini again reached accepted closure on the unattended lane with `final_result.status = "PROVEN"`.
  - This is the first live run where the waiver contour is actually realized in `bundle.json`:
    - `runtime_verification_sufficient = true`
    - `has_structured_runtime_verification = true`
    - `readback.waived_by_runtime_corroboration = true`
    - `scenario_proof.waived_by_runtime_corroboration = true`
  - The accepted proof stayed on the stronger direct-observation path:
    - `diff_provenance.method = "direct_file_observation"`
    - exact `added_line`
    - stable `context_before/context_after`
    - local runtime verification command and observed output
  - The run still created `readback.txt` and `scenario_proof.txt`, but the important semantic change is that they no longer carried the trust decision. `bundle.json` explicitly treats them as explanatory rather than blocking.
  - The lane stayed cheap:
    - `1` check
    - `0` repairs
    - `0` rejections
    - about `0.4` minutes total
  - Small seams still remain:
    - Gemini still spent time orienting on the executable path instead of immediately using the intended `synrail` binary.
    - Post-run finalization on the server still did not flush `summary/raw` automatically; artifacts had to be copied from the workspace again.

## Verdict

- Verdict: strong positive evidence. `027` is the first unattended Gemini trivial run where the evidence-first kernel path is not just available but semantically realized: runtime-backed proof closes the trust decision, and the prose proof surfaces are present only as waived explanatory artifacts.

## Notes

- Hidden oracle result: `n/a`
- Most important product signal: this is the first live proof that `Synrail` can make `readback/scenario` non-blocking on a real agent run while still reaching `Accepted` cheaply.
- Most important remaining doubt: the lane is now near-baseline rather than clearly better-than-baseline, and the agent still writes extra proof files even though the kernel no longer needs them for trust.
