# Synrail

[![CI](https://github.com/USBVadik/synrail/actions/workflows/security-hygiene.yml/badge.svg)](https://github.com/USBVadik/synrail/actions/workflows/security-hygiene.yml)
[![License: Apache-2.0](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)
![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue)
![Status: Alpha](https://img.shields.io/badge/status-alpha-orange)

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

## Is This Just Post-Review?

Not exactly.

A normal post-review asks: is this code good?

Synrail asks a narrower question first: is the agent allowed to claim this task is done?

If you personally inspect every diff, run every check, and keep the whole agent context in your head, Synrail may be unnecessary overhead. In that mode, you are acting as Synrail manually.

Synrail is for the moment you stop being the runtime supervisor: repeated small agent runs, long context, handoff, failed repairs, or proof-sensitive changes.

It does not replace review. It prevents unearned acceptance before review.

## Try It In 2 Minutes

```bash
git clone https://github.com/USBVadik/synrail
cd synrail
make install-dev
make demo
```

This is the fastest way to see Synrail block a simulated false-green claim and then accept the repaired proof.

## Verify The Local Install

```bash
make install-dev
.venv/bin/synrail --help
make demo
```

Use this when you already have the checkout and want the shortest local smoke path.

## You May Not Need Synrail If

- you are doing one tiny change
- you personally inspect every changed line
- you run the verification yourself
- you keep the whole agent context in your head
- a false-green costs less than running the gate

In that case, the baseline is probably better. Synrail becomes useful when verification debt compounds.

## Who This Is For

- developers using Claude Code, Cursor, Codex, Aider, Gemini CLI, or similar coding agents
- operators who still manually verify whether an agent's "done" claim is actually supported
- teams running repeated small agent changes where false-green review cost compounds
- second operators inheriting a failed repair and needing one bounded next step

## False-Green Cases Synrail Targets

- tests claimed as passed but not actually run
- proof that does not match the changed files
- a plausible diff that does not satisfy the requested task
- narrative completion instead of concrete runtime evidence
- failed repair handoff without a bounded continuation path

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

Prefer a repo-clean artifact lane when you are using Synrail for QA/analysis across many repositories:

```bash
.venv/bin/synrail start --ephemeral "Describe the bounded local analysis."
# edit the reported final_result.json in the user-cache artifact root
.venv/bin/synrail check --ephemeral
.venv/bin/synrail cleanup --ephemeral
```

`--ephemeral` keeps Synrail artifacts outside the project checkout while still resolving proof and verification paths against the project root. If you run from a subdirectory inside a git checkout, Synrail uses the git repository root as the default project root. If you are launching from a parent workspace that contains many repos, pass the target explicitly:

```bash
.venv/bin/synrail start --ephemeral --project-root path/to/target-repo "Describe the bounded local analysis."
```

`start --ephemeral` also prunes stale ephemeral runs older than 24 hours. To sweep old cache runs manually:

```bash
.venv/bin/synrail cleanup --ephemeral --stale
```

For `diff_provenance.verification_command`, keep the command directly recheckable: use one repo-relative read-only command such as `grep -n`, `cat`, `head`, `tail`, `git diff -- <path>`, `git show -- <path>`, or `git log -- <path>`. Do not use pipes, `&&`, `sed`, `awk`, `perl`, subshells, or multi-command snippets in that field.

Windows notes:

```powershell
# Helpful for localized paths such as "Рабочий стол"
$env:PYTHONUTF8 = "1"

# Needed when your verification_command uses grep/cat/head/tail from Git for Windows
$env:Path = "C:\Program Files\Git\usr\bin;" + $env:Path
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

## Give Feedback

- Real false-green caught or missed? Open a `False-green case` issue.
- Confusing install, check, repair, or acceptance output? Open a `Confusing output` issue.
- Tried the demo or one real small task? Open an `Alpha feedback` issue.

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
