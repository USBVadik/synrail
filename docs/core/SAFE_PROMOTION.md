# SAFE_PROMOTION

## Purpose

`Safe Promotion` closes the `Promotion Gap` between isolated execution and safe adoption into the baseline.

Promotion is not complete when a worker run "looks done".
Promotion is complete only when the produced artifact is:

- identified
- verified
- reviewable
- reversible
- admitted through explicit gates

## Core problem: Promotion Gap

`Promotion Gap` is the gap between:

- isolated task completion in a branch/worktree/runtime
- and safe, checkable, reversible integration into the trusted baseline

If this gap is not closed, the layer can produce local success claims without safe baseline advancement.

## Promotion stages

### 1. Isolated Execution Artifact

Produced inside bounded execution.

Required:

- exact task identity
- exact artifact identity
- exact scope identity
- raw proof bundle

Not enough for promotion.

### 2. Verified Artifact

The isolated artifact becomes verified only after:

- proof bundle completeness check
- required scenario/test evidence
- formal validation where applicable
- no unresolved blocker class

If proof is partial, artifact stays below promotion.

### 3. Promotion Candidate

An artifact becomes a promotion candidate only if:

- verified artifact exists
- target baseline is named explicitly
- delta against baseline is reviewable
- rollback path is known
- promotion risk is classified

### 4. Safe Adoption

Promotion into baseline is allowed only through explicit admission.

Required gates:

- proof gate
- formal validation gate
- scope gate
- baseline identity gate
- reversibility gate

## Mandatory promotion gates

### Proof Gate

Required:

- full proof bundle
- artifact identity
- required execution evidence
- no success claim without proof

### Formal Validation Gate

Mandatory for schema/protocol/config-like artifacts.

See `docs/core/FORMAL_VALIDATION.md`.

### Scope Gate

Required:

- changes are inside intended scope
- no hidden scope drift
- no unrelated adoption bundled into promotion

### Baseline Identity Gate

Required:

- trusted baseline named explicitly
- working tree / commit artifact / tested artifact distinction preserved
- promotion target named explicitly

### Reversibility Gate

Required:

- rollback path known
- rejection path known
- promotion can be stopped without ambiguous partial success

## Stop conditions

Stop promotion immediately if any of the following is true:

- proof bundle incomplete
- formal validation fails
- baseline identity ambiguous
- rollback path unclear
- new failure class appears
- artifact is semantically plausible but formally invalid

## Failure-memory conversion

Every promotion failure class must be converted into:

- rule
- checkpoint
- validation step
- retry/recovery semantic

Promotion failures must not remain narrative-only lessons.

## Minimal promotion record

Each promotion candidate should record:

- task id
- source artifact
- tested artifact
- target baseline
- proof bundle status
- formal validation status
- scope status
- reversibility status
- final decision

## Decision rule

`Promote` only if all gates pass.

`Do not promote` if any gate is missing, ambiguous, or blocked.

No "almost promoted" state should be treated as success.
