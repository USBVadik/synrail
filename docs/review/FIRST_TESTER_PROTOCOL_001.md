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

Then try one real small task in a local repo with the normal lane:

```bash
synrail start "Describe the bounded local change."
synrail check
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

## Honest boundary

This protocol is for narrow local alpha signal.
It is meant to pressure the current wedge, not to prove broad product readiness.
