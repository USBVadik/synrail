# Your First Synrail Run

Synrail governs one bounded change at a time. It blocks false-green closure and tells you what to fix.

## False-Green Demo

```text
Agent: tests passed
Synrail: Status: Proof Invalid
Reason: verification command not executed / freshness mismatch
Next: repair final_result.json
```

Only `Status: Accepted` means the task may be reported as complete.

## Install

```bash
make install-dev
```

This creates the local development venv and installs the `synrail` console script used by the public quickstart.

## Optional One-Time Repo Setup For Local Agents

If you want local coding agents to discover Synrail naturally in this repo, bootstrap the repo-native hints in one step:

```bash
make install-local
```

That wraps the repo-native installer and immediately creates missing `AGENTS.md` / `GEMINI.md` / `CLAUDE.md` files in the repo root or appends a managed Synrail block to existing ones. If you later rerun with `--force`, Synrail first writes a timestamped `.synrail.bak.*` backup of the existing policy file before replacing it. It is optional for humans, but useful when you want the local agent workflow to start in controlled mode without adding Synrail instructions to every prompt.

For a runnable GitHub Actions lane after install, use:

```bash
synrail init-ci --workflow
```

That writes both the local composite action and `.github/workflows/synrail-check.yml`. If you only want the adapter, run `synrail init-ci` and then add your own workflow that calls `uses: ./.github/actions/synrail-check`.

If either generated file already exists with different contents, Synrail blocks unless you rerun with `--force`, and it writes a timestamped `.synrail.bak.*` backup before replacing the existing file.

## Git Preflight

Start here:

```bash
synrail preflight
```

If the checkout-local wrapper is blocked on this host, use the repo-local fallback instead:

```bash
python3 alpha.py preflight
```

Synrail works best when `git` is installed because the cheapest strong proof is a real `git_diff`.

Check once:

```bash
git --version
```

If `git` is missing, preflight should make the weaker path explicit:

Git is not installed. Synrail can still use structured diff_provenance, but git_diff and restore coverage will be weaker. Install git for the normal path.

Use that exact message when preflight reports the missing-git path.

If `git` is missing, Synrail can still run. Do not invent a `git_diff`. In `.synrail/final_result.json`, leave `git_diff` empty and use structured provenance instead:

- for a single-file change, use `diff_provenance`
- for a multi-file change, use `diff_provenance_records` or `per_file_diff_provenance` with one record per modified file
- in each record, include `changed_file`
- one exact `added_line`, `removed_line`, or `observed_line`
- one stable `context_before` or `context_after`
- `verification_command`
- `verification_result`

If `synrail` is not on your `PATH` after install, use the local wrapper from this checkout:

```bash
./.venv/bin/synrail
```

If a local agent host blocks that checkout-local wrapper behind a permission or approval wall, try the repo-local fallback instead:

```bash
python3 alpha.py
```

For a full repo-native first loop, use the exact fallback commands instead of probing wrapper paths:

```bash
python3 alpha.py
python3 alpha.py start "Describe the bounded local change."
python3 alpha.py check
```

The rest of this guide still uses `synrail` for brevity.

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

If you are doing QA/analysis across many repositories and do not want Synrail artifacts inside each checkout, use the repo-clean artifact lane:

```bash
synrail start --ephemeral "Describe the bounded local analysis."
```

That stores Synrail artifacts in the user cache for this project while keeping `project_root` and verification paths bound to the repository you launched from. Continue with:

```bash
synrail check --ephemeral
synrail cleanup --ephemeral
```

If you run from a subdirectory inside a git checkout, Synrail uses the git repository root as the default project root. If you are launching from a parent workspace that contains many repos, pass the target explicitly:

```bash
synrail start --ephemeral --project-root path/to/target-repo "Describe the bounded local analysis."
```

`start --ephemeral` prunes stale ephemeral runs older than 24 hours before creating the new run. You can also sweep old ephemeral cache runs manually:

```bash
synrail cleanup --ephemeral --stale
```

Use `--artifact-root ./.synrail` only when you intentionally want the run artifacts to stay inside the repository for handoff or debugging.

### 2. Do the bounded work and keep proof honest

Make the requested change. Run local verification. Then strengthen `final_result.json` first. On the normal happy path, treat it as the only proof surface you need to touch. Only expand fallback proof surfaces later if `synrail check` names them, or if `final_result.json` still cannot carry strong structured verification by itself:

- `final_result.json` for the trust-bearing status, changed files, and diff/provenance record
- `readback.txt` is fallback-only; if `final_result.json` already carries strong structured verification, leave `readback.txt` untouched unless `synrail check` explicitly names it
- `scenario_proof.txt` is fallback-only; if `final_result.json` already carries strong structured verification, leave `scenario_proof.txt` untouched unless `synrail check` explicitly names it

In `final_result.json`, use a trust-bearing status: `PROVEN` for an evidenced bounded edit, or `ALREADY_SATISFIED` only for a truthful no-op attestation where the requested state was already present before any edit.

If `git` is unavailable in the project environment, leave `git_diff` empty. Use `diff_provenance` for a single-file change, or `diff_provenance_records` / `per_file_diff_provenance` with repo-relative paths and exact observed lines for a multi-file change, instead of trying to simulate a patch.

For `diff_provenance.verification_command`, use one directly recheckable repo-relative read-only command: `grep -n`, `cat`, `head`, `tail`, `git diff -- <path>`, `git show -- <path>`, or `git log -- <path>`. Git recheck commands must use exactly `git diff/show/log -- <path>` with no `git -c`, `--ext-diff`, `--textconv`, or other options before `--`. Do not use pipes, `&&`, `sed`, `awk`, `perl`, subshells, or multi-command snippets there; those can be valid manual investigation commands, but they are not stable closure recheck commands.

On Windows, set UTF-8 mode before runs that touch localized paths such as `Рабочий стол`, and put Git for Windows `usr\bin` on `PATH` when your `verification_command` uses `grep`, `cat`, `head`, or `tail`:

```powershell
$env:PYTHONUTF8 = "1"
$env:Path = "C:\Program Files\Git\usr\bin;" + $env:Path
```

In the normal `synrail check` path, you usually do not need to hand-copy run identity fields or a cleanup summary into `final_result.json` when the current controlled run context and doctor-ready workspace already provide that truth. Focus first on the status, changed files, and diff/provenance. Only spend extra steps on `readback.txt` or `scenario_proof.txt` if `check` still names them after `final_result.json` is already strong.

If you need help with the default proof shape, use:

```bash
synrail final-result-template
```

Only if `check` later targets a fallback prose surface, use:

```bash
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

Repeat until `synrail check` prints `Status: Accepted`.

Only `Status: Accepted` means the task may be reported as complete. If Synrail returns `Proof Invalid`, `Rejected`, `Blocked`, or any repair step, do not summarize the task as done; run the named repair step or report the exact Synrail blocker.

## What non-green means

- `Controlled Run Required` -- you need to use `synrail start`, not plain init.
- `Proof Incomplete` -- the proof bundle is incomplete. Fill in the named sections.
- `Proof Too Thin To Trust` -- structure is there but evidence is thin. Strengthen the named sections.
- `Workspace Not Ready` or `Workspace Not Trusted` -- readiness or trust failed. Read the blocking repair target.
- `Cannot Continue This Run` -- this run reached a terminal rejected state. Start a new bounded run or restore a verified point before trying again.

Non-green is the normal first state. It means the system is working.

## When you are done

`Status: Accepted` means the proof bundle is complete, the doctor passed, and closure is honest. You can now:

```bash
synrail session-export --artifact-root .synrail
```

If a later deploy or restart script must cause a side effect, do not call it raw.
Use the deploy-guard pattern described in [DEPLOY_GUARD_INTEGRATION_001.md](./DEPLOY_GUARD_INTEGRATION_001.md).

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
