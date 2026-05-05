# Synrail Post-Fix Execution Roadmap

Date: 2026-05-03  
Base commit: `672758e Complete Synrail post-audit hardening tranche`  
Purpose: implementation-ready roadmap for the next Claude/Codex pass after the post-fix audit.

## Operating Rule

Do not broaden product scope while executing this roadmap. The goal is not to add more proof surfaces. The goal is to make the current trust kernel harder to game, make external alpha setup boring, and collect better proof of usefulness.

Every implementation slice must end with:

1. A regression test that fails on `672758e` and passes after the change.
2. A focused test command.
3. `python3 -m unittest discover -s tests` before handoff.
4. A short summary naming files changed and exact risk closed.

## Priority Order

1. `P1-A`: Scope verification command operands.
2. `P1-B`: Make live closure freshness mandatory for acceptance.
3. `P2-A`: Thread real trusted roots through artifact consistency hash checks.
4. `P2-B`: Make external install/preflight path boring.
5. `P2-C`: Turn `init-ci` from adapter-only into an optional workflow scaffold.
6. `P2-D`: Strengthen generated agent policies around non-accepted Synrail results.
7. `P3-A`: Prepare empirical external alpha ledger and demo path.
8. `P3-B`: Public README/demo cleanup.
9. `P3-C`: Structural CLI cleanup only after trust and alpha UX are stable.

---

## P1-A: Scope Verification Command Operands

### Problem

`verification_recheck_result()` validates the executable name and fingerprints `changed_file`, but it does not validate file operands passed to allowlisted commands. Today this can pass:

```json
{
  "changed_file": "safe.txt",
  "verification_command": "cat /tmp/outside_secret.txt",
  "verification_result": "outside-secret\n"
}
```

Local proof from audit:

```text
executed=True, command_allowed=True, matched=True
stdout_snippet=outside-secret
```

This weakens the claim that closure recheck proves the project surface.

### Files

Primary:

- `tools/reference/synrail_bundle_v0.py`
- `tests/test_truth_regressions.py`

Possible helper reuse:

- `tools/reference/synrail_path_scope_v0.py`

### Implementation Plan

1. Add a command-shape parser inside `synrail_bundle_v0.py`.
2. Keep executable allowlist narrow: `grep`, `cat`, `head`, `tail`, `git`.
3. Validate file operands for each allowed executable before `subprocess.run()`.
4. Reject out-of-root operands before execution with:

```json
"skip_reason": "command_path_out_of_scope"
```

5. Reject command shapes that cannot be safely interpreted with:

```json
"skip_reason": "command_shape_unsupported"
```

6. If `changed_file` is present, require the verification command to reference either:

- the `changed_file`, or
- an explicitly proven per-file provenance target from the current record.

7. Keep shell pipelines unsupported. Do not add `curl`, `python3`, `bash`, `sh`, `node`, `npm`, or arbitrary command execution.

### Command Parsing Rules

`cat`:

- Allow: `cat changed.txt`
- Allow: `cat ./changed.txt`
- Reject: `cat /tmp/outside.txt`
- Reject: `cat ../outside.txt`
- Reject if no file operands.

`head` / `tail`:

- Allow common numeric options: `-n 5`, `-n5`, `-c 20`, `-c20`.
- Validate remaining file operands.
- Reject out-of-root operands.
- Reject stdin-only commands.

`grep`:

- Allow simple shape: `grep [safe options] PATTERN FILE...`.
- Safe options can include `-n`, `-C NUM`, `-A NUM`, `-B NUM`, `-i`, `-F`, `-E`.
- Validate all file operands.
- Reject if no file operand.
- Reject out-of-root operands.

`git`:

- Keep minimal. Allow only known read-only subcommands already used by Synrail: `diff`, `show`, `log`.
- Do not treat revision strings as filesystem paths.
- If pathspec separator `--` is present, validate all following pathspecs that look like paths.
- Reject absolute out-of-root pathspecs.

### Regression Tests

Add to `tests/test_truth_regressions.py`:

1. `test_recheck_rejects_cat_outside_project_operand`
2. `test_recheck_rejects_grep_outside_project_operand`
3. `test_recheck_rejects_mixed_safe_and_unsafe_operands`
4. `test_recheck_accepts_cat_changed_file_inside_project`
5. `test_recheck_accepts_grep_changed_file_inside_project`
6. Optional: `test_recheck_rejects_stdin_only_cat`

Each test should assert:

- out-of-root command does not execute or does not match,
- `command_allowed` may be true for the executable, but `executed` should be false if operands are invalid,
- `skip_reason == "command_path_out_of_scope"` for out-of-root operands.

### Acceptance Criteria

- The local proof above no longer passes.
- Existing legitimate grep/cat/head/tail/git recheck tests still pass.
- Full suite passes.

### Focused Test Command

```bash
python3 -m unittest tests.test_truth_regressions
python3 -m unittest discover -s tests
```

---

## P1-B: Make Live Closure Freshness Mandatory For Acceptance

### Problem

The CLI path sets `_state_file` and `_bundle_file`, so freshness is live-rechecked in normal `synrail check`. But direct `build_verdict()` calls can still evaluate closure freshness in non-live mode if those hidden file paths are absent.

That makes the kernel easier to misuse in future internal integrations.

### Files

Primary:

- `tools/reference/synrail_closure_v0.py`
- `tests/test_truth_regressions.py`
- `tests/test_gate_units.py`

### Implementation Plan

1. In `build_verdict()`, compute:

```python
live_freshness_available = bool(state.get("_state_file") and bundle.get("_bundle_file"))
```

2. For a `COMPLETE` bundle that reaches the freshness gate, reject if live freshness is unavailable.

Recommended reason:

```text
CLOSURE_FRESHNESS_NOT_LIVE
```

3. Set:

```json
"closure_status": "REJECTED"
"next_allowed_transition": "PROOF_BUNDLE_REPAIR"
"narrow_next_safe_step": "rerun closure through the live artifact path so freshness can be verified"
```

4. Only allow non-live freshness in explicitly named tests/modes if they do not produce `ACCEPTED`.

5. Confirm `main()` still sets `_state_file` and `_bundle_file` before calling `build_verdict()`.

### Regression Tests

Add:

1. `test_build_verdict_rejects_complete_bundle_without_live_freshness_files`
2. `test_build_verdict_accepts_complete_bundle_with_live_freshness_files`
3. `test_closure_certificate_not_issued_as_accepted_when_freshness_not_live`

### Acceptance Criteria

- Direct in-memory `build_verdict()` cannot return `ACCEPTED` without live file bindings.
- Normal CLI closure still accepts valid runs.
- Full suite passes.

### Focused Test Command

```bash
python3 -m unittest tests.test_gate_units tests.test_truth_regressions
python3 -m unittest discover -s tests
```

---

## P2-A: Thread Real Trusted Roots Through Artifact Consistency Hash Checks

### Problem

`compare_hash_field()` now fails closed on missing source artifacts, but its path validation is still partly self-rooted:

- `artifact_root=source_path.parent`
- `project_root=Path.cwd().resolve()`

This catches some symlink cases, but it does not prove the source belongs to the current run's trusted artifact/project roots.

### Files

Primary:

- `tools/reference/synrail_artifact_consistency_v0.py`
- `tests/test_truth_regressions.py`

Possible helper:

- `tools/reference/synrail_path_scope_v0.py`

### Implementation Plan

1. Add explicit `project_root` and `artifact_root` parameters to `compare_hash_field()`.
2. Pass trusted roots from the artifact-consistency entrypoint/build path.
3. For source paths from `closure_freshness_binding`, validate that they are inside allowed roots.
4. If a hash-bound source path is outside allowed roots, mark artifact stale/corrupt.

Recommended detail:

```text
closure_certificate refers to out-of-scope source artifact for final_result_sha256
```

5. Avoid deriving the trusted root from the untrusted source path itself.

### Regression Tests

Add:

1. `test_artifact_consistency_rejects_certificate_final_result_hash_outside_artifact_root`
2. `test_artifact_consistency_rejects_run_embedded_certificate_outside_hash_source`
3. `test_artifact_consistency_accepts_certificate_hash_source_inside_artifact_root`

### Acceptance Criteria

- A certificate cannot point `final_result_sha256` at `/tmp/outside` and pass consistency just because the hash matches.
- Existing stale/missing source tests still pass.
- Full suite passes.

### Focused Test Command

```bash
python3 -m unittest tests.test_truth_regressions
python3 -m unittest discover -s tests
```

---

## P2-B: Make External Alpha Installation Boring

### Problem

Live external testing showed that users and agents still get confused by:

- missing `git`,
- wrapper/PATH ambiguity,
- when to start a controlled run,
- what to do after `Proof Invalid`,
- whether non-accepted Synrail output still means task complete.

### Files

Primary:

- `tools/reference/synrail_cli_v0.py`
- `tools/reference/synrail_commands_v0.py`
- `tools/reference/synrail_agent_adoption_v0.py`
- `docs/core/FIRST_RUN_GUIDE.md`
- `tests/test_controlled_start_smoke.py`
- `tests/test_agent_adoption.py`
- `tests/test_install_smoke.py`

### Implementation Plan

1. Add `synrail preflight` or `synrail doctor-install`.
2. It should check:

- Python version,
- `git` availability,
- whether current directory is a git repo,
- whether there is a parent git repo above current project root,
- whether artifact root is writable,
- whether `synrail` wrapper is available,
- whether repo-native `python3 alpha.py` fallback is available.

3. Output should be human-readable by default and JSON with `--json`.
4. If git is missing, say exactly:

```text
Git is not installed. Synrail can still use structured diff_provenance, but git_diff and restore coverage will be weaker. Install git for the normal path.
```

5. Update `FIRST_RUN_GUIDE.md` with a first command:

```bash
synrail preflight
```

or:

```bash
python3 alpha.py preflight
```

6. Keep this as a diagnostic surface, not a new closure requirement.

### Regression Tests

Add:

1. `test_preflight_reports_git_missing_without_crashing`
2. `test_preflight_reports_repo_native_alpha_fallback`
3. `test_preflight_json_shape_is_machine_readable`
4. `test_first_run_guide_mentions_preflight_and_git_missing_path`

### Acceptance Criteria

- Fresh user can run one command and understand whether Synrail is installed and usable.
- Missing git produces a clear warning, not a confusing proof failure later.
- Full suite passes.

### Focused Test Command

```bash
python3 -m unittest tests.test_controlled_start_smoke tests.test_install_smoke tests.test_claim_validation_pack
python3 -m unittest discover -s tests
```

---

## P2-C: Turn `init-ci` Into A Real CI Lane

### Problem

`init-ci` creates a composite action adapter, but not a complete workflow. A user may expect one command to produce a runnable GitHub Actions setup.

### Files

Primary:

- `tools/reference/synrail_commands_v0.py`
- `tools/reference/synrail_cli_v0.py`
- `tests/test_agent_adoption.py`
- `docs/core/FIRST_RUN_GUIDE.md`

### Implementation Plan

1. Add option:

```bash
synrail init-ci --workflow
```

2. Keep default behavior adapter-only, but wording must say clearly:

```text
Adapter only: add a workflow that calls uses: ./.github/actions/synrail-check, or rerun with --workflow.
```

3. `--workflow` should write:

```text
.github/workflows/synrail-check.yml
```

4. Workflow should:

- run on `pull_request` and `workflow_dispatch`,
- checkout repo,
- run the local composite action,
- avoid mutating proof artifacts by default.

5. If workflow exists and differs, block unless `--force`, with backup behavior matching adapter writing.

### Regression Tests

Add:

1. `test_init_ci_workflow_writes_composite_action_and_workflow`
2. `test_init_ci_default_says_adapter_only`
3. `test_init_ci_workflow_blocks_existing_different_file_without_force`
4. `test_init_ci_workflow_force_creates_backup`

### Acceptance Criteria

- `synrail init-ci --workflow` leaves a runnable GitHub Actions workflow.
- Default `init-ci` no longer sounds like full CI setup.
- Full suite passes.

### Focused Test Command

```bash
python3 -m unittest tests.test_agent_adoption tests.test_controlled_start_smoke
python3 -m unittest discover -s tests
```

---

## P2-D: Strengthen Generated Agent Policies Around Non-Accepted Results

### Problem

External agent testing showed the dangerous behavior: agent sees `Proof Invalid` or `Rejected`, but still tells the human the task is complete.

### Files

Primary:

- `tools/reference/synrail_agent_adoption_v0.py`
- `tests/test_agent_adoption.py`
- `docs/core/FIRST_RUN_GUIDE.md`

### Implementation Plan

1. Add one strong rule to all generated agent policy files:

```text
Only `Status: Accepted` means the task may be reported as complete. If Synrail returns Proof Invalid, Rejected, Blocked, or any repair step, do not summarize the task as done; run the named repair step or report the exact Synrail blocker.
```

2. Make sure this appears in:

- `AGENTS.md` / Codex/Cursor path,
- `GEMINI.md`,
- `CLAUDE.md`.

3. Add a short run-loop command sequence:

```bash
synrail start "TASK" --artifact-root ./.synrail
# work
synrail check --artifact-root ./.synrail
# only stop on Status: Accepted
```

4. Avoid expanding policy into a giant document.

### Regression Tests

Add:

1. `test_generated_agent_policy_forbids_done_after_non_accepted_check`
2. `test_init_agent_single_file_contains_non_accepted_rule`
3. `test_install_agent_files_contains_non_accepted_rule_for_all_agents`

### Acceptance Criteria

- Generated files contain the non-accepted rule exactly once.
- Existing append/update behavior still works.
- Full suite passes.

---

## P3-A: Prepare Empirical External Alpha Ledger

### Problem

Synrail has much stronger trust tests, but product usefulness is still under-proven. We need external/live task data separate from curated benchmark fixtures.

### Files

Suggested:

- `docs/review/EXTERNAL_ALPHA_LEDGER_2026-05.md`
- `docs/review/EXTERNAL_ALPHA_RUN_TEMPLATE_001.md`
- Maybe `fixtures/external_alpha_runs/README.md`

### Implementation Plan

1. Create a template for live run records.
2. Track:

- task class,
- repo type,
- agent used,
- whether Synrail was installed before,
- time to first blocker,
- time to accepted closure,
- false-done prevented,
- operator confusion moments,
- manual interventions,
- final verdict.

3. Keep empirical data separate from curated benchmark JSON.
4. Add a claim-validation test that docs clearly distinguish curated fixtures from empirical external runs.

### Acceptance Criteria

- There is a repeatable place to record 10 external runs.
- No curated benchmark claim is presented as empirical external proof.

---

## P3-B: Public README / Demo Cleanup

### Problem

Synrail is technically stronger than it looks from the first public reading path. The product still needs a short false-green demo.

### Files

Primary:

- `README.md`
- `docs/core/FIRST_RUN_GUIDE.md`
- maybe `examples/false-green-demo/README.md`

### Implementation Plan

1. Rewrite top README around:

```text
Synrail catches false-green AI-agent work before you accept it.
```

2. Add a short terminal transcript:

```text
Agent: tests passed
Synrail: Status: Proof Invalid
Reason: verification command not executed / freshness mismatch
Next: repair final_result.json
```

3. Add `When to use / When not to use` section.
4. Keep archival reviews out of the first reading path.

### Acceptance Criteria

- A new reader understands Synrail in 30 seconds.
- README does not overclaim broad production readiness.

---

## P3-C: Structural Cleanup After Trust Work

### Problem

The CLI split improved structure, but command composition is still callback-heavy.

### Files

Primary:

- `tools/reference/synrail_cli_v0.py`
- `tools/reference/synrail_commands_v0.py`
- `tools/reference/synrail_controlled_start_shell_v0.py`
- `tools/reference/synrail_public_shell_v0.py`

### Implementation Plan

1. Do not start this until P1-A, P1-B, and P2-B are complete.
2. Introduce a small `CommandContext` object for shared dependencies.
3. Replace long callback parameter lists gradually.
4. One command group per commit.
5. No behavior changes.

### Acceptance Criteria

- Full suite green before and after every extraction.
- CLI file shrinks without reducing readability in extracted modules.

---

## Recommended First Claude Prompt

Use this exact instruction for the next implementation agent:

```text
Work in /Users/usbdick/Documents/New project/synrail on branch main. Base commit is 672758e. Do not broaden Synrail scope. Implement only Phase 0 from docs/review/POST_FIX_EXECUTION_ROADMAP_2026-05-03.md.

Start with P1-A: scope verification command operands in tools/reference/synrail_bundle_v0.py. Add adversarial tests that fail on 672758e for cat/grep reading absolute out-of-project files. Keep the executable allowlist narrow; do not add python3/bash/curl/node/npm. Then implement P1-B: make closure acceptance require live freshness bindings. Then P2-A: thread real roots into artifact consistency hash checks.

After each slice run focused tests. Before handoff run:
python3 -m py_compile alpha.py tools/reference/*.py
python3 -m unittest discover -s tests

Return changed files, exact tests run, and whether every Phase 0 acceptance criterion is met. Do not claim completion if Synrail is not test-clean.
```

## Do Not Do Yet

- Do not add new proof artifact families.
- Do not broaden command execution allowlists.
- Do not make runtime-helper a closure recheck command source.
- Do not rewrite the CLI architecture before Phase 0 and external alpha UX are stable.
- Do not market Synrail as broad production-grade until empirical external runs exist.

