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
- Update the starter proof files in `.synrail/` as the change becomes real.
- Run the local verification commands needed for the task.

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

## Agent Execution Rules

- **Simplicity First** — Prefer the smallest change that solves the actual problem. Do not add layers, abstractions, or fallback behavior unless runtime truth requires them.
- **Surgical Changes** — Keep changes tightly bounded to the task. Avoid opportunistic refactors, broad renames, or unrelated cleanup.
- **Goal-Driven Execution** — Before non-trivial work, state the concrete verification target in one sentence.
- **Assume Only When Cheap** — If ambiguity would materially change the implementation, ask. Otherwise state the assumption briefly and proceed.
- **Read Real Files First** — Do not guess file names, tests, classes, commands, or symbols.
- **No Blind Retry Loops** — After one or two failed retries, switch to root-cause investigation.
- **Verification Over Motion** — Prefer runtime-backed or test-backed verification over prose confidence.
- **Update Roadmap With Reality** — If shipped capability, benchmark posture, or roadmap truth changes, update the relevant roadmap or review markdown in the same change.

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
<!-- SYNRAIL_CLAUDE_END -->
