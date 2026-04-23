# Gemini Workflow

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

<!-- SYNRAIL_GEMINI_START -->
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

## Start

If Synrail shows that no controlled run is active, start one:

```bash
synrail start "Describe the bounded local change."
```

## Work

- Keep edits bounded and local to this repo.
- Run the local verification commands needed for the task before updating `.synrail/final_result.json`. Only materialize fallback prose surfaces later if Synrail explicitly targets them, and leave `cleanup_status` absent unless Synrail later asks for cleanup attestation.
- Keep proof explicit in the cheapest honest order: make final_result carry trust-bearing status plus patch or structured diff provenance first; treat readback and scenario proof as fallback-only surfaces and do not touch them unless Synrail explicitly targets them or final_result cannot yet carry strong structured verification.

## Finish

Before claiming success, run:

```bash
synrail check
```

If non-green, fix only what check tells you to fix, then rerun `synrail check`.

Do not bypass Synrail and do not claim success without real local verification.
- Keep repo instructions portable: prefer `synrail` in commands and committed docs.
- If `synrail` from PATH is unavailable in this checkout, try a local wrapper like `./.venv/bin/synrail` before assuming the control tool is missing.
- If this repo exposes a local alpha entrypoint at `alpha.py`, use `python3 alpha.py` as the next checkout-local fallback instead of reverse-engineering the entrypoint from setup metadata.
<!-- SYNRAIL_GEMINI_END -->
