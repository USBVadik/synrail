# Your First Synrail Run

Synrail governs one bounded agent task at a time. It does not decide whether a
piece of code is beautiful; it decides whether the run has earned the right to
say it is done.

Only `Status: Accepted` means the task may be reported as complete.

## 0. Install And See The Demo

macOS / Linux:

```bash
make install-dev
make demo
```

Windows PowerShell:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -e ".[dev]" -c constraints-dev.txt
$env:Path = "$(Resolve-Path .venv\Scripts);$env:Path"
synrail.exe --help
```

The animated demo is a Bash harness. On Windows, run it from Git Bash after the
PowerShell install. Synrail currently supports CPython 3.11-3.14.

If the installed command is not on your PATH in a source checkout, use the
local executable:

```bash
.venv/bin/synrail --help
```

`make demo` is disposable and is the quickest way to understand the product.
It shows a real required test fail, a plausible but insufficient proof, and
acceptance only after the behavior is repaired and reverified.

## Pick One Route

1. **A small existing tracked edit:** prove a patch and a recheckable
   observation. Use [route 1](#1-prove-one-small-tracked-change).
2. **A test or runtime claim:** make an operator-reviewed command mandatory.
   Use [route 2](#2-enforce-a-behavioral-claim).
3. **QA across several repositories:** keep artifacts outside each checkout.
   Use [route 3](#3-keep-artifacts-outside-many-repositories).
4. **An unusual edge case:** untracked, deleted, binary, no-git, pre-dirty,
   very large, or no-op work uses the explicit `final_result.json` route. Run
   `synrail final-result-template`, fill only the named proof fields, then let
   `synrail check` tell you whether a fallback surface is actually needed.

Do not use a small patch proof to claim that a test suite passed. That claim
needs route 2.

## 1. Prove One Small Tracked Change

Start from a clean git worktree. Begin one bounded run:

```bash
synrail start "Describe the bounded local change."
```

Make the change and run the project's normal local checks. For exactly one
existing tracked regular file, record the patch and one read-only observation:

```bash
synrail record path/to/file \
  --summary "Describe the concrete bounded result." \
  --verify "grep -n 'needle' path/to/file"
```

Then evaluate closure:

```bash
synrail check
```

For a small clean-start batch of up to 32 existing tracked files, use:

```bash
synrail record --all-modified \
  --summary "Describe the concrete bounded result across the tracked files."
synrail check
```

The batch recorder creates per-file rechecks and binds the complete live dirty
scope and patch. It rejects untracked, deleted, binary, oversized, pre-dirty,
revision-changing, or concurrently modified work. Both record modes write
proof, not acceptance.

If `check` is non-green, fix only the named blocker and run `synrail check`
again. If the change makes a behavior claim, continue with route 2 before that
final check.

## 2. Enforce A Behavioral Claim

Use this when the agent says "tests pass," "the build works," or any other
runtime claim. The command has to be operator-reviewed and committed before
work starts.

```bash
synrail suggest-verification
synrail init-verification --name unit -- @synrail-python -m pytest -q
# review synrail.toml, then commit it
synrail preflight
synrail start "Describe the bounded local change."
# make the change and record its scope proof
synrail verify
synrail check
```

Continue only when `preflight` reports `Behavioral verification: READY`.
`verify` writes a fresh receipt for the locked command; `check` blocks if that
receipt is missing, red, or stale. Full setup, trust limits, and troubleshooting
are in [Behavioral Verification Profiles](../advanced/VERIFICATION_PROFILES.md).

## 3. Keep Artifacts Outside Many Repositories

For analysis, QA, or small work across several repositories, use the ephemeral
lane:

```bash
synrail start --ephemeral "Describe the bounded local analysis."
# make or inspect the bounded change
synrail record --ephemeral --all-modified \
  --summary "Describe the concrete bounded result across the tracked files."
synrail check --ephemeral
synrail cleanup --ephemeral
```

From a git subdirectory, Synrail discovers the checkout root. From a parent
workspace containing multiple repositories, select the target explicitly:

```bash
synrail start --ephemeral --project-root path/to/target-repo \
  "Describe the bounded local analysis."
```

Use the same `--ephemeral` and `--project-root` values throughout the run. The
full multi-repo lifecycle, Windows notes, and allowed proof-command shapes are
in [Repo-Clean Workflows](../advanced/REPO_CLEAN_WORKFLOWS.md).

## Read A Non-Green Result

| Status | Meaning | What to do |
| --- | --- | --- |
| `Verification Failed` | A required behavior command failed or has no green receipt. | Repair the behavior, run `synrail verify`, then check again. |
| `Proof Incomplete` | A required proof surface is absent. | Fill only the named field or run the named template command. |
| `Proof Too Thin To Trust` | The surface exists but does not prove enough. | Strengthen the named scope/provenance evidence. |
| `Workspace Not Ready` / `Workspace Not Trusted` | Root, doctor, or workspace trust is not valid. | Read the named diagnostic; do not bypass it with a generic claim. |
| `Cannot Continue This Run` | The run is terminally rejected. | Start a new bounded run or restore a verified point. |

The first result being non-green is normal. It is Synrail preventing an
unearned completion claim.

## Optional Agent Wiring

Humans can run the commands directly. To teach local agent hosts the same
controlled workflow without repeating it in every prompt:

```bash
make install-local
```

This adds a managed Synrail block to agent-discovery files in the target repo.
The default policy mode is `strict`: it asks the agent to start with Synrail on
every task. For day-to-day Codex, Claude, Gemini, or Cursor work, the focused
mode is usually cheaper:

```bash
synrail init-agent --agent codex --ephemeral --policy-mode focused
```

`focused` leaves ordinary read-only questions, planning, and code review outside
Synrail. It still requires the controlled loop before a mutation task can be
reported complete: `start` -> `record` -> optional `verify` -> `check`. Use the
default `strict` mode when you intentionally want every task, including
orientation and analysis, to begin from governed state.

For Kiro, use:

```bash
synrail init-agent --agent kiro
```

Agent policy does not make behavior claims trustworthy by itself; use a
[verification profile](../advanced/VERIFICATION_PROFILES.md) when needed.

## After A Run

- Keep artifacts when you need a handoff or an audit trail.
- Use `synrail cleanup --ephemeral` after a disposable external-cache run.
- Use `synrail explain-proof` when the printed reason needs more detail.
- Use `synrail restore --preview` before a restore; do not assume restore is a
  universal workspace rollback.
- For a compact report, use `synrail bug-packet`.

For the product overview, return to the [README](../../README.md). For the
complete current/user/maintainer separation, see the [Docs Map](../README.md).
