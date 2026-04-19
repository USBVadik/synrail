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
3. Edit the starter proof files under `.synrail/` in place as the work becomes real.
4. Run the local commands needed to verify the change honestly.

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

If Synrail shows that no controlled run is active, start one:

```bash
synrail start "Describe the bounded local change."
```

Before claiming success, run:

```bash
synrail check
```

If non-green, run `synrail repair-step` and repair only the named gap before re-checking.

Do not bypass Synrail and do not claim success without real local verification.
- Keep repo instructions portable: prefer `synrail` in commands and committed docs.
- If `synrail` from PATH is unavailable in this checkout, try a local wrapper like `./.venv/bin/synrail` before assuming the control tool is missing.
- If this repo exposes a local alpha entrypoint at `alpha.py`, use `python3 alpha.py` as the next checkout-local fallback instead of reverse-engineering the entrypoint from setup metadata.
<!-- SYNRAIL_AGENTS_END -->
