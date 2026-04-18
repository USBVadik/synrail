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

This creates `.synrail/` and opens one governed run for this bounded change.

### 2. Do the bounded work and keep proof honest

Make the requested change. Then make `final_result.json` strong first. Only expand the other proof surfaces if `synrail check` later asks for them, or if `final_result.json` still cannot carry strong structured verification by itself:

- `final_result.json` for the changed files and diff/provenance record
- `readback.txt` for a brief observed readback of the changed surface; when `final_result.json` already carries strong structured verification, treat `readback.txt` as explanatory, or leave it in starter form until `synrail check` explicitly names it
- `scenario_proof.txt` for labeled verification evidence such as `Command:` plus `Observed:` or `Result:`; when `final_result.json` already carries strong structured verification, treat `scenario_proof.txt` as explanatory, or leave it in starter form until `synrail check` explicitly names it

In `final_result.json`, use a trust-bearing status: `PROVEN` for an evidenced bounded edit, or `ALREADY_SATISFIED` only for a truthful no-op attestation where the requested state was already present before any edit.

In the normal `synrail check` path, you usually do not need to hand-copy run identity fields or a cleanup summary into `final_result.json` when the current controlled run context and doctor-ready workspace already provide that truth. Focus first on the status, changed files, and diff/provenance. Only spend extra steps on `readback.txt` or `scenario_proof.txt` if `check` still names them after `final_result.json` is already strong.

If you need help with the expected shape, use:

```bash
synrail final-result-template
synrail readback-template
synrail scenario-proof-template
```

### 3. Check

```bash
synrail check
```

**Expected output on first try: non-green.** This is normal. You will see what failed and what to fix.

### 4. Fix what check says, then re-check

Fix only the named blocker, then rerun:

```bash
synrail check
```

If you need a clearer breakdown of a proof gap, run:

```bash
synrail explain-proof
```

Repeat until you see `CLOSURE_ACCEPTED`.

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

If you already saved a fallback and want to understand what restore would do before changing the workspace again, preview it first:

```bash
synrail restore --preview
```

Then decide whether to actually restore:

```bash
synrail restore
```

If the preview says the current contour is limited or unsupported, do not treat restore as a full workspace rollback.

If you need a compact bug report instead:

```bash
synrail bug-packet --artifact-root .synrail
```

This creates a machine-readable bug report you can share with the maintainer.
