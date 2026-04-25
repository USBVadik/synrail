# Alpha External Run 024

- Tester: Codex
- Agent: Gemini CLI
- Task: Please make a very small change in this project: add a one-line docstring to the main function in `alpha.py`. Do not change anything else. Then verify locally that the docstring is really there, and finish the task as correctly as you can in the current workflow. At the end briefly say which files you changed, how you checked it, what final status you reached, and if you did not finish, what blocker remained.
- Project: `synrail` fresh remote workspace from current build `db192c4`, reusing the prior working `.venv` from the unattended Gemini lane
- Task class:
  - `trivial / additive_change`
- Start time: `2026-04-18T20:41:57Z`
- End time: `2026-04-18T20:42:55Z` (`closure.json` server mtime; post-run finalizer did not persist `end.txt`)
- Elapsed minutes: `1.0`
- Check iterations: `2`
- Final outcome: `CLOSURE_ACCEPTED_WITH_PROVEN_STATUS_BUT_STILL_NO_WAIVER`
- Failure owner:
  - `mixed`
- Reuse tomorrow:
  - `unclear`
- Wedge fit:
  - `low`

## Baseline Delta

- Baseline minutes estimate: `0.3`
- Synrail minutes actual: `1.0`
- Delta time: `+0.7`
- Baseline retry count estimate: `0`
- Synrail check count: `2`
- Delta loops: `+2`
- Baseline restore path: `n/a`
- Synrail restore path: `n/a`
- Delta recovery: `n/a`

## What Happened

- Got lost moments:
  - Gemini again reached accepted closure on the unattended lane and emitted `final_result.status = "PROVEN"`.
  - This is the first live run after the `db192c4` tranche that can infer `diff_provenance.method` from a sufficiently strong direct-observation record.
  - The run still did **not** realize the waiver contour: `bundle.json` records `normalized_method = ""`, `method_inferred = false`, `readback.waived_by_runtime_corroboration = false`, and `scenario_proof.waived_by_runtime_corroboration = false`.
  - The important refinement is that the remaining gap is no longer just a missing `method` token. Gemini still authored only a thin direct-observation record in `final_result.json`: `changed_file`, `verification_command`, and `verification_result`, but no `added_line`, `removed_line`, `context_before`, or `context_after`.
  - Because that structured provenance record stayed too thin, the agent again wrote both `readback.txt` and `scenario_proof.txt`, and the run needed a second `synrail check` after one repair attempt.
  - Two harness seams remained visible: Gemini again hit a bare `synrail` permission problem before recovering to the workspace binary path, and the normal `read_file` tool still could not read `.synrail/final_result.json`, forcing a shell `cat` fallback.
  - Compared with `023`, this is still a useful result: the new kernel tranche did not break the live unattended Gemini lane, but it also showed that the next missing piece is stronger agent-side direct-observation shaping rather than another kernel waiver rule.

## Verdict

- Verdict: mixed-positive evidence. The live unattended Gemini lane still survives the newer evidence-first kernel build and still closes honestly with `PROVEN`, but the intended cheapening still does not materialize automatically because the agent does not yet author a sufficiently rich structured direct-observation record to trigger the waiver path.

## Notes

- Hidden oracle result: `n/a`
- Most important product signal: the latest kernel tranche is safe on a real unattended Gemini contour and the remaining waiver gap is now more precisely localized to live provenance shape, not to a missing trust-bearing status or a missing kernel affordance.
- Most important remaining doubt: trivial-task cost is still above baseline and the live agent is still paying prose-proof tax because its direct-observation record remains too thin to waive `readback` and `scenario_proof`.
