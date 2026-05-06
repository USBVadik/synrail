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
