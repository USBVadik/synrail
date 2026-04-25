# Claude Workflow

Use Synrail as the default local control path for this repo.

## First Command

For every new user task, run Synrail first so you can see the current governed state:

```bash
synrail
```

Synrail is a CLI control kernel, not a background daemon.

## Start

If Synrail shows that no controlled run is active and the task needs edits, start one controlled run:

```bash
synrail start "Describe the bounded local change."
```

## Work

- Keep edits bounded and local to this repo.
- Run the local verification commands needed for the task before updating `.synrail/final_result.json`. Only materialize fallback prose surfaces later if Synrail explicitly targets them, and leave `cleanup_status` absent unless Synrail later asks for cleanup attestation.
- Keep proof explicit in the cheapest honest order: make final_result carry trust-bearing status plus patch or structured diff provenance first; treat readback and scenario proof as fallback-only surfaces and do not touch them unless Synrail explicitly targets them or final_result cannot yet carry strong structured verification.

## Finish

```bash
synrail check
```

If non-green, fix only what check tells you to fix, then rerun `synrail check`.

Do not bypass Synrail and do not claim success without real local verification.

<!-- SYNRAIL_CLAUDE_START -->
## Synrail Local Workflow

Use Synrail as the default local control path for this repo.

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

## Repo-Local Fallback

If this host blocks checkout-local wrappers behind approval or permission gates, use the repo-local alpha entrypoint directly:

```bash
python3 alpha.py
python3 alpha.py start "Describe the bounded local change."
python3 alpha.py check
```

Prefer these exact repo-local commands instead of probing wrapper paths with shell piping.

## Start

If Synrail shows that no controlled run is active, start one:

```bash
synrail start "Describe the bounded local change."
```

## Work

- Keep edits bounded and local to this repo.
- Run the local verification commands needed for the task before updating `.synrail/final_result.json`. Only materialize fallback prose surfaces later if Synrail explicitly targets them, and leave `cleanup_status` absent unless Synrail later asks for cleanup attestation.
- Keep proof explicit in the cheapest honest order: make final_result carry trust-bearing status plus patch or structured diff provenance first; treat readback and scenario proof as fallback-only surfaces and do not touch them unless Synrail explicitly targets them or final_result cannot yet carry strong structured verification.
- If `git` is unavailable on this host, do not invent `git_diff`; leave it empty in `.synrail/final_result.json` and fill structured `diff_provenance` with `changed_file`, one exact changed or observed line, a stable context anchor, `verification_command`, and `verification_result`.

## Finish

Before claiming success, run:

```bash
synrail check
```

If non-green, fix only what check tells you to fix, then rerun `synrail check`.

Do not bypass Synrail and do not claim success without real local verification.

## Non-Accepted Status Rule

Only `Status: Accepted` means the task may be reported as complete.
If `synrail check` prints `Proof Invalid`, `Proof Incomplete`, `Proof Too Thin To Trust`, `Workspace Not Ready`, `Workspace Not Trusted`, `Needs Review`, or any other non-green status, do not send a final success/completion answer.
Do not say the task is functionally complete, 100% done, fully done, or all requirements met while Synrail is non-green.
Instead report the exact Synrail status, follow only the named next command or repair target, and rerun Synrail until `Status: Accepted` appears.

- Keep repo instructions portable: prefer `synrail` in commands and committed docs.
- If `synrail` from PATH is unavailable in this checkout, try a local wrapper like `./.venv/bin/synrail` before assuming the control tool is missing.
- If this repo exposes a local alpha entrypoint at `alpha.py`, prefer `python3 alpha.py` as the repo-local fallback instead of reverse-engineering the entrypoint from setup metadata.
- If a checkout-local wrapper path itself triggers an agent approval or permission wall, switch immediately to the exact repo-local commands below before concluding Synrail cannot run on this host.
<!-- SYNRAIL_CLAUDE_END -->
