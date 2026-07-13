# Synrail Revival Roadmap

Updated: 2026-07-13
Base commit: `abf213c Restart bounded revival: hygiene, tester checklist, recheck fix`
Purpose: restart bounded development after a pause, without broadening scope.

This roadmap is the current source of truth for the revival pass. Older sprint
plans (`POST_FIX_EXECUTION_ROADMAP_2026-05-03.md`, `LAST.md`, `Priority.md`)
stay valid as deeper technical backlog, but this file governs what happens next.

## Situation

- Development stalled around 2026-06-11 after the AWS-inspector hackathon work.
- The test corpus is healthy: 880 tests and Ruff are green. The release gate is
  not yet green because dependency audit found vulnerable development packages.
- The project was frozen at the correct decision gate from `ROADMAP.md`:
  stop growing the kernel, go collect external signal. Issues #7 and #8 produced
  useful install/artifact-lifecycle feedback, but the fresh post-hardening utility
  ledger still lacks enough real task runs to establish product leverage.
- The "deterministic verification gate for AI coding agents" category has become
  crowded since this was built. Synrail's differentiation is still real
  (local, single-worktree, pre-CI, handoff/continuation honesty), but the window
  to stake that position is narrowing.

## Operating Rule

Do not broaden product scope during this pass. The goal is to de-rust the repo,
de-risk the first impression for an external tester, and unblock external signal.

No new proof/kernel features. No typed-evidence-graph rewrite. No confidence
score. No new internal audit documents.

Every code module below must end with:

1. A local verification command that actually ran.
2. A strong `.synrail/final_result.json` proof.
3. `synrail check` reaching `Status: Accepted`.

## Active Trust-Closure Tranche

This bounded tranche precedes new integrations because the audit reproduced two
fail-open outcomes at supported trust boundaries. Modules must land in order.

### M0 — Isolate And Baseline

Status: complete.

- Work from `codex/trust-closure-2026-07`, based on `abf213c`.
- Keep the unfinished Kiro integration in the original checkout untouched.
- Baseline: 880 tests pass, coverage is 51%, Docker install smoke passes, and
  dependency audit is red.

Definition of done: an isolated clean branch exists and the baseline results are
recorded here without claiming that `make verify` is green.

### M1 — Fail-Closed Closure Freshness

Status: complete.

- A closure freshness binding must use `closure_freshness_binding_v0`.
- It must carry `bound_at_utc` and exactly one record for each canonical artifact
  id: `final_result`, `readback`, `scenario_proof`, and `doctor`.
- `final_result` is required. Present artifacts require an absolute live path
  inside the validated project or artifact root and a valid SHA-256. Absent optional
  artifacts must not retain a path or hash.
- Empty, duplicate, unknown, malformed, missing, stale, or symlinked bindings fail
  closed before `ACCEPTED`.
- A non-green named repair keeps `final_result.json` editable on the same run.
  The accepted hash advances only from the live-rechecked in-memory binding at
  atomic closure, never from a later unaudited disk reread.

Definition of done: direct closure calls and the public live path reject malformed
bindings; a current builder-generated binding remains accepted; adversarial and
gate-unit suites are green.

Residual boundary: this tranche rejects static symlink surfaces and rechecks live
hashes, but it does not claim to eliminate every concurrent filesystem TOCTOU race.
Descriptor-relative traversal hardening remains a separate follow-up if the local
single-operator threat model expands.

### M2 — Retire The Contest-Only AWS Branch

Status: complete.

- Remove `verify-aws-state` and its boto3 inspector from the supported CLI.
- Remove the separate self-fingerprint command introduced with that experiment;
  core artifact integrity remains owned by Synrail closure bindings.
- Remove the AWS feature section from the public README.
- Preserve history in Git rather than carrying an untested compatibility promise.

Definition of done: public help and README no longer advertise AWS inspection or
the contest fingerprint; no live import or test references remain.

### M3 — Runtime/Schema Conformance

Status: complete.

- Extend `proof_bundle_v0.schema.json` to describe every currently emitted top-
  level field, including verification recheck and freshness binding.
- Add a regression that builds a real current bundle and validates it against the
  packaged schema.
- Keep `additionalProperties: false` so future runtime/schema drift fails loudly.

Definition of done: a generated bundle validates with zero errors, while removing
a required trust field or adding an unknown field fails validation.

### M4 — Green Dependency Gate

Status: complete.

- Upgrade vulnerable locked dependencies and regenerate the lock snapshot.
- Add a weekly scheduled dependency-audit run so a stale green badge cannot hide
  newly disclosed advisories.

Definition of done: `make audit` exits zero in a fresh environment and CI keeps a
scheduled audit path.

### M5 — Security And Version Contract

Status: complete.

- Move sensitive vulnerability intake away from public issue attachments.
- Do not ask reporters to upload an unredacted bug packet publicly.
- Set the development version after tag `v0.1.2` and make package/runtime version
  drift testable.

Definition of done: `SECURITY.md` has a private-first path and the installed
version agrees with the development version contract.

### M6 — Release-Gate Verification

Status: complete.

Required commands:

```bash
make compile
make lint
make test
make coverage
make audit
make demo
docker build -t synrail-trust-closure .
```

Definition of done: all commands pass, `git diff --check` is clean, an adversarial
review has no unresolved P0/P1 finding, and no unrelated Kiro work is present in
the branch.

Result: 897 unittest and pytest cases pass, coverage visibility is 53%, Ruff is
clean, `pip-audit` reports no known vulnerabilities, the wheel reports
`0.1.3.dev0`, and the Python 3.11 Docker image installs and starts the public CLI.
The former transcript-only demo is now a live disposable `Proof Invalid` to
`Accepted` run and fails if either expected status is absent.

## Track A: De-rust And De-risk First Impression

Small, safe, high-certainty hygiene that a returning maintainer and a fresh
external tester both benefit from.

- [x] **Module 1 — Single-source package version.** The initial revival aligned
      metadata with `v0.1.2`; this tranche now uses one dynamic source for the
      unreleased `0.1.3.dev0` package and runtime version.
- [x] **Module 2 — Remove dead code.** `tools/reference/synrail_doctor_v0.py`
      has zero import references anywhere in `tools/` or `tests/` (the live doctor
      is `synrail_doctor_v1.py`). Delete it and keep the suite green.
- [x] **Module 3 — Separate advisory from blocking output.** The live finding
      (`SERVER_GEMINI_ALPHA_FINDING_001.md`) was reproduced as a real stale-
      report fail-open: a child-only path-scope failure could be followed by a
      prior `Status: Accepted` and exit 0. CLI and spine now share one canonical
      orchestration path-scope map, prior derived reports are removed before a
      new orchestration, and default output renders path violations as explicit
      blocking results. Machine stdout remains JSON and states `accepted: false`
      plus `closure_evaluated: false`; doctor overrides remain warnings. The
      observed-safe dirty-worktree path also ignores caller-supplied scope claims
      and recomputes its non-override evidence from live git plus proof-backed
      provenance.

      Definition of done: the previously failing accepted-then-out-of-root
      coverage-profile sequence exits 2 with `Status: Blocked`, no accepted
      token, and regression coverage for parent-map parity plus stale-report
      defense.

## Track B: Unblock External Signal

The actual strategic priority from `ROADMAP.md` P0.

- [x] **Module 4 — First external-tester repro checklist.** Lower the friction
      for 3-5 real users of Claude Code / Cursor / Codex / Aider to run the demo
      plus one real task and file feedback, using the existing
      `FIRST_TESTER_PROTOCOL_001.md` and issue templates.
- [ ] Recruit and run 3-5 external testers. Issues #7 and #8 are now classified
      historical alpha signal, but they predate this tester flow and do not prove
      it. Require at least three fresh real-task runs on current `main`.
- [x] **Sharpen the one-sentence positioning against the now-crowded CI-gate
      field.** Synrail is now presented as a local acceptance gate: CI asks
      whether configured jobs passed, AI code review asks what looks wrong in a
      diff, and Synrail asks whether this bounded run earned `done` through
      task-scoped rechecked proof.
- [x] **Classify each report as product- / operator- / harness-owned before any
      kernel change.** Issue forms now collect reproduction facts and start at
      `ownership:needs-triage`; the first-tester protocol defines the three
      mutually exclusive primary owners and requires mixed reports to be split.

## Deeper Backlog (Only After External Signal)

Do not start these until Track B produces signal that the wedge is worth its
overhead. Sourced from `LAST.md`, unchanged in intent:

- everyday-economics accounting as the primary cost metric
- behavioral cheapening (optional prose surfaces stop appearing by default)
- proof-independence attack pack (mutation / adversarial / unseen shapes)
- change-impact invalidation for cheaper retry
- shell pruning to felt-thin first loop

## Track C: Thin First Run

Owner-directed product work resumed before the external tester ledger was full.
The bounded goal is to reduce ceremony without changing what `Accepted` means.

- [x] Preserve explicit `--project-root` across every public-shell command that
      resolves an ephemeral artifact root.
- [x] Reduce public `check --help` to user-facing locator/mode options while
      preserving internal parser compatibility.
- [x] Add `synrail record` for the cheapest honest contour: exactly one direct,
      existing, tracked changed file with a real git patch and one command that
      the existing closure policy can recheck.
- [x] Bind that contour to a clean git baseline and unchanged `HEAD`, and route
      Git subprocesses through a shared layer that blocks local executable Git
      config, hooks, fsmonitor, external diff/textconv, filters, inherited
      `GIT_*` redirection, and repo-local command-binary substitution.
- [x] Rebind recorder-generated proof to the live `HEAD`-to-worktree patch at
      closure time, so a post-record edit becomes non-green until proof is
      recorded again.
- [x] Keep ambiguous contours fail closed. Multi-file, untracked, deleted,
      already-satisfied/no-op, no-git, oversized patch, symlink, concurrent
      mutation, and unsupported verification-command cases remain on the
      explicit proof path.

Definition of done: a real cross-repo ephemeral run reaches `Accepted` through
`start -> edit -> record -> check` without an override; negative cases do not
overwrite the starter proof; the full release gate and adversarial review pass.

## Track D: Operator-Owned Behavioral Verification

The thin proof loop establishes that evidence is real, fresh, and in scope. This
track closes the separate product question: whether behavior such as a test suite
actually passed under a command the operator approved before the agent run.

- [x] Replace the transcript-only public story with a real disposable behavioral
      demo: weak read-only proof is blocked while the approved test profile is red,
      then the same run reaches `Accepted` only after behavioral repair and a green
      receipt.
- [x] Add authenticated Verification Profiles v1. `synrail start` locks a tracked,
      clean `synrail.toml`, executable identity, and project/git root; `synrail
      verify` runs exact argv without a shell and writes run/config/executable/
      workspace-bound receipts; `synrail check` requires fresh green receipts for
      every required profile.
- [x] Add fail-safe `init-verification`: scaffold one review-required profile
      without guessing the ecosystem or executing the command, refuse silent
      replacement, and back up explicit `--force` replacement.
- [x] Extend `synrail preflight` with `NOT_CONFIGURED`, `REVIEW_REQUIRED`,
      `BLOCKED`, and `READY` verification readiness without executing commands or
      creating a trusted lock. Start reuses the same preparation contract.
- [x] Teach generated Codex/Cursor, Claude, and Gemini policies the full
      `preflight -> start -> verify -> check` lifecycle. The policy keeps
      `synrail.toml` operator-owned, blocks mutation starts on review/block states,
      labels `NOT_CONFIGURED` as behaviorally ungated, and forbids replacing a
      failed profile with narrative or read-only proof.
- [x] Add read-only `suggest-verification` discovery for conventional
      Python/Node/Go/Rust root markers. Suggestions expose exact argv and a
      copyable scaffold command, but execute nothing, write nothing, and remain
      `REVIEW_REQUIRED` until the operator explicitly chooses and commits a
      profile.

Definition of done: the public demo, direct CLI, preflight, and generated agent
onboarding all express the same behavioral gate; config/executable/workspace drift
fails closed; targeted policy tests plus the full release gate and adversarial
review pass.

## Do Not Do Yet

- No typed-evidence-graph or VSA closure-certificate rewrite.
- No new proof-artifact families, continuation families, or semantic sections.
- No confidence score, hosted telemetry, or SaaS surface.
- No large CLI refactor of the god-modules before external UX is stable.
- No reviving through the AWS inspector.

## Verification Commands

```bash
.venv/bin/python -m pytest tests/ -q
.venv/bin/ruff check .
make verify
make demo
```

## Session Log — 2026-07-12

The trust-closure tranche was implemented in the isolated
`codex/trust-closure-2026-07` worktree so the unrelated Kiro WIP in the original
checkout remained untouched.

Landed:

- strict live closure freshness binding validation, including trusted roots,
  exact canonical artifact membership, UTC/hash/type checks, and static symlink
  rejection;
- a repairable proof-hash lifecycle that permits the named bounded repair and
  binds the accepted hash from atomic closure;
- runtime/schema conformance plus enforcement for array bounds, patterns, and
  timezone-aware date-time fields;
- retirement of the contest-only AWS inspector and duplicate fingerprint CLI;
- dependency refresh, weekly scheduled audit, private-first security intake,
  private vulnerability reporting enabled on GitHub, and one dynamic
  `0.1.3.dev0` version source;
- a real disposable false-green demo instead of a printed transcript.

The adversarial pass found and fixed four pre-commit defects: symlinked-parent
bindings, builder-side symlink erasure, macOS `/var` alias false rejects, and the
broken `Proof Invalid`/`Proof Incomplete` repair loop. The remaining documented
filesystem TOCTOU boundary is not promoted as solved.

Verification: 897 tests pass in unittest and pytest, coverage visibility is 53%,
Ruff and `git diff --check` are clean, `pip-audit` reports no known
vulnerabilities, the wheel metadata is `0.1.3.dev0`, and the Python 3.11 Docker
install/CLI path passes.

### Track B positioning and report triage

Implemented in the isolated `codex/positioning-triage-2026-07` worktree after
Module 3 merged cleanly to `main`.

Landed locally:

- a first-screen category claim that distinguishes local run acceptance from CI
  execution and AI diff review;
- a repo-clean `--ephemeral` first-tester path, with explicit macOS/Linux and
  Windows install/demo guidance;
- ownership triage in existing issue forms, tester protocol, and contributor
  guidance, without adding another audit document;
- materialized GitHub labels plus retrospective `ownership:product`
  classification for issues #7 and #8;
- Node 24 GitHub Actions in both this repository and generated `init-ci`
  workflows.

Verification: 903 unittest tests and 903 pytest tests pass, coverage visibility
is 54%, Ruff and `git diff --check` are clean, `pip-audit` reports no known
vulnerabilities, issue-form YAML parses, the cross-repo ephemeral setup/cleanup
smoke passes, and the live false-green demo reaches `Proof Invalid` then
`Accepted`.

## Session Log — 2026-07-11

Six bounded Synrail runs, each closed at `Status: Accepted` (all under the
`--clean-surface` doctor override, because the worktree carries unrelated WIP).

Landed:

- Module 0 — this roadmap doc.
- Module 1 — `pyproject.toml` version 0.1.0 -> 0.1.2.
- Module 2 — deleted dead `tools/reference/synrail_doctor_v0.py`; suite green.
- Module 4 — `docs/review/FIRST_TESTER_CHECKLIST_2026-07.md`.
- Option A (below) — verification-recheck env bugfix + regression test.

### A (done) — verification recheck env bugfix

`tools/reference/synrail_bundle_v0.py::_verification_recheck_env` set
`GIT_EXTERNAL_DIFF=""`. On git 2.39 that makes `git diff` abort with
`fatal: external diff died`, so every advertised `git diff -- <path>` recheck
command silently produced empty output on this host. Fix: unset the variable
(`env.pop("GIT_EXTERNAL_DIFF", None)`) so git uses its built-in diff.
Regression test: `tests/test_truth_regressions.py::VerificationRecheckEnvTests`
spins up a temp repo, deletes a tracked file, and asserts `git diff` under the
recheck env returns a real deletion patch. Suite: 880 passed. Accepted.

### Finding — pure deletions are awkward to prove

Runtime recheck cannot observe a removed file: `verification_recheck.required`
equals `runtime_verification_sufficient`, and sufficiency needs a `changed_file`
that still exists on disk. A pure deletion therefore forces the fallback prose
surfaces (`readback` / `scenario_proof`), which Synrail names explicitly. Module 2
was closed that way. Worth a dedicated deletion-disposition proof path later
(backlog, not this pass).

### B (done) — Module 3, separate advisory from blocking output

Completed on 2026-07-12. The initial handoff assumption was corrected during
reproduction: `PATH_SCOPE_VIOLATION` is a blocking diagnostic, not an advisory.
The exact out-of-root `--target-path` stops before closure, while a spine-only
out-of-root path exposed the real historical class: a failed child could reuse a
prior accepted report.

Landed:

- one canonical CLI/spine orchestration path-scope map;
- stale report invalidation before runtime validation and orchestration;
- human `Status: Blocked` output plus one machine JSON object with
  `accepted: false` and `closure_evaluated: false`;
- fail-closed handling for malformed report surfaces;
- independent live-git plus proof-backed scope derivation, so caller-supplied
  `--changed-file` / `--allowed-scope-path` claims cannot hide another dirty file;
- regression coverage for the accepted-then-path-failure sequence, map drift,
  report corruption, scope-claim spoofing, and default/dev rendering.

Final local verification for this tranche is recorded in its PR rather than
retroactively changing the historical 2026-07-11 session counts above.
