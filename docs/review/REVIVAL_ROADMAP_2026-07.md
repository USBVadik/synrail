# Synrail Revival Roadmap

Date: 2026-07-11
Base commit: `d73b371 Optimize small Synrail hot paths`
Purpose: restart bounded development after a pause, without broadening scope.

This roadmap is the current source of truth for the revival pass. Older sprint
plans (`POST_FIX_EXECUTION_ROADMAP_2026-05-03.md`, `LAST.md`, `Priority.md`)
stay valid as deeper technical backlog, but this file governs what happens next.

## Situation

- Development stalled around 2026-06-11 after the AWS-inspector hackathon work.
- The kernel is healthy: full test suite is green (879 tests + 7 subtests),
  Ruff is clean.
- The project was frozen at the correct decision gate from `ROADMAP.md`:
  stop growing the kernel, go collect external signal. That step was never run.
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

## Track A: De-rust And De-risk First Impression

Small, safe, high-certainty hygiene that a returning maintainer and a fresh
external tester both benefit from.

- [x] **Module 1 — Align package version.** `pyproject.toml` says `0.1.0` while
      the latest shipped git tag is `v0.1.2`. Bump package metadata to `0.1.2`
      so install metadata does not claim to be older than what was released.
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
