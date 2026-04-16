# Your First Synrail Run

Synrail governs one bounded change at a time. It blocks false-green closure and tells you what to fix.

## Install

```bash
python3 tools/reference/synrail_install_v0.py --venv .venv
```

## Five Steps

```bash
ARTIFACT_ROOT="$(pwd)/.synrail"
```

### 1. Start a controlled run

```bash
synrail start --artifact-root "$ARTIFACT_ROOT" --project-root "$(pwd)" \
  --task-identity "Describe the bounded change you are making."
```

This creates `.synrail/` with starter proof files: `final_result.json`, `readback.txt`, `scenario_proof.txt`.

### 2. Edit the proof files

Open `.synrail/final_result.json` and replace the placeholder content with your actual result. Do the same for `readback.txt` (your readback of what changed) and `scenario_proof.txt` (evidence the change works).

### 3. Check

```bash
synrail check --artifact-root "$ARTIFACT_ROOT"
```

**Expected output on first try: non-green.** This is normal. You will see `CLAIMED_NOT_ACCEPTED` with a `blocking_reason` and a `next_safe_step`. Read them.

### 4. Repair

```bash
synrail repair-step --artifact-root "$ARTIFACT_ROOT"
```

This tells you exactly what is still missing or weak. Fix the named issue in your proof files.

### 5. Re-check

```bash
synrail check --artifact-root "$ARTIFACT_ROOT"
```

Repeat steps 4-5 until you see `CLOSURE_ACCEPTED`. Typical: 2-4 iterations.

## What non-green means

- `DOCTOR_NOT_GREEN` -- readiness check failed. Read the blocking failure class.
- `MISSING_PROOF_SECTIONS` -- proof bundle is incomplete. Fill in the named sections.
- `SEMANTIC_PROOF_INSUFFICIENT` -- structure is there but evidence is thin. Strengthen the named sections.
- `CONTROLLED_BOOTSTRAP_NOT_CONFIRMED` -- you need to use `synrail start`, not plain init.

Non-green is the normal first state. It means the system is working.

## When you are done

`CLOSURE_ACCEPTED` means the proof bundle is complete, the doctor passed, and closure is honest. You can now:

```bash
synrail session-export --artifact-root "$ARTIFACT_ROOT"
```

If a later deploy or restart script must cause a side effect, do not call it raw.
Use the deploy-guard pattern described in [DEPLOY_GUARD_INTEGRATION_001.md](/Users/usbdick/Documents/New%20project/synrail/docs/core/DEPLOY_GUARD_INTEGRATION_001.md).

## If something breaks

```bash
synrail bug-packet --artifact-root "$ARTIFACT_ROOT"
```

This creates a machine-readable bug report you can share with the maintainer.
