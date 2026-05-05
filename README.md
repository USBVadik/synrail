# Synrail

Synrail catches false-green AI-agent work before you accept it.

The failure mode is simple: an agent says "done", the tests look plausible, and the operator is still missing trustworthy proof.
Synrail exists to hold that line between execution and acceptance.

An agent saying "done" is not the same thing as an accepted result.
Synrail keeps that boundary explicit.

**New here?** Start with [Your First Synrail Run](docs/core/FIRST_RUN_GUIDE.md).

## 30-Second Demo

```text
Agent: tests passed
Synrail: Status: Proof Invalid
Reason: verification command not executed / freshness mismatch
Next: repair final_result.json
Agent: repaired final_result.json
Synrail: Status: Accepted
```

That is the product wedge: block plausible-but-unproven closure, name the exact blocker, and keep the next repair step bounded.
The point is not to make agent output sound confident. The point is to stop false-green closure before it gets accepted as truth.
See the standalone [false-green demo](examples/false_green_demo.md).

## Quick Start

```bash
# Install into a local venv (writes CLAUDE.md / GEMINI.md / AGENTS.md for agent discovery)
python3 tools/reference/synrail_install_v0.py --venv .venv --project-root "$(pwd)"

# Workflow: start → verify locally → strengthen final_result.json first → check → fix → check again
synrail start "Describe the bounded local change."
# run local verification, strengthen .synrail/final_result.json first,
# leave readback/scenario_proof untouched unless synrail check names them, then:
synrail check
# if non-green, fix what check says, then rerun synrail check
```

## When To Use It

Use Synrail when:

- an agent can plausibly claim success before the proof is trustworthy
- you want one bounded repair step instead of free-form debugging after a non-green result
- continuation or handoff should work without author memory
- restore of a trusted local state is worth preserving explicitly

## When Not To Use It

Do not use Synrail when:

- the task is so cheap that a simpler baseline already keeps false-green exposure low enough
- you need a broad hosted workflow platform or general automation engine
- you need broad production-target or remote-host orchestration as the main lane today

## Current Readiness

Synrail is currently a narrow local alpha product.
It is stronger on false-green prevention, bounded repair, and continuation than earlier versions, but it is not yet broad self-serve or broad production-ready.

## What It Does

- blocks claimed-done closure until proof reaches accepted status
- surfaces one bounded next repair step after a non-green result
- keeps proof on explicit runtime artifacts instead of narrative trust
- preserves trusted local recovery points when they exist
- supports bounded continuation and second-operator handoff

## First Reading Path

Start here:

- [First Run Guide](docs/core/FIRST_RUN_GUIDE.md)
- [Docs Map](docs/README.md)

Then, only if you want deeper product or technical context:

- [Review archive map](docs/review/README.md)

## Layout

- `docs/core/` — kernel contracts and truth surfaces
- `tools/reference/` — CLI and reference implementation
- `tests/` — unit and integration tests
- `fixtures/` — run artifacts and alpha test results

## Truth Boundary

`Status: Accepted` is the only state that means the task may be reported as complete.
Non-green is not failure theater; it is the product telling you what still needs repair.

## Current Support Boundary

Supported today: one local trusted worktree on the same machine where the agent acts.
Not yet the main lane: broad remote-host, ops, or production-target execution.

## Why This Exists

Synrail is for the narrow middle where "looks plausible" is too weak, but heavyweight process is too expensive.
It tries to make honest local agent work reviewable without pretending every claimed success is real.

## Honest Limitation

This repo currently shows a stronger narrow alpha lane, not broad product inevitability.
Read the deeper review material only after the first-run path makes sense.
