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
