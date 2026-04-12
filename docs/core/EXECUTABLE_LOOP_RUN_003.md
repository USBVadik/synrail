# Executable Loop Run 003

## Purpose

Record a third internal end-to-end run through the current executable `Synrail` stack on a hybrid middle-mode scenario.

This document exists so the repo can show a third reading beyond:

- `SYNRAIL_BETTER`
- `BASELINE_GOOD_ENOUGH`

The point of this run is to test whether the current stack can express a credible middle result rather than forcing every scenario into a cleaner verdict than the evidence supports.

## Scenario

- run id: `EXECUTABLE_LOOP_RUN_003`
- task class: `medium_risk_ambiguous_fix`
- scenario shape:
  - some ambiguity remains
  - one explicit artifact sanity check is available
  - the full governed path feels too expensive
  - the lightweight baseline feels a little too loose

## Artifacts

The run artifacts now live under:

- `fixtures/executable_loop_run_003/`

Included artifacts:

- `state.json`
- `doctor.json`
- `bundle.json`
- `closure.json`
- `comparison.json`
- `orchestration.json`
- `readback.txt`

The comparison fixtures used for this run are:

- `fixtures/comparison_input_hybrid_baseline_v0.json`
- `fixtures/comparison_input_hybrid_synrail_v0.json`

## What was executed

The run used the current executable stack:

1. `synrail_cli_v0.py init`
2. `synrail_cli_v0.py doctor`
3. `synrail_cli_v0.py bundle-check`
4. `synrail_cli_v0.py apply-bundle`
5. `synrail_cli_v0.py closure`
6. `synrail_cli_v0.py apply-closure`
7. `synrail_baseline_harness_v0.py`

## Observed path

### 1. Doctor path

Before proof assembly, the run emitted a green doctor record:

- verdict = `ACCEPTABLE_FOR_CORE_RUN`

This is important because the hybrid mode still keeps one explicit readiness check.

The doctor artifact now also reflects the stronger `v1` reading style:

- explicit clean execution input
- explicit artifact viability input
- bounded readiness without full heavy diagnostics

### 2. Bundle path

This run intentionally preserved only one artifact sanity check:

- `readback.txt` present
- `scenario_proof` absent

Observed result:

- proof bundle status = `PARTIAL`
- missing sections:
  - `scenario_proof`

This matches the intended hybrid discipline:

- not a full proof bundle
- but not a bluffing or purely narrative path either

### 3. Closure path

The closure engine emitted:

- closure status = `CLAIMED_NOT_ACCEPTED`
- blocking reason = `MISSING_PROOF_SECTIONS`
- next safe step = `rerun the scenario check against the attested target surface`

This is the most important behavior in the run.

The stack did not:

- pretend the available evidence was enough for accepted closure
- collapse back to a pure narrative judgment

It preserved a bounded stop/no-bluff posture.

### 4. Baseline comparison path

Using the hybrid comparison fixtures, the harness emitted:

- verdict = `UNCLEAR`

Reason recorded in the comparison artifact:

- `synrail_improves_proof_completeness`

The current comparison reading is therefore:

- the baseline remains plausible
- `Synrail` adds some truth discipline
- but the current evidence is not decisive enough to claim a clear win

This run now also has a canonical worked orchestration envelope:

- `fixtures/executable_loop_run_003/orchestration.json`

## Why this run matters

This run closes the current policy triangle with executable evidence:

1. strong path:
   - `docs/core/EXECUTABLE_LOOP_RUN_001.md`
   - `SYNRAIL_BETTER`
2. weaker path:
   - `docs/core/EXECUTABLE_LOOP_RUN_002.md`
   - `BASELINE_GOOD_ENOUGH`
3. hybrid path:
   - `docs/core/EXECUTABLE_LOOP_RUN_003.md`
   - `UNCLEAR`

That is a healthier product reading than trying to show only crisp wins.

It suggests the current hybrid mode is:

- plausible
- policy-relevant
- but still under-proven

## What this changes

The repo can now state a stronger and more honest current wedge:

- full governed `Synrail` looks best on proof-sensitive closure work
- the lightweight baseline is often enough on small low-risk incidents
- the hybrid subset is promising, but still not yet decisive

## What this does not prove

It does not prove:

- that the hybrid mode is already optimized
- that `UNCLEAR` is a final stable reading
- that the comparison harness fully captures medium-risk economics

It only proves that the current executable stack can now represent all three current policy outcomes without leaving the decision in prose alone.
