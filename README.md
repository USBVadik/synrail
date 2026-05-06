# Synrail

Synrail catches false-green AI-agent work before you accept it.

Your coding agent says the task is done.
Synrail checks whether the proof is real.

If the proof is weak, mismatched, or unverified,
Synrail blocks acceptance and gives one bounded repair step.

The failure mode is simple: an agent says "done", the tests look plausible, and the operator is still missing trustworthy proof.
Synrail exists to hold that line between execution and acceptance.

An agent saying "done" is not the same thing as an accepted result.
Synrail keeps that boundary explicit.

**New here?** Start with [Your First Synrail Run](docs/core/FIRST_RUN_GUIDE.md).

## 30-Second Demo

```text
Agent: done, tests passed
Synrail: Status: Proof Invalid
Reason: verification command not executed / freshness mismatch
Next: repair final_result.json
Agent: repaired final_result.json and ran the real verification
Synrail: Status: Accepted
```

![Synrail false-green demo](examples/false-green-demo/assets/synrail-false-green-hero.gif)

A simulated false-green claim is blocked until the proof is repaired and verified.
For social posts or embeds that prefer video, use the [MP4 demo asset](examples/false-green-demo/assets/synrail-false-green-hero.mp4).

That is the product wedge: block plausible-but-unproven closure, name the exact blocker, and keep the next repair step bounded.
The point is not to make agent output sound confident. The point is to stop false-green closure before it gets accepted as truth.
See the standalone [false-green demo](examples/false-green-demo/README.md), the short [demo summary](examples/false_green_demo.md), and the [first tester protocol](docs/review/FIRST_TESTER_PROTOCOL_001.md).

If you only open three public surfaces, use them in this order:

- [false-green demo](examples/false-green-demo/README.md)
- [Your First Synrail Run](docs/core/FIRST_RUN_GUIDE.md)
- [first tester protocol](docs/review/FIRST_TESTER_PROTOCOL_001.md)

## Run Locally In 2 Minutes

```bash
make install-dev
.venv/bin/synrail --help
make demo
```

This is the recommended public path for trying Synrail from a checkout.

## Quick Start

```bash
# after make install-dev

# Workflow: start → verify locally → strengthen final_result.json first → check → fix → check again
.venv/bin/synrail start "Describe the bounded local change."
# run local verification, strengthen .synrail/final_result.json first,
# leave readback/scenario_proof untouched unless synrail check names them, then:
.venv/bin/synrail check
# if non-green, fix what check says, then rerun .venv/bin/synrail check
```

## Alpha Tester Install Path

Use this only when you want the repo-native installer path used by alpha testers.
It writes `CLAUDE.md`, `GEMINI.md`, and `AGENTS.md` for agent discovery in the target project.

```bash
make install-local
```

## Developer Checks

```bash
make smoke
make verify
```

`make verify` runs compile, tests, Ruff, coverage visibility, and dependency audit.
For a container smoke path:

```bash
docker build -t synrail-demo .
docker run --rm synrail-demo synrail --help
```

## Comparison Table

| Scenario | Manual checks | Agent rules | CI alone | Synrail |
| --- | --- | --- | --- | --- |
| Agent claims tests passed but never ran them | easy to miss | usually trusts the claim | maybe later | blocks acceptance until verified |
| Agent shows a plausible diff but proof does not match the task | manual line audit | weak | no | names the exact proof repair |
| Second operator inherits a failed repair | manual reconstruction | weak | no | bounded continuation from artifacts |
| Several bounded agent runs happen in sequence | expensive to re-check each run | weak | late branch signal | proof gate per run |

## When To Use It

Use Synrail when:

- one local agent run on the same machine needs a reviewable proof boundary
- an agent can plausibly claim success before the proof is trustworthy
- you want one bounded repair step instead of free-form debugging after a non-green result
- continuation or handoff should work without author memory
- restore of a trusted local state is worth preserving explicitly

## When Not To Use It

Do not use Synrail when:

- the task is so cheap that a simpler baseline already keeps false-green exposure low enough
- you need a broad self-serve workflow platform or general automation engine
- you need remote-host or production-target execution as the main lane today
- you want the current alpha to stand in for full deployment or ops orchestration

## Current Readiness

Synrail is currently a narrow local alpha product.
It is stronger on false-green prevention, bounded repair, and continuation than earlier versions, but it is not yet broad self-serve or broad production-ready.

## License

Synrail is licensed under the Apache License 2.0. See [LICENSE](LICENSE).

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
