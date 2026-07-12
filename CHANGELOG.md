# Changelog

All notable changes to the public Synrail alpha are recorded here.

## Unreleased — 0.1.3.dev0

- Make closure freshness binding validation fail closed.
- Keep named `final_result.json` repairs editable until accepted closure, then
  bind the accepted hash from the live-rechecked closure surface.
- Synchronize the proof-bundle schema with the emitted runtime bundle.
- Retire the contest-only AWS inspector and separate fingerprint commands.
- Refresh audited development dependencies and add scheduled dependency checks.
- Move vulnerability reporting to a private-first path.
- Replace the canned false-green transcript script with a real disposable
  `Proof Invalid` to `Accepted` CLI loop.
- Fail closed on path-scope errors before rendering closure, and prevent a
  failed check from reusing a prior accepted report.
- Derive observed-safe dirty-worktree scope only from live git observation and
  proof-backed provenance, never from caller-supplied scope claims.
- Position Synrail explicitly as a local acceptance gate that complements CI and
  AI code review instead of competing with either one.
- Make first-tester runs repo-clean by default and require ownership triage before
  an alpha report can trigger a kernel change.
- Move repo-owned and generated GitHub workflows to Node 24 action releases.
- Add a fail-closed `synrail record` happy path for one tracked changed file:
  capture a real patch plus recheckable evidence without hand-authoring JSON,
  while leaving acceptance exclusively to `synrail check`.
- Keep `--ephemeral --project-root` usable across status, proof guidance,
  templates, record, check, and cleanup, and hide internal orchestration flags
  from public `check --help`.
- Harden every Git subprocess against local execution config: inherited config
  injection, hooks, fsmonitor, external diff/textconv, and clean/smudge/process
  filters are neutralized; filtered workspace mutation fails closed. Reject
  allowed recheck binaries resolved from inside the target repository.
- Bind the thin recorder to the clean worktree and `HEAD` observed at `start`,
  then rebind its saved patch to the live worktree during `check`, so
  pre-existing or post-record edits cannot be relabeled as current-run proof.

## 0.1.2 — 2026-06-11

- Added the temporary AWS prompt-challenge inspector experiment.

## 0.1.0-alpha — 2026-05-06

- First public local false-green proof-gate alpha.
