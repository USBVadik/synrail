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
- Update the starter proof files in `.synrail/` as the change becomes real.
- Run the local verification commands needed for the task.

## Finish

```bash
synrail check
```

If non-green, fix only what check tells you to fix, then rerun `synrail check`.

Do not bypass Synrail and do not claim success without real local verification.
