# First Tester Protocol 001

This is the shortest bounded protocol for early external testers.

It is for people who already use Claude Code, Codex, Cursor, or Aider on real small tasks.
It is not a broad product onboarding flow.

## Goal

Learn three things quickly:

1. did the false-green wedge make sense fast
2. did Synrail catch anything useful on one real small task
3. did the operator overhead feel justified

## Who this is for

Good first testers usually:

- already use a coding agent on real repo work
- can run one small local task end to end
- care about false-green outcomes, weak proof, or manual re-check cost

## Give the tester this path

1. Install Synrail.
2. Read the repo README first screen.
3. Run the false-green demo.
4. Try one real small local task.
5. Report the result through the issue templates.

## Exact reading / run order

1. `README.md`
2. `examples/false-green-demo/README.md`
3. `docs/core/FIRST_RUN_GUIDE.md`

Then:

```bash
./examples/false-green-demo/run_demo.sh
```

On Windows, create and install the venv from PowerShell as documented in the
First Run Guide, then run the demo command above from Git Bash. The demo harness
detects both `.venv/bin/synrail` and `.venv/Scripts/synrail.exe`.

Before leaving the Synrail checkout, make its installed console script available
to the current shell:

```bash
# macOS / Linux
export PATH="$PWD/.venv/bin:$PATH"
```

```powershell
# Windows PowerShell
$env:Path = "$(Resolve-Path .venv\Scripts);$env:Path"
```

Then change directory to the target repository root and try one real small task
with the repo-clean lane:

```bash
synrail start --ephemeral "Describe the bounded local change."
# edit the final_result.json path printed by start
synrail check --ephemeral
# follow only the named repair step until Status: Accepted
synrail cleanup --ephemeral
```

## What kind of task to try

Prefer one small task where an agent could plausibly sound finished too early:

- small refactor
- template or docs change
- test fix
- small batch edit
- narrow multi-file cleanup

Avoid broad migrations, production rollout work, or large refactors for this first pass.

## What feedback we want

Report:

- where you got confused
- whether Synrail caught anything useful
- whether the overhead felt justified
- whether you would use it again
- if the agent claimed done but reality did not match, whether Synrail caught it

## Where to file feedback

Use the GitHub issue templates:

- `Alpha feedback`
- `False-green case`
- `Confusing output`

The reporter should provide facts, not diagnose ownership. Ask for the Synrail
version or commit, OS, agent, exact command, redacted working directory, artifact
mode, and whether the standalone demo passed.

## Maintainer triage before any kernel change

Every new alpha report starts as `ownership:needs-triage`. Reproduce it on current
`main`, then assign exactly one primary owner:

- `ownership:product` - the supported public CLI violates a documented contract;
  add a failing regression before changing the implementation
- `ownership:operator` - the command, working directory, dependency, agent policy,
  or unsupported usage caused the failure; improve guidance or diagnostics first
- `ownership:harness` - the demo, fixture, CI adapter, wrapper, or tester protocol
  fails while the equivalent direct public CLI path works

If one report contains multiple owners, split it before implementation. Do not
change proof or closure policy merely to make an operator- or harness-owned case
green. Remove `ownership:needs-triage` when the primary owner is assigned.

## Honest boundary

This protocol is for narrow local alpha signal.
It is meant to pressure the current wedge, not to prove broad product readiness.
