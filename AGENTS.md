# Agent Workflow

This repo uses Synrail to keep one bounded local change inside one controlled run.

## Before You Edit

1. Start one controlled run before mutating code:
```bash
ARTIFACT_ROOT="$(pwd)/.synrail"
synrail start --artifact-root "$ARTIFACT_ROOT" --project-root "$(pwd)" --task-identity "Describe the bounded local change."
```

2. Keep the change local and bounded to the stated task.
3. Edit the starter proof files under `.synrail/` in place as the work becomes real.
4. Run the local commands needed to verify the change honestly.

## Before You Claim Success

```bash
synrail check --artifact-root "$ARTIFACT_ROOT"
```

If Synrail is non-green, run:

```bash
synrail repair-step --artifact-root "$ARTIFACT_ROOT"
```

Then repair only the named gap and re-check.

## Important

- Do not skip Synrail and try to legalize edits afterward.
- Do not claim success without real local verification.
- If `synrail` is unavailable on this machine, stop and report that the control tool is missing instead of bypassing it.
