# SYNRAIL_DOCTOR

## Purpose

Define a productized doctor / preflight surface for `Synrail`.

The purpose of `Synrail Doctor` is not generic diagnostics.

The purpose is:

- verify that an execution surface is trustworthy enough for a controlled run
- surface blockers before expensive or misleading execution starts
- make readiness machine-readable
- reduce bespoke runtime-audit cycles
- strengthen proof-first operation for coding-agent execution

## Core rule

`Synrail Doctor` must answer one narrow question:

> Is the current execution surface acceptable for the intended class of run?

It must not answer this by narrative confidence.

It must answer this by explicit gates and an explicit verdict.

## What Doctor is allowed to evaluate

`Synrail Doctor` may evaluate:

- trusted baseline identity
- execution-surface cleanliness
- helper integrity
- credential surface
- provider reachability
- JSON/artifact path viability
- machine-readable output viability
- exact-task support readiness

`Synrail Doctor` must not:

- silently repair product code
- blur diagnosis with mutation
- treat observed live dirtiness as trusted baseline truth
- treat successful startup as proof of end-to-end readiness

## Doctor levels

### 1. Core Doctor

Used before any meaningful support or retry cycle.

It checks:

- trusted baseline identity is named
- target execution surface is known
- current path is either clean or explicitly refused
- output artifact path is writable
- machine-readable JSON return path is viable

### 2. Support Doctor

Used before exact-like support runs.

It checks:

- helper surface is trustworthy or bypassed safely
- provider-specific credentials are present when required
- provider invocation path is reachable
- timeout and cleanup semantics are active
- support-run classification can still produce a receipt/artifact on failure

### 3. Exact Retry Doctor

Used only before the actual exact retry task.

It checks:

- exact prompt artifact is present
- exact task semantics are named
- execution policy is present
- support baseline is acceptable
- no unresolved blocker remains in promotion / validation / execution surface

## Mandatory gates

### Gate 1. Baseline Identity

Doctor must know:

- what commit or artifact is trusted
- whether the current run targets:
  - trusted baseline
  - clean derived path
  - dirty observed working tree

If this is ambiguous, doctor must fail.

### Gate 2. Clean Execution Surface

Doctor must determine whether the execution surface is:

- clean and promotable
- dirty but intentionally observed only
- dirty and unsafe for the intended run

If current-run attribution would be unsafe, doctor must fail.

### Gate 3. Helper Integrity

Doctor must determine whether helper entrypoints are:

- trusted artifacts
- bypassed safely by direct invocation
- contaminated or drifted

If helper trust is unknown and helper use is required, doctor must fail.

### Gate 4. Credential Surface

Doctor must determine whether required provider credentials are discoverable for the intended model path.

If credentials are missing, doctor must fail before downstream startup.

### Gate 5. Artifact Viability

Doctor must determine whether the run can return:

- machine-readable status
- modified file list
- diff/provenance artifact
- cleanup status

If the run can fail without leaving a reliable artifact, doctor must fail.

### Gate 6. Prompt / Task Identity

For exact retries, doctor must determine whether:

- the literal exact prompt exists
- the task id exists
- the execution policy exists

If the exact prompt artifact is missing, exact retry doctor must fail.

## Verdict classes

Doctor must return one of these verdict classes:

- `ACCEPTABLE_FOR_CORE_RUN`
- `ACCEPTABLE_FOR_SUPPORT_RUN`
- `ACCEPTABLE_FOR_EXACT_RETRY`
- `NOT_ACCEPTABLE_BASELINE_IDENTITY`
- `NOT_ACCEPTABLE_DIRTY_SURFACE`
- `NOT_ACCEPTABLE_HELPER_INTEGRITY`
- `NOT_ACCEPTABLE_CREDENTIAL_SURFACE`
- `NOT_ACCEPTABLE_ARTIFACT_PATH`
- `NOT_ACCEPTABLE_EXACT_PROMPT_MISSING`
- `NOT_ACCEPTABLE_UNCLASSIFIED`

## Minimal doctor record

A doctor record should minimally contain:

- doctor level
- target execution surface
- trusted baseline identity
- intended run class
- gate results
- final verdict
- blocking failure classes
- timestamp

## Known Synrail doctor inputs

From current observed history, `Synrail Doctor` must be able to incorporate findings such as:

- `dirty_repo_before_execution`
- `branch-collision silent exit`
- `executor-timeout orphan path`
- `execution-surface contamination`
- `credential-surface missing`
- `exact-prompt-artifact-missing`

These are not narrative notes.

They are doctor-relevant readiness facts.

## Anti-gaming rule

Doctor must not be considered green just because:

- a short smoke succeeds
- a subprocess starts
- a helper returns output
- a model session opens

Doctor is green only when the gates required for the intended run class are green.

## Decision rule

If doctor cannot distinguish:

- trusted artifact vs observed artifact
- clean surface vs dirty surface
- helper integrity vs helper contamination
- credential presence vs credential assumption

then doctor must return a non-acceptable verdict.

`Synrail Doctor` exists to make uncertain readiness explicit, not to smooth it over.
