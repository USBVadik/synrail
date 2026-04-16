# Gemini Workflow

Use Synrail as the default local control path for this repo.

## Start

Before editing code, start one controlled run:

```bash
ARTIFACT_ROOT="$(pwd)/.synrail"
synrail start --artifact-root "$ARTIFACT_ROOT" --project-root "$(pwd)" --task-identity "Describe the bounded local change."
```

## Work

- Keep edits bounded and local to this repo.
- Update the starter proof files in `.synrail/` as the change becomes real.
- Run the local verification commands needed for the task.

## Finish

```bash
synrail check --artifact-root "$ARTIFACT_ROOT"
```

If non-green, run `synrail repair-step --artifact-root "$ARTIFACT_ROOT"`, repair only the named gap, and re-check.

Do not bypass Synrail and do not claim success without real local verification.
