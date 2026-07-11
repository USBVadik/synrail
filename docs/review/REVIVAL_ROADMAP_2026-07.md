# Synrail Revival Roadmap

Date: 2026-07-11
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
- [ ] **Module 3 — Separate advisory from blocking output.** The one known live
      finding (`SERVER_GEMINI_ALPHA_FINDING_001.md`) is that a run can print
      `PATH_SCOPE_VIOLATION` and `Status: Accepted` in the same user-facing
      output. Reproduce first, then make advisory diagnostics visually distinct
      from blocking errors so a tester is not confused about whether the run is
      clean. Scope carefully; may split into its own runs.

## Track B: Unblock External Signal

The actual strategic priority from `ROADMAP.md` P0.

- [x] **Module 4 — First external-tester repro checklist.** Lower the friction
      for 3-5 real users of Claude Code / Cursor / Codex / Aider to run the demo
      plus one real task and file feedback, using the existing
      `FIRST_TESTER_PROTOCOL_001.md` and issue templates.
- [ ] Recruit and run 3-5 external testers.
- [ ] Sharpen the one-sentence positioning against the now-crowded CI-gate field.
- [ ] Classify each report as product- / operator- / harness-owned before any
      kernel change.

## Deeper Backlog (Only After External Signal)

Do not start these until Track B produces signal that the wedge is worth its
overhead. Sourced from `LAST.md`, unchanged in intent:

- everyday-economics accounting as the primary cost metric
- behavioral cheapening (optional prose surfaces stop appearing by default)
- proof-independence attack pack (mutation / adversarial / unseen shapes)
- change-impact invalidation for cheaper retry
- shell pruning to felt-thin first loop

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

### B (handoff) — Module 3, separate advisory from blocking output

Not started; still the next code target. Reproduce first (the live finding is
`SERVER_GEMINI_ALPHA_FINDING_001.md`, where `--target-path` resolved outside the
repo). Located seam in `tools/reference/synrail_cli_v0.py`:

- `~line 2994` — blocking path prints a raw `PathScopeValidationError` JSON and returns 2.
- `~line 3039` — `validate_check_like_paths` is called without a try/except wrapper.
- `~line 1872` — `maybe_print_doctor_override_warning` is the clean `Warning:` renderer
  that advisory diagnostics should be routed through.

Plan: build an out-of-repo path reproduction harness plus a regression test, then
route advisory path-scope diagnostics through the `Warning:` renderer so they read
as advisory, never as a blocking error sitting next to `Status: Accepted`.
