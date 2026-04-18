# Your First Synrail Run

Synrail governs one bounded change at a time. It blocks false-green closure and tells you what to fix.

## Install

```bash
python3 tools/reference/synrail_install_v0.py --venv .venv
```

## Optional One-Time Repo Setup For Local Agents

If you want local coding agents to discover Synrail naturally in this repo, bootstrap the repo-native hints in one step:

```bash
python3 tools/reference/synrail_install_v0.py --venv .venv --project-root "$(pwd)"
```

This installs the current Synrail CLI into `.venv` and immediately creates missing `AGENTS.md` / `GEMINI.md` / `CLAUDE.md` files in the repo root or appends a managed Synrail block to existing ones. If you later rerun with `--force`, Synrail first writes a timestamped `.synrail.bak.*` backup of the existing policy file before replacing it. It is optional for humans, but useful when you want the local agent workflow to start in controlled mode without adding Synrail instructions to every prompt.

## Quick Status

Run this first in the repo:

```bash
synrail
```

Synrail is a CLI control kernel, not a background daemon. The dashboard tells you whether a controlled run is active and what the next command should be.

For open-ended questions like "what is this project?" or "where did we stop?", still start with `synrail` and keep the first pass read-only before broader repo exploration.

## Four Steps

### 1. Start a controlled run

```bash
synrail start "Describe the bounded change you are making."
```

This creates `.synrail/` with starter proof files: `final_result.json`, `readback.txt`, `scenario_proof.txt`.

### 2. Edit the proof files

Open `.synrail/final_result.json` and replace the placeholder content with your actual result. Do the same for `readback.txt` (your readback of what changed) and `scenario_proof.txt` (evidence the change works).

### 3. Check

```bash
synrail check
```

**Expected output on first try: non-green.** This is normal. You will see what failed and what to fix.

### 4. Fix what check says, then re-check

Fix only the named issue in your proof files, then rerun:

```bash
synrail check
```

Repeat until you see `CLOSURE_ACCEPTED`. Typical: 2-4 iterations.

## What non-green means

- `DOCTOR_NOT_GREEN` -- readiness check failed. Read the blocking failure class.
- `MISSING_PROOF_SECTIONS` -- proof bundle is incomplete. Fill in the named sections.
- `SEMANTIC_PROOF_INSUFFICIENT` -- structure is there but evidence is thin. Strengthen the named sections.
- `CONTROLLED_BOOTSTRAP_NOT_CONFIRMED` -- you need to use `synrail start`, not plain init.

Non-green is the normal first state. It means the system is working.

## When you are done

`CLOSURE_ACCEPTED` means the proof bundle is complete, the doctor passed, and closure is honest. You can now:

```bash
synrail session-export --artifact-root .synrail
```

If a later deploy or restart script must cause a side effect, do not call it raw.
Use the deploy-guard pattern described in [DEPLOY_GUARD_INTEGRATION_001.md](/Users/usbdick/Documents/New%20project/synrail/docs/core/DEPLOY_GUARD_INTEGRATION_001.md).

## If something breaks

```bash
synrail bug-packet --artifact-root .synrail
```

This creates a machine-readable bug report you can share with the maintainer.
