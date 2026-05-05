# Synrail Post-Fix Audit And Next Roadmap

Date: 2026-05-03  
Branch: `main`  
Audited commit: `672758e Complete Synrail post-audit hardening tranche`  
Audit mode: adversarial review after the post-audit hardening tranche

## Executive Verdict

Synrail is materially stronger than the previous audit baseline. The latest tranche closed the immediate restore regression, added a first-class `closure_certificate_v0`, tightened artifact freshness, improved path/symlink/TOCTOU checks, added session timestamps/counters, and introduced first-step integration surfaces through `init-agent` and `init-ci`.

Current verdict: `CONCERNS`, not `BLOCK`.

There is no test-suite blocker at the audited commit. The remaining issues are not "the product does not work"; they are the next trust-boundary and product-integration gaps that matter if Synrail is going to move from a strong local kernel to a reliable external alpha.

## Verification Snapshot

- `git status --short --branch`: clean, `main...origin/main`
- `python3 -m py_compile alpha.py tools/reference/*.py`: passed
- `git diff --check HEAD~1..HEAD`: passed
- `python3 -m unittest discover -s tests`: `841 tests`, `OK`

## What Is Now Earned

1. Restore is no longer red in the full suite.
2. `closure_certificate_v0` exists as a real artifact surface, not just prose.
3. Closure freshness binding rejects stale/missing required artifacts in the normal CLI path.
4. Artifact consistency no longer silently passes missing hash-bound sources.
5. One-sided freshness and recheck snapshots are now treated as stale.
6. Doctor/path surfaces reject many direct symlink and ancestor-symlink cases.
7. Runtime helper is now framed as manual runtime evidence, not as a `verification_command` source.
8. `init-agent --agent claude|gemini|codex|cursor` exists.
9. `init-ci` creates a bounded composite GitHub Action adapter.
10. Session timestamps and `check_count` are now represented in state and downstream artifacts.

## Adversarial Findings

### Finding 1: Recheck allowlist does not scope command file operands

Severity: `P1`

Relevant code:
- `tools/reference/synrail_bundle_v0.py:196-250`

The recheck path validates the executable name and fingerprints `changed_file`, but it does not validate the file operands passed to the allowed command. That means an allowed binary such as `cat`, `head`, `tail`, or `grep` can still be pointed at an out-of-project file. The command executes under `project_root`, but absolute path operands still work.

Observed local proof:

```text
verification_command: cat /tmp/.../outside_secret.txt
changed_file: safe.txt
result: executed=True, command_allowed=True, matched=True
stdout_snippet: outside-secret
```

This does not give a remote attacker new shell execution, but it weakens the claim that closure recheck is a tightly scoped project proof. A malicious or confused agent can turn recheck into a local file-reading oracle and then store the output in artifacts.

Required next step:

Restrict allowed command shapes, not only executable names.

Acceptance criteria:

- `grep`, `cat`, `head`, and `tail` may only read paths under the declared project/artifact scope.
- If `changed_file` is present, the command must reference that file or an explicitly proven per-file provenance target.
- Absolute paths outside the project/artifact roots reject with `verification_recheck.skip_reason = "command_path_out_of_scope"`.
- Add adversarial tests for `cat /tmp/outside`, `grep needle /tmp/outside`, and mixed safe+unsafe operands.

### Finding 2: Closure freshness can be evaluated without live file recheck in direct kernel calls

Severity: `P1`

Relevant code:
- `tools/reference/synrail_closure_v0.py:350-353`

The CLI path sets `_state_file` and `_bundle_file`, so `evaluate_closure_freshness_binding(..., live_recheck=True)` is used in normal closure. But `build_verdict()` itself only enables live recheck when those hidden paths are present. A programmatic or future internal caller can pass a self-attested freshness binding and get non-live freshness semantics.

This is not currently breaking the main CLI path, but it is a kernel-level trust footgun. The closure engine should fail closed when it cannot perform live freshness verification, unless an explicitly named offline/non-accepting mode is being used.

Required next step:

Make live freshness verification mandatory for `ACCEPTED`.

Acceptance criteria:

- If bundle status is `COMPLETE` but live freshness cannot be evaluated, closure returns `REJECTED` or `CLAIMED_NOT_ACCEPTED` with a named reason such as `CLOSURE_FRESHNESS_NOT_LIVE`.
- Unit tests cover direct `build_verdict()` calls without `_state_file`/`_bundle_file`.
- Existing tests that intentionally call the function in-memory must either add live file bindings or assert non-acceptance.

### Finding 3: Artifact consistency path validation is still partly self-rooted

Severity: `P2`

Relevant code:
- `tools/reference/synrail_artifact_consistency_v0.py:142-193`

`compare_hash_field()` now fails closed on missing sources, which is a real improvement. But its path-surface validation uses `source_path.parent` as the artifact root and `Path.cwd()` as the project root. That catches some symlink surfaces, but it does not prove the source path belongs to the actual run artifact root or project root.

Required next step:

Thread real `project_root` and `artifact_root` into hash comparison.

Acceptance criteria:

- `compare_hash_field()` receives explicit trusted roots from the artifact-consistency entrypoint.
- Hash-bound source paths outside the run's artifact/project roots are stale/corrupt.
- Add tests for a closure certificate whose `final_result_sha256` points at an out-of-root file with a matching hash.

### Finding 4: `init-ci` is an adapter, not a complete CI workflow

Severity: `P2`

Relevant code:
- `tools/reference/synrail_commands_v0.py:363-440`

`synrail init-ci` creates a composite action at `.github/actions/synrail-check/action.yml`. That is useful, but external users may reasonably expect "init CI" to leave them with a runnable workflow. Today it only gives them a call site hint.

Required next step:

Add an optional workflow scaffold or rename/framing that makes the current scope obvious.

Acceptance criteria:

- `synrail init-ci --workflow` writes `.github/workflows/synrail-check.yml`.
- The default output explicitly says "adapter only; add a workflow that calls it" if no workflow is created.
- Add a smoke test that generated workflow YAML calls `./.github/actions/synrail-check`.

### Finding 5: CLI split improved structure, but the composition seam is still fragile

Severity: `P2`

Relevant code:
- `tools/reference/synrail_cli_v0.py`
- `tools/reference/synrail_controlled_start_shell_v0.py`
- `tools/reference/synrail_public_shell_v0.py`
- `tools/reference/synrail_commands_v0.py`

The split is real, but it is still dependency-injection heavy: extracted command functions receive long lists of callbacks from the CLI monolith. This is better than one giant file, but a new contributor still has to trace behavior across several modules and callback names.

Required next step:

Stabilize command contexts before further splitting.

Acceptance criteria:

- Introduce a small `CommandContext` object for shared CLI dependencies.
- Move only behavior-preserving command groups after tests are green.
- Do not prioritize this above trust-boundary and external-alpha work.

## Next Roadmap

### Phase 0: Close The Remaining Trust Footguns

Goal: make the post-hardening trust claims harder to attack.

1. Scope verification command operands.
2. Make live closure freshness mandatory for acceptance.
3. Thread real project/artifact roots through artifact consistency hash checks.
4. Add adversarial tests for out-of-root command operands and out-of-root hash-bound certificate paths.

Exit criteria:

- Full suite green.
- New adversarial tests fail on `672758e` and pass after the fix.
- No acceptance path relies on self-attested freshness when live file bindings are unavailable.

### Phase 1: Make External Alpha Installation Boring

Goal: reduce the support burden seen in live friend/Hetzner tests.

1. Add `synrail doctor-install` or `synrail preflight` that checks `git`, Python version, executable wrapper, current repo root, and artifact root writability.
2. Upgrade `FIRST_RUN_GUIDE` around no-git and PATH/wrapper fallback.
3. Add a short "if Synrail says Proof Invalid, do not report done" agent-policy line to every generated agent file.
4. Add an external-alpha smoke script that runs install, init-agent, start, check, and an expected non-green repair loop in a temp repo.

Exit criteria:

- A fresh tester can install and reach either `Accepted` or a named repair step without private hand-holding.
- Generated `GEMINI.md`/`CLAUDE.md` makes it harder for agents to stop after non-accepted `check`.

### Phase 2: Turn `init-ci` Into A Real CI Lane

Goal: make Synrail inspectable by non-local reviewers.

1. Add `synrail init-ci --workflow`.
2. Add docs showing minimal PR workflow usage.
3. Add a CI example fixture and a test that validates generated YAML.
4. Keep CI mode check-only; do not let CI mutate proof artifacts by default.

Exit criteria:

- A user can run one command and get a commit-ready GitHub Actions workflow.
- CI failure messages point back to the local bounded repair loop.

### Phase 3: Prove Product Usefulness Beyond Trust Mechanics

Goal: move from "Synrail blocks bad proof" to "Synrail is worth using."

1. Run 10 external/live tasks across at least 3 task classes:
   - small template/text fix
   - config/dependency change
   - small multi-file refactor
2. Measure:
   - time to first useful blocker
   - time to accepted closure
   - false-done prevented
   - operator confusion moments
   - number of manual interventions
3. Record results in a new empirical alpha ledger, clearly separated from curated fixtures.
4. Produce one public demo case where an agent claims done, Synrail rejects, repair happens, then Synrail accepts.

Exit criteria:

- At least 3 real runs show clear value over "manual checklist + tests".
- At least 1 run is allowed to be ugly/non-green and still tells a useful story.

### Phase 4: Product Shell And Public Positioning

Goal: make the project understandable in 30 seconds.

1. Rewrite README top section around the false-green problem.
2. Add a short terminal transcript or GIF-like asciinema-style example.
3. Add a "When to use / When not to use" page.
4. Move archival review docs out of the first reading path.

Exit criteria:

- A new visitor understands the product without reading the review archive.
- The first demo demonstrates a concrete prevented false accept.

### Phase 5: Structural Cleanup

Goal: lower future maintenance cost without destabilizing the kernel.

1. Introduce command context objects to reduce callback-heavy extracted command signatures.
2. Continue CLI split only after Phase 0 and Phase 1 are green.
3. Consolidate duplicate policy wording between agent adoption, first-run docs, and critic docs.
4. Add schema/migration handling for older local repair packets and certificates.

Exit criteria:

- CLI behavior remains unchanged under full suite.
- New contributors can locate command behavior without reading the whole CLI file.

## Current Score After This Audit

Technical trust maturity: `8.0/10`  
External alpha readiness: `7.0/10`  
Product usefulness proof: `5.5/10`  
Public/GitHub readability: `5.0/10`

The next quality jump will not come from adding more proof surfaces. It will come from tightening the remaining trust boundaries, making first-run adoption boring, and collecting empirical external runs that prove Synrail is worth its ceremony.

