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

## 0.1.2 — 2026-06-11

- Added the temporary AWS prompt-challenge inspector experiment.

## 0.1.0-alpha — 2026-05-06

- First public local false-green proof-gate alpha.
