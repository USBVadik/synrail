# Hetzner Live Comparison 2026-04-21

## Scope

This note compares the same tiny `tools/reference` docstring contour on the same Hetzner host (`49.13.140.183`) using the current pushed branch build `8967d8f`.

Compared runs:

- Gemini main run: [alpha_external_run_032](../../fixtures/alpha_external_run_032/REPORT.md)
- Claude blocked run: [alpha_external_run_033](../../fixtures/alpha_external_run_033/REPORT.md)
- Claude diagnostic trace: [alpha_external_run_034](../../fixtures/alpha_external_run_034/REPORT.md)
- Claude harness-valid rerun: [alpha_external_run_035](../../fixtures/alpha_external_run_035/REPORT.md)

Task shape:

- add a one-line docstring to `repo_root_from_script` in `tools/reference/synrail_install_v0.py`
- do not change anything else
- verify locally
- finish the task in the current `Synrail` workflow if possible

## Bottom Line

- `Gemini 032` and `Claude 035` both reach governed accepted closure on the same tiny current-branch contour.
- The earlier Claude failure was real, but it was a harness issue:
  - under the default root-host non-interactive shape, Claude could edit code but could not execute the checkout-local `synrail` wrapper
  - once that wrapper path was pre-approved in `allowedTools`, Claude reached the same cheapened governed path
- So the updated current difference is not product quality. It is harness ergonomics:
  - Gemini is already harness-valid by default on this lane
  - Claude currently needs wrapper-path pre-approval to become harness-valid on this host

## Gemini 032

- Outcome: `CLOSURE_ACCEPTED`
- `final_result.status = PROVEN`
- optional prose surfaces absent
- no manual cleanup authorship needed
- accepted closure was real
- later blocked state was caused by post-run operator re-check and should not count against the run

This is strong positive product evidence for the cheapened proof path.

## Claude 033

- Outcome: `GOVERNED_FINISH_BLOCKED_BY_PERMISSION_GATE`
- code change landed correctly
- file verification happened
- no `.synrail` directory or closure artifacts were produced
- Claude itself reported that `synrail start` / `synrail check` were blocked by approval denial

This is useful negative **harness** evidence, not product evidence against the branch.

## Claude 034

- Outcome: `HARNESS_PERMISSION_DENIAL_CONFIRMED`
- same tiny contour rerun with `stream-json` output
- tool trace captured explicit `permission_denials` on:
  - `/root/alpha_external_run_034/workspace/.venv/bin/synrail 2>&1 | head -40`
  - `/root/alpha_external_run_034/workspace/.venv/bin/synrail`

This confirms the blocker cause instead of leaving it as agent narrative.

## Claude 035

- Outcome: `CLOSURE_ACCEPTED`
- same tiny contour again
- same host
- same branch
- but now with pre-approved wrapper path in `allowedTools`
- Claude successfully:
  - read the local dashboard
  - started a controlled run
  - edited the file
  - updated `final_result.json`
  - ran `synrail check`
  - reached accepted closure
- optional prose surfaces absent
- `cleanup_status` absent
- final status green under `synrail check`

This is strong positive product evidence and closes the earlier ambiguity about whether Claude could follow the cheapened governed path at all on this host.

## Practical Reading

What improved:

- the branch now clearly supports a live cheapened trivial lane on both agents
- the accepted contour is not Gemini-only anymore
- Claude can traverse the same governed path once the wrapper permission seam is removed

What did not improve yet:

- Claude's default non-interactive root-host ergonomics are still worse than Gemini's on this machine
- so the remaining issue is not proof semantics here, but how boring the wrapper-based first loop is under Claude's host policy

## Most Honest Verdict

- Better than before on live cheapened proof behavior: `yes`, clearly.
- Better than before on cross-agent comparability: `yes`.
- Evidence of a new product regression in `Synrail` itself: `no`.
- Evidence of a still-open Claude host-harness seam: `yes`, but now it is narrowed and well-understood.
