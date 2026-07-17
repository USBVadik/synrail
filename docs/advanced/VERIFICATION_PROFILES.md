# Behavioral Verification Profiles

Use this route when an agent needs to make a behavior claim, for example
"tests pass", "the route returns 200", or "the build succeeds". A patch or a
`grep` result can prove that a file changed; it cannot prove program behavior.

Synrail makes a behavioral command an acceptance requirement only when the
operator reviews and commits it before the controlled run begins.

## The Short Route

From the target repository root:

```bash
# 1. Inspect safe, review-required candidates. Nothing is executed or written.
synrail suggest-verification

# 2. Write a review-required scaffold for the command you chose.
synrail init-verification --name unit -- @synrail-python -m pytest -q

# 3. Review synrail.toml and commit it.
git add synrail.toml
git commit -m "Add Synrail unit verification profile"

# 4. Confirm that the run can lock the profile.
synrail preflight

# 5. Start work, make the change, record proof, then run the profile.
synrail start "Describe the bounded local change."
synrail verify
synrail check
```

Continue only when preflight reports `Behavioral verification: READY`.
`REVIEW_REQUIRED` and `BLOCKED` are intentional non-green states: do the named
next step rather than starting a mutation run.

## Example Config

```toml
[verification.unit]
argv = ["@synrail-python", "-m", "pytest", "-q"]
timeout_seconds = 300
required = true
```

`@synrail-python` is the one reserved executable alias. It resolves to the
interpreter that is running Synrail, while Synrail locks that interpreter's
realpath and bytes. It is useful for a portable Python profile, but it does not
search for a separate target-project virtual environment. If Synrail runs from
a global tool environment, review an explicit project interpreter or
project-owned test runner instead.

## What Synrail Locks

At `start`, Synrail authenticates a lock over the project and git root, the
raw and normalized config hashes, and each resolved executable's path and
SHA-256. At `verify`, it rechecks that lock and executes the exact argv without
a shell.

A required profile blocks acceptance when any of these change:

- the project root or visible workspace
- `synrail.toml` or its clean tracked provenance
- the configured executable
- the run-bound profile lock
- the files after a previous green receipt

`verify` sanitizes common runtime override variables such as `PYTEST_ADDOPTS`,
`NODE_OPTIONS`, and preload hooks. It retains bounded diagnostic output, hashes
the full output, and writes a receipt tied to the run and workspace.

A failed or missing required receipt means `synrail check` cannot return
`Status: Accepted`. A convenient read-only `grep` proof cannot substitute for a
failing required test.

## Rules That Matter

- Treat `synrail.toml` as operator-owned policy. Do not let an active agent
  change it to escape a failing profile.
- Review and commit the file before `start`; a present but dirty, untracked,
  invalid, unsafe, or unresolved profile is not trusted.
- Do not put secrets in `argv`. The profile is intended to be reviewed and
  committed, and Synrail displays the argv during setup.
- `suggest-verification` recognizes conventional Python, Node, Go, and Rust
  markers. It is a suggestion only: it never executes a candidate, writes
  config, or treats a guess as trusted.
- `init-verification` is idempotent and refuses to replace a different config
  by default. `--force` writes a timestamped backup first.

## Receipt Key Lifecycle

Synrail signs verification locks and receipts with one local per-user HMAC key.
It is user state, not a project artifact. Never commit, attach, or share it.

- macOS: `~/Library/Caches/synrail/receipt_hmac.key`
- Linux: `~/.cache/synrail/receipt_hmac.key`
- `SYNRAIL_CACHE_HOME` overrides the default.
- On Linux, `XDG_CACHE_HOME` selects the cache base when `SYNRAIL_CACHE_HOME`
  is unset.

Rotating or deleting the key makes earlier receipts unverifiable by design.
Start a fresh run and verify again; do not use key rotation to make a blocked
run appear green.

## Important Trust Boundary

This is a strong local drift and accidental-false-success guard, not a hostile
same-user boundary. If the agent shares your account, it can potentially reach
both project files and local user state. For a tamper-resistant acceptance
boundary, make a required CI check run on a surface the agent cannot modify.

## Troubleshooting

| State | Meaning | Next move |
| --- | --- | --- |
| `NOT_CONFIGURED` | No behavioral policy was locked. | Use only a non-behavioral proof claim, or create and commit a profile for the next run. |
| `REVIEW_REQUIRED` | A scaffold/config needs operator review or commit. | Inspect argv and timeout, then commit `synrail.toml`. |
| `BLOCKED` | The config, executable, or git provenance is unsafe. | Follow the exact printed reason; do not bypass it with narrative proof. |
| Verification fails | The actual command returned non-zero or timed out. | Repair the code or command, then rerun `synrail verify`. |
| Receipt is stale | Code/config/workspace changed after verification. | Rerun `synrail verify` against the current workspace. |
