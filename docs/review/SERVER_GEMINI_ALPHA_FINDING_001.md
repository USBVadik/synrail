# Server Gemini Alpha Finding 001

## Summary

A live Gemini server run created the requested bounded docs file and reached `Status: Accepted`, but the CLI output also surfaced a `PATH_SCOPE_VIOLATION` error and doctor overrides.
This should not be treated as a clean successful alpha run.

## What worked

- Synrail was installed on the server.
- The false-green demo ran.
- `tests.test_install_smoke` passed.
- Gemini created `docs/review/SERVER_GEMINI_ALPHA_SMOKE_001.md` during the attempted live task.
- The verification command confirmed the expected line:
  `grep -n "Synrail server install was checked" docs/review/SERVER_GEMINI_ALPHA_SMOKE_001.md`

## What failed or confused the workflow

- `~/bin/synrail check --artifact-root ./.synrail` printed `PATH_SCOPE_VIOLATION`.
- The same output later printed `Status: Accepted`.
- The run used doctor overrides:
  - `clean_execution_surface`
  - `prompt_task_identity`
- A `git diff` verification attempt used an absolute `/root/docs/...` path outside `/root/synrail_repo`.

## Additional boundary finding

The first attempt to record this finding was written outside the repository at:

`/root/docs/review/SERVER_GEMINI_ALPHA_FINDING_001.md`

The canonical repo copy is now:

`docs/review/SERVER_GEMINI_ALPHA_FINDING_001.md`

This reinforces the alpha finding: Gemini/server workflows need stronger repo-root and repo-relative path guidance.

## Why this matters

A public CLI path should not mix a path-scope diagnostic and accepted closure in the same user-facing result without a clearer explanation.
This can confuse agents and operators about whether the run is genuinely clean.

## Current interpretation

This is a useful alpha integration finding, not a clean success case.

## Suggested follow-up

- Reproduce the `PATH_SCOPE_VIOLATION` on a fresh run.
- Check why `--target-path` resolved to `/root`.
- Ensure user-facing output distinguishes advisory diagnostics from blocking errors.
- Improve Gemini/server workflow guidance around repo-relative paths and `git diff`.

## Resolution (2026-07-12)

A fresh single-process reproduction confirmed that an out-of-root `--target-path` itself exits with code 2 before doctor, proof, or closure evaluation. However, an adversarial follow-up reproduced the underlying mixed-output class with another spine-owned path field: after a prior accepted check, an out-of-root `--coverage-profile-file` produced `PATH_SCOPE_VIOLATION`, then reused the stale accepted report, printed `Status: Accepted`, and exited 0. The finding was therefore a real fail-open output bug even though the exact historical command boundary cannot be reconstructed from the aggregated server transcript.

The bug is now closed without weakening path policy:

- default `check` output renders `Status: Blocked` and `Blocking diagnostic: PATH_SCOPE_VIOLATION` on stderr;
- machine-readable stdout remains one JSON object and now states `severity: BLOCKING`, `accepted: false`, and `closure_evaluated: false`;
- CLI and spine use one canonical orchestration path-scope map, so spine-owned paths are prevalidated by the public command;
- a new orchestration removes the previous derived `report.json`, so a failed child cannot reuse stale accepted output;
- the bounded next step distinguishes target/project-root repair from artifact-root repair;
- `--mode dev` preserves the machine-only JSON path;
- README, first-run guidance, and generated agent policy explicitly forbid combining a blocked invocation with a later command's accepted result.

Doctor overrides remain advisory warnings. They are not permitted to downgrade or bypass a path-scope violation.
