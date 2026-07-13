# Synrail Roadmap

Current as of 2026-07-13.

This file is the public current roadmap. Older kernel-hardening detail lives in `docs/review/ROADMAP_STATUS_001.md` and the review archive; do not treat the old sprint notes as the active source of truth.

## Current Phase

Synrail is in a narrow public-alpha proof phase.

The job is no longer to add more kernel surface. The job is to prove whether the current false-green control loop is understandable, installable, and useful to real users working with coding agents.

Current product claim:

> Synrail catches false-green AI-agent work before you accept it.

Supported lane today:

- one local trusted worktree
- one bounded local agent task
- explicit proof in `.synrail/final_result.json`
- `synrail check` as the acceptance gate
- bounded repair when proof is weak, stale, mismatched, or unverified

Not the current lane:

- broad hosted orchestration
- remote production operations as the main path
- generic CI/CD replacement
- universal agent correctness
- broad self-serve platform behavior

## Already Closed

The following tranches are considered closed enough for public-alpha pressure:

- kernel hardening around doctor, bundle, closure, restore, continuation, artifact consistency, and path scope
- false-green demo and README-first positioning
- public tester protocol and issue templates
- public repo readiness: `pyproject.toml`, CI, coverage visibility, `Makefile`, Docker smoke path, dev constraints, and Apache-2.0 license
- agent adoption files for Claude, Gemini, and generic agent hosts
- local benchmark/discussion starter surfaces for false-green cases
- operator-owned behavioral verification profiles, a real red-to-green demo,
  and fail-safe profile scaffolding/readiness inspection before controlled start

These are not proofs of broad product maturity. They are enough to stop self-curating and collect external signal.

## Active Priorities

### P0. Run Real External Alpha Tests

Goal:

- get feedback from 3-5 real users who already use Claude Code, Codex, Gemini CLI, Cursor, Aider, or similar coding-agent workflows

What to ask testers to do:

1. read the README first screen
2. run the false-green demo
3. try one small real local task
4. report where Synrail helped, confused them, or felt too heavy

Primary handoff:

- `docs/review/FIRST_TESTER_PROTOCOL_001.md`
- `.github/ISSUE_TEMPLATE/alpha_feedback.yml`
- `.github/ISSUE_TEMPLATE/false_green_case.yml`
- `.github/ISSUE_TEMPLATE/confusing_output.yml`

Definition of done:

- at least three non-LLM external reports
- at least one report from a live coding-agent workflow
- each report classified as product-owned, operator-owned, harness-owned, mixed, or unclear before changing the kernel

### P1. Fix Alpha Integration Findings From Live Runs

Goal:

- make first live installs and server/tester workflows boring enough that the tool does not confuse the operator before proving value

Known current finding:

- Gemini/server alpha run surfaced `PATH_SCOPE_VIOLATION` and doctor overrides while also reaching `Status: Accepted`
- one attempted finding file was written outside the repo before being copied back inside
- an external black-box run on 82f3d71 reached `Status: Accepted` with a failing
  test suite by substituting a valid read-only grep for the claimed test run;
  closed by operator-owned verification profiles (`synrail.toml`, `synrail verify`,
  fail-closed receipt gate in `check`) with regression coverage in
  `tests/test_behavioral_claim_gap.py`
- first-run profile setup no longer depends on memorizing TOML: `init-verification`
  writes an untrusted review scaffold, while verification-aware `preflight`
  reports whether config/git/executable inputs are actually ready for `start`

Follow-up:

- reproduce the `PATH_SCOPE_VIOLATION` on a fresh run
- ensure user-facing output distinguishes blocking errors from advisory diagnostics
- improve repo-root and repo-relative path guidance for Gemini/server workflows
- avoid reporting a run as clean when accepted closure required operator overrides that materially affect trust

Anchor:

- `docs/review/SERVER_GEMINI_ALPHA_FINDING_001.md`

Definition of done:

- fresh repro or explicit non-repro note
- docs or code fix tied to the observed failure mode
- regression coverage if the issue is product-owned

### P2. Turn The Demo Into Evidence, Not Decoration

Goal:

- make the false-green problem visible in under 30 seconds and runnable in under 2 minutes

Current surfaces:

- `examples/false-green-demo/README.md`
- `examples/false-green-demo/run_demo.sh`
- `examples/false-green-demo/assets/synrail-false-green-hero.gif`
- `examples/false-green-benchmark/README.md`

Next work:

- keep the README hero demo short and legible
- collect 10-20 small false-green benchmark cases as discussion/tester prep, not as inflated empirical claims
- separate result labels clearly: `accepted`, `blocked`, `repair-needed`
- measure overhead only when the run is actually observed, not estimated from author intuition

Definition of done:

- a new user can understand the problem from the README without reading internal review docs
- benchmark/example cases are honest about provenance
- no claim of broad false-green rates until external data exists

### P3. Keep Public Repo Readiness Boring

Goal:

- preserve install/test/CI confidence without turning the project into compliance theater

Allowed work:

- fix CI breakage
- fix install friction
- update `Makefile`/Docker/docs when they drift
- keep dependency constraints current intentionally
- keep the license and packaging metadata clear

Not now:

- full strict typing migration
- broad SBOM/release compliance stack
- large architecture rewrite
- large docs reshuffle unrelated to first-user comprehension

Definition of done:

- `make verify` remains green
- GitHub Actions remains green
- README quickstart and demo commands remain true

### P4. Decide From Signal, Not From More Internal Audits

Goal:

- stop letting self-review replace market/user evidence

After the first external signal set, decide one of three paths:

1. **Double down on the wedge** if users see real false-green value despite overhead.
2. **Reduce ceremony** if users understand the value but bounce off the workflow cost.
3. **Pause kernel growth** if users do not find a real need beyond simpler checklists, tests, and manual review.

Definition of done:

- a written decision note that cites external reports, not only internal audits or model critiques

## Public-Signal Freeze Rule

During this phase, these changes are allowed:

- bugfixes
- install-path fixes
- docs clarification
- demo polish
- feedback intake improvements
- narrowly scoped regressions from live alpha findings

These changes are frozen unless external signal justifies them:

- new proof/kernel features
- new continuation families
- broad CLI/spine refactors
- hosted telemetry or SaaS work
- remote ops/product broadening
- generic workflow automation layers
- large compliance programs

## Decision Rule

A change is on-roadmap if it helps a new external user answer one of these questions:

- What problem does Synrail solve?
- Can I install and run it without special author knowledge?
- Did it catch a real false-green or proof mismatch?
- Did it give a bounded repair step that helped?
- Was the overhead justified for this task?

A change is probably off-roadmap if it mainly makes the internal architecture feel more complete while delaying external proof.

## Current Verification Commands

Before public-facing changes land, prefer:

```bash
git diff --check
make install-dev
make verify
make demo
docker build -t synrail-demo .
docker run --rm synrail-demo synrail --help
```

If Docker is unavailable, record that explicitly rather than pretending the container smoke path ran.

## Current Reading Path

For new users:

1. `README.md`
2. `examples/false-green-demo/README.md`
3. `docs/core/FIRST_RUN_GUIDE.md`
4. `docs/review/FIRST_TESTER_PROTOCOL_001.md`

For reviewers:

1. `docs/README.md`
2. `docs/review/ROADMAP_STATUS_001.md`
3. `docs/review/SERVER_GEMINI_ALPHA_FINDING_001.md`
4. archived audits only when historical context is needed
