# Synrail Audit #3 Remaining Roadmap

Date: 2026-04-25
Updated: 2026-04-30 after local post-audit P0 tranche
Base audit: docs/review/AUDIT_3_2026-04-25.md
Current baseline: main after `8b798aa` plus local P0 hardening changes pending commit

Purpose: this is the execution/status brief for the remaining Opus Audit #3 work. It separates already-closed audit items from the next real risk-bearing work so future agents do not reopen solved items or push stale roadmap text.

## Closed After Audit #3

Closed on main by `8b798aa`:

- `FIX-PYTHON3`: `python3` was removed from `VERIFICATION_RECHECK_ALLOWED_BINARIES`.
- `FIX-EMPTY-RECHECK`: required runtime verification rejects closure when recheck is skipped or not executed.
- `FIX-HASH-CLI`: final-result integrity hashes are no longer accepted through CLI hash arguments; bundle reads state-bound hash context from Synrail-controlled files.

Closed by the local post-audit P0 tranche:

- `P0.1 / FIX-SUBSTRING`: verification recheck now uses exact normalized matching instead of `expected in stdout`.
- `P0.2 / FIX-STATE-CRASH`: corrupted `.synrail/state.json` no longer crashes `synrail start` with a traceback.
- `P0.3 / FIX-DEPLOY-GUARD`: deploy guard now fails loudly on corrupted deploy receipt or state JSON.
- `P0.4 / FIX-DOCTOR-WARNING`: doctor override use is surfaced early through doctor records and human-facing CLI output before closure summary.

Regression guardrails:

- Do not reintroduce `python3`, shell, bash, node, perl, ruby, curl, or any arbitrary-code executor into verification recheck.
- Do not restore `--last-known-final-result-hash` or `--starter-final-result-hash` as public/user-controlled CLI inputs.
- Do not allow `verification_recheck.required == true` with `executed == false` to reach `ACCEPTED`.
- Do not restore raw substring matching in recheck.
- Do not let corrupted JSON be converted into an ambiguous empty value.
- Keep the full unittest suite green and add targeted tests for every change below.

## Remaining P1: Path And File-Surface Safety

### P1.1: Add Path Scope Validation For User-Provided File Arguments

Problem:

- Audit #3 flags path traversal through `--artifact-path`, `--helper-path`, `--state-file`, and related file arguments.

Files:

- `tools/reference/synrail_cli_v0.py`
- `tools/reference/synrail_spine_v0.py`
- `tools/reference/synrail_doctor_v1.py`
- Any helper modules that open CLI-provided paths

Implementation:

- Define an allowlist policy:
  - state/proof artifacts must be inside the current artifact root unless explicitly documented otherwise;
  - project files must resolve inside project root or repo root;
  - helper/artifact paths must not escape their declared root.
- Use `.expanduser().resolve()` before scope checks.
- Reject `..` traversal and symlink escapes.
- Return a bounded user-facing error instead of a traceback.

Required tests:

- `../../outside.json` is rejected for state/proof paths.
- Symlink from artifact root to outside target is rejected.
- Normal repo-relative paths still work.

Definition of done:

- No user-provided file path can silently escape artifact root/project root policy.

### P1.2: Harden Doctor TOCTOU And Symlink Handling

Problem:

- Audit #3 flags `exists()` then later use patterns in doctor probes.
- Credential probe uses `expanduser()` without full symlink resolution.

Files:

- `tools/reference/synrail_doctor_v1.py`
- `tests/test_gate_units.py`

Implementation:

- Resolve paths before use.
- Avoid `exists()` then later open/run when possible; prefer open/read or subprocess invocation on the already-resolved path.
- Reject symlinks that escape allowed roots for credential/helper/artifact probes.
- Make failure notes explicit: `PATH_OUT_OF_SCOPE`, `SYMLINK_ESCAPE`, or similar.

Required tests:

- Credential/helper symlink to outside workspace is rejected.
- Missing path still reports the current expected failure.
- Valid resolved path still passes.

Definition of done:

- Doctor path probes are no longer relying on unchecked path strings or silent symlink traversal.

## Remaining P2: Adversarial Proof Quality

### P2.1: Build Dedicated Attack Pack With At Least 10 Cases

Problem:

- Audit #3 says proof guard is still mostly syntactic.
- Empty/unexecuted recheck and substring matching are now blocked, but we still need a dedicated adversarial corpus to prevent future regressions.

Files:

- `tests/test_truth_regressions.py` or a new `tests/test_proof_attack_pack.py`
- Optional fixtures under `fixtures/proof_attack_pack_001/`

Attack cases to include:

- Thin readback with concrete-looking line number but no real runtime verification.
- Scenario proof with command label but fabricated observed output.
- Synonym bypasses of vacuous phrases.
- Paraphrased command confirmation that mentions a file but no observed content.
- Correct-looking diff provenance but changed file missing.
- Correct-looking diff provenance with command not in allowlist.
- Correct-looking diff provenance with allowed command but mismatched output.
- Correct-looking proof with hostile substring output.
- Already-satisfied claim with no real observation.
- Multi-file claim where only one file has provenance.

Expected behavior:

- Cases with missing/unexecuted/mismatched recheck must be `REJECTED` or structurally/semantically incomplete.
- Cases with prose-only proof must not reach `ACCEPTED`.
- Positive controls with real repo-relative files and exact recheck should still pass.

Definition of done:

- At least 10 adversarial cases exist and are named clearly as adversarial, not snapshot tests.

### P2.2: Strengthen Multi-File Provenance Consistency

Problem:

- A single `diff_provenance.changed_file` can prove one changed file, but multi-file changes need per-file evidence or parsed patch-backed coverage.

Files:

- `tools/reference/synrail_bundle_v0.py`
- `tools/reference/synrail_cli_v0.py`
- `tests/test_truth_regressions.py`

Implementation:

- For `modified_files` length > 1, require either:
  - patch-shaped `git_diff` covering every modified file, or
  - per-file provenance array, or
  - a strict single-file task classification.
- Do not let prose or `modified_files` alone expand trusted scope.

Required tests:

- Two modified files, one provenance record: not accepted.
- Two modified files, patch covers both and verification is valid: accepted if other gates pass.
- Self-declared `modified_files` cannot whitelist unrelated dirty paths.

Definition of done:

- Non-override scope remains proof-backed, not self-declared.

## Remaining P3: Evidence Honesty And Runtime Instrumentation

### P3.1: Complete Timestamps In State

Status note:

- `start_timestamp_utc`, `closure_timestamp_utc`, and `check_count` exist in state/spine.
- Treat this as implemented unless a fresh audit finds a missing edge case.

Recommended regression tests:

- Start writes start timestamp.
- Accepted closure writes closure timestamp.
- Rejected check does not write closure timestamp.

### P3.2: Improve Benchmark Provenance Mix

Problem:

- `data_provenance` exists mostly as `curated_local_estimate`.
- Audit #3 asks for clearer separation between curated, pressure synthetic, and external empirical records.

Files:

- benchmark fixtures under `fixtures/`
- benchmark docs under `docs/core/` and `docs/review/`
- tests for benchmark pack reads

Implementation:

- Keep current curated estimates but label them honestly.
- Add at least one `pressure_synthetic` record if available.
- Reserve `external_empirical` only for actual outside-user run data.
- Aggregate and expose `provenance_mix` in the summary if not already complete.

Required tests:

- Benchmark summary reports provenance mix.
- No fixture with hand-curated data claims `external_empirical`.

Definition of done:

- Economics claims are machine-readable and provenance-honest.

## Remaining P4: Narrow Tech Debt, Only After Trust Work

### P4.1: Continue Shared JSON IO Adoption

- `synrail_io_v0.py` exists, but local `load_json/save_json` duplicates remain.
- Migrate modules in small batches only, preserving behavior differences intentionally.

### P4.2: Continue Policy Renderer Dedup

- Policy rendering is partially deduplicated, but one policy block path still drifts separately.
- Fold the remaining separate renderer into the parameterized renderer only if behavior can stay stable or intentionally updated.

### P4.3: First Real CLI Split

- CLI remains a large monolith.
- Split only after P1/P2 are stable.
- Extract low-risk helpers first, not command behavior.

## Recommended Next Execution Order

1. P1.1 path scope validation.
2. P1.2 doctor symlink/TOCTOU hardening.
3. P2.1 adversarial attack pack.
4. P2.2 multi-file provenance consistency.
5. P3.2 benchmark provenance mix.
6. P4 tech debt only after trust-path tests are green.

## Required Verification Before Handoff Back

```bash
python3 -m py_compile tools/reference/*.py tests/*.py
python3 -m unittest tests.test_truth_regressions tests.test_gate_units tests.test_controlled_start_smoke tests.test_deploy_gate
python3 -m unittest discover -s tests
git diff --check
```

Report:

- exact files changed,
- which roadmap items were completed,
- which tests were run and their result,
- any intentionally deferred item with reason,
- whether any user-facing command output changed.

