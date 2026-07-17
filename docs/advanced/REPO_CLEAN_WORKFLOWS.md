# Repo-Clean Workflows

Use `--ephemeral` when you do QA, analysis, or small agent work across several
repositories and do not want a `.synrail/` directory in every checkout.

The artifacts stay in a per-user cache outside the target repository. Proof,
verification, and changed-file paths still resolve against the target project
root.

## Normal Ephemeral Run

Run these commands from the target repository root:

```bash
synrail start --ephemeral "Describe the bounded local analysis."
# make or inspect the bounded change
synrail record path/to/file --ephemeral \
  --summary "Describe the concrete bounded result." \
  --verify "grep -n 'needle' path/to/file"
synrail check --ephemeral
synrail cleanup --ephemeral
```

For a small clean-start batch of up to 32 existing tracked files:

```bash
synrail start --ephemeral "Describe the bounded local change."
# make the tracked changes
synrail record --ephemeral --all-modified \
  --summary "Describe the concrete bounded result across the tracked files."
synrail check --ephemeral
synrail cleanup --ephemeral
```

`record --all-modified` records per-file rechecks and binds the complete dirty
scope and patch. It is scope proof, not behavioral proof. If the task claims a
test or runtime behavior passed, configure a [behavioral profile](VERIFICATION_PROFILES.md)
and run `synrail verify --ephemeral` before `check`.

## Root Selection

- From a subdirectory inside a git checkout, Synrail discovers the checkout's
  git root automatically.
- From a parent workspace containing multiple repositories, choose the target
  explicitly:

```bash
synrail start --ephemeral --project-root path/to/target-repo \
  "Describe the bounded local analysis."
```

Use the same `--ephemeral` and `--project-root` values for every command in the
run. If a command reports `PATH_SCOPE_VIOLATION`, that command stopped before
closure; correct the named path/root and run `check` again as a new command.
Do not combine a prior blocked result with a later `Status: Accepted`.

## Lifecycle And Cleanup

After a terminal run that no longer needs handoff or debugging, run:

```bash
synrail cleanup --ephemeral
```

That removes this checkout's external run artifacts and never edits project
files. On a later `start --ephemeral`, Synrail prunes stale cache runs older
than 24 hours. To sweep stale cache runs deliberately:

```bash
synrail cleanup --ephemeral --stale
```

`--stale` can affect old runs for other checkouts under the same user cache, so
do not use it as ordinary per-repository cleanup.

A process killed mid-run cannot promise instant cleanup. The normal recovery is
per-project cleanup above or stale pruning on a later ephemeral start. This is
an honest alpha limitation, not proof that an interrupted run was accepted.

## Recheckable Proof Commands

For manual `diff_provenance.verification_command`, use exactly one
repository-relative, read-only command:

- `grep -n ... path/to/file`
- `cat path/to/file`
- `head ... path/to/file`
- `tail ... path/to/file`
- `git diff -- path/to/file`
- `git diff HEAD -- path/to/file`
- `git diff --numstat HEAD -- path/to/file`
- `git show -- path/to/file`
- `git log -- path/to/file`

Do not use `git -c`, `--ext-diff`, `--textconv`, pipes, `&&`, `sed`, `awk`,
`perl`, subshells, or multi-command snippets in this field. Those may be fine
for manual investigation, but they are intentionally not closure-recheckable.
`record --all-modified` selects a safe `git diff --numstat HEAD -- <path>`
shape automatically.

## Windows Notes

Use PowerShell for install, then Git Bash for the current demo harness. For
localized paths and Unix-style read-only commands from Git for Windows:

```powershell
$env:PYTHONUTF8 = "1"
$env:Path = "C:\\Program Files\\Git\\usr\\bin;" + $env:Path
```

## Cache Location

By default, the cache is `~/Library/Caches/synrail` on macOS and
`~/.cache/synrail` on Linux. Set `SYNRAIL_CACHE_HOME` to use a deliberate
separate cache location; on Linux, `XDG_CACHE_HOME` controls the base when the
Synrail-specific variable is unset.
