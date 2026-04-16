# Executable Loop Run 002

## Purpose

Record a second internal end-to-end run through the current executable `Synrail` stack on a less favorable scenario.

This document exists so the repo can show that the kernel loop does not only look good on its strongest current path.

## Scenario

- run id: `EXECUTABLE_LOOP_RUN_002`
- task class: `honesty_restoration_guard`
- scenario shape:
  - lower false-success risk
  - cheaper operator validation
  - a case where the simpler baseline is more plausible

## Artifacts

The run artifacts now live under:

- `fixtures/executable_loop_run_002/`

Included artifacts:

- `run.json`
- `state.json`
- `doctor.json`
- `bundle.json`
- `closure.json`
- `comparison.json`
- `orchestration.json`

The comparison fixtures used for this run are:

- `fixtures/comparison_input_weak_baseline_v0.json`
- `fixtures/comparison_input_weak_synrail_v0.json`

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

### 1. Bundle path

Before proof assembly, the run emitted a green doctor record:

- verdict = `ACCEPTABLE_FOR_CORE_RUN`

The doctor artifact here now reads as a bounded green path for this lighter scenario:

- explicit clean execution input
- explicit artifact viability input
- no extra helper or credential gates required at this level

This run intentionally used a partial bundle shape.

Observed result:

- proof bundle status = `PARTIAL`
- missing sections:
  - `readback`
  - `scenario_proof`

### 2. Closure path

The closure engine emitted:

- closure status = `CLAIMED_NOT_ACCEPTED`
- blocking reason = `MISSING_PROOF_SECTIONS`
- next safe step = `collect readback from changed sections on the attested surface`
- resulting state = `PROOF_BUNDLE_PARTIAL`

This confirms that the current stack still behaves honestly on a weaker scenario:

- it does not pretend closure is accepted when proof remains partial

### 3. Baseline comparison path

Using the weak comparison fixtures, the harness emitted:

- verdict = `BASELINE_GOOD_ENOUGH`

This run now also has a canonical primary run artifact:

- `fixtures/executable_loop_run_002/run.json`

And a worked orchestration envelope:

- `fixtures/executable_loop_run_002/orchestration.json`

## Why this run matters

This is the second internal executable run reading, and it is useful because it narrows the product claim further:

- the stack still preserves proof discipline correctly
- but the simpler baseline may already be sufficient on this class of work

That is a healthier signal than trying to force every scenario into a `Synrail better` reading.

## What this changes

Together with Run 001, the repo now has a pair of executable internal readings:

1. strong path:
   - `SYNRAIL_BETTER`
2. weaker path:
   - `BASELINE_GOOD_ENOUGH`

This gives the current wedge a stronger basis:

- `Synrail` appears most justified where false completion and proof ambiguity are expensive
- it is less clearly justified on lower-risk honesty-restoration paths

## What this does not prove

It does not prove:

- that the weaker scenario should never use `Synrail`
- that the baseline is generally superior
- that the current stack is production-complete

It only proves that the current executable comparison logic can now express both:

- stronger-than-baseline
- baseline-good-enough

without relying on prose-only judgment.

For the first canonical repaired reverse edge from that partial-proof surface, see:

- `EXECUTABLE_LOOP_PARTIAL_REENTRY_RUN_001.md`
