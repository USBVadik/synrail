# Agent Workflow

This repo uses Synrail to keep one bounded local change inside one controlled run.

## First Step On Every New Task

Run Synrail before deciding what to do next. It is a CLI control kernel, not a background daemon.
```bash
synrail
```

## Before You Edit

1. If Synrail shows that no controlled run is active, start one before mutating code:
```bash
synrail start "Describe the bounded local change."
```

2. Keep the change local and bounded to the stated task.
3. Run the local commands needed to verify the change honestly, then edit `.synrail/final_result.json` in place as the work becomes real. Only materialize `readback.txt` or `scenario_proof.txt` if Synrail explicitly targets them, and leave `cleanup_status` absent unless Synrail later asks for cleanup attestation.
4. Keep proof explicit in the cheapest honest order: make `final_result.json` carry trust-bearing status plus patch or structured diff provenance first.

## Before You Claim Success

```bash
synrail check
```

If Synrail is non-green, fix only what check tells you to fix, then rerun:

```bash
synrail check
```

## Important

- Do not skip Synrail and try to legalize edits afterward.
- Do not claim success without real local verification.
- If `synrail` is unavailable on this machine, stop and report that the control tool is missing instead of bypassing it.

<!-- SYNRAIL_AGENTS_START -->
## Synrail Local Workflow

This repo uses Synrail to keep one bounded local change inside one controlled run.

First command for every new task:

```bash
synrail
```

## Project Orientation

If the user asks what this project is, where work stopped, or what the current status is, treat that as a Synrail-guided orientation task too.

- Start with `synrail` before broader repo search.
- Stay inside this project root and prefer read-only inspection first.
- Summarize the governed state before exploring older files, sibling probes, or unrelated surfaces.
- Do not turn project recall into repo archaeology.
- Do not create helper scripts or make edits for an orientation-only question.

## Behavioral Verification Gate

Before starting any mutation run, inspect the operator-owned verification policy:

```bash
synrail preflight
```

Interpret the behavioral-verification status exactly:

- `READY`: start the run, then run the required profiles with `synrail verify` after the change and before `synrail check`.
- `NOT_CONFIGURED`: only a task that does not require behavioral acceptance may continue. Claims such as tests passing are not Synrail-gated; do not make or attribute them to Synrail. If behavior matters, report the missing gate and suggest that the operator run `synrail suggest-verification` outside the controlled run.
- `REVIEW_REQUIRED` or `BLOCKED`: do not start a mutation run. Follow only the named safe setup step or report the blocker.
- Any missing, malformed, or unrecognized status is blocking: do not start.

Treat `synrail.toml` as operator-owned policy. Do not create, edit, commit, weaken, or replace it unless the user explicitly asks to configure verification and no controlled run is active. Never change it during an active run to evade a failed profile.

When preflight reported `READY`, run behavioral verification before closure:

```bash
synrail verify
```

If verification fails, repair the behavior and rerun `synrail verify`. Do not replace a failing behavioral profile with `grep`, narrative proof, or another convenient read-only check. Any later code or config change makes prior verification stale, so rerun it before `synrail check`.

## Repo-Local Fallback

If this host blocks checkout-local wrappers behind approval or permission gates, use the repo-local alpha entrypoint directly:

```bash
python3 alpha.py
python3 alpha.py preflight
python3 alpha.py start "Describe the bounded local change."
python3 alpha.py verify
python3 alpha.py check
python3 alpha.py runtime-helper
```

Prefer these exact repo-local commands instead of probing wrapper paths with shell piping.

## Start

If Synrail shows that no controlled run is active, start one:

```bash
synrail start "Describe the bounded local change."
```

## Run Loop

```bash
synrail preflight --artifact-root ./.synrail
# continue on READY; NOT_CONFIGURED only for non-behavioral tasks
synrail start "TASK" --artifact-root ./.synrail
# make one bounded change and run the real local verification
synrail record path/to/file --summary "Describe the concrete bounded result." --verify "grep -n 'expected text' path/to/file"
# READY only: synrail verify --artifact-root ./.synrail
synrail check --artifact-root ./.synrail
# only stop on Status: Accepted
```

Use `record` only when the run started with a clean git worktree, `HEAD` did not change, and exactly one tracked regular file changed. For multi-file, untracked, deleted, no-op, no-git, pre-dirty, or revision-changing work, update `final_result.json` with complete structured proof instead. `record` never accepts the task; behavioral `verify` and final `check` remain separate gates.

## Work

- Keep edits bounded and local to this repo.
- For a clean-start change to exactly one tracked regular file, run the real local verification and use `synrail record path/to/file --summary "Describe the concrete bounded result." --verify "grep -n 'expected text' path/to/file"` to record recheckable proof without hand-authoring JSON.
- For every other contour, run the local verification commands needed for the task before updating `.synrail/final_result.json`. Only materialize fallback prose surfaces later if Synrail explicitly targets them, and leave `cleanup_status` absent unless Synrail later asks for cleanup attestation.
- Keep proof explicit in the cheapest honest order: make final_result carry trust-bearing status plus patch or structured diff provenance first; treat readback and scenario proof as fallback-only surfaces and do not touch them unless Synrail explicitly targets them or final_result cannot yet carry strong structured verification.
- If `git` is unavailable on this host, do not invent `git_diff`; leave it empty in `.synrail/final_result.json` and use structured provenance: `diff_provenance` for a single-file change, or `diff_provenance_records` / `per_file_diff_provenance` with one `changed_file`-backed record per modified file for a multi-file change. Each record should include one exact changed or observed line, a stable context anchor, `verification_command`, and `verification_result`.
- Keep `diff_provenance.verification_command` recheckable: use one repo-relative read-only command such as `grep -n`, `cat`, `head`, `tail`, `git diff -- <path>`, `git show -- <path>`, or `git log -- <path>`. Git recheck commands must use exactly `git diff/show/log -- <path>` with no `git -c`, `--ext-diff`, `--textconv`, or other options before `--`. Do not use pipes, `&&`, `sed`, `awk`, `perl`, subshells, or multi-command snippets there.
- Treat `PATH_SCOPE_VIOLATION` as blocking for that command: Synrail stopped before closure and did not accept the task. Fix the named path or `--project-root`, rerun `check` as a separate command, and never combine the blocked output with a later command's `Status: Accepted`.

## Finish

Before claiming success, run:

```bash
synrail check
```

If non-green, fix only what check tells you to fix, then rerun `synrail check`.

Do not bypass Synrail and do not claim success without real local verification.

## Non-Accepted Status Rule

Only `Status: Accepted` means the task may be reported as complete. If Synrail returns Proof Invalid, Rejected, Blocked, or any repair step, do not summarize the task as done; run the named repair step or report the exact Synrail blocker.
Do not say the task is functionally complete, 100% done, fully done, or all requirements met while Synrail is non-green.
If `synrail check` prints any other non-green status, report the exact Synrail status, follow only the named next command or repair target, and rerun Synrail until `Status: Accepted` appears.

- Keep repo instructions portable: prefer `synrail` in commands and committed docs.
- If `synrail` from PATH is unavailable in this checkout, try a local wrapper like `./.venv/bin/synrail` before assuming the control tool is missing.
- If this repo exposes a local alpha entrypoint at `alpha.py`, prefer `python3 alpha.py` as the repo-local fallback instead of reverse-engineering the entrypoint from setup metadata.
- If a checkout-local wrapper path itself triggers an agent approval or permission wall, switch immediately to the exact repo-local commands below before concluding Synrail cannot run on this host.
<!-- SYNRAIL_AGENTS_END -->
