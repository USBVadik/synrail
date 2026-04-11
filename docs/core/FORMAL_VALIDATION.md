# FORMAL_VALIDATION

## Purpose

`Formal Validation` is the mandatory layer for schema/protocol/config-like artifacts where semantic plausibility is not enough.

This layer exists because `semantic review` can pass while the artifact remains structurally invalid.

## Locked failure class

`semantic_ok_but_formally_invalid_artifact`

This failure class is now treated as a core-layer rule, not as an incidental observation.

## When formal validation is mandatory

Use formal validation for artifacts that behave like:

- schemas
- protocols
- configs
- contracts
- structured control documents
- machine-consumed nested artifacts

## Validation dimensions

### Structural completeness

Check:

- required sections exist
- structure is not truncated
- expected top-level shape is present

### Required keys

Check:

- required fields exist
- required markers exist
- no critical field is omitted

### Nesting

Check:

- nesting depth is valid
- parent/child placement is valid
- sections are not semantically correct but structurally misplaced

### Conditional logic

Check:

- conditional requirements are enforced
- if field A exists, field B also exists when required
- mutually dependent blocks are complete

### Machine validation

Use machine validation where possible.

Examples:

- parser acceptance
- schema validator
- structural checker
- deterministic format checker

If machine validation is available but skipped, artifact is not fully validated.

## Validation outcomes

### Pass

Artifact is:

- semantically acceptable
- structurally complete
- formally valid for its intended consumer

### Fail

Artifact is not admissible if any of the following is true:

- semantic intent is acceptable but structure is invalid
- required keys are missing
- nesting is broken
- conditional requirements are violated
- machine validator rejects artifact

## Admission rule

For schema/protocol/config-like artifacts:

- semantic review alone is insufficient
- formal validation is mandatory before acceptance or promotion

## Failure-memory conversion

A formal validation failure must be converted into:

- rule
- checkpoint
- validation step
- retry/recovery semantic

## Minimal validation record

Each formally validated artifact should record:

- artifact identity
- artifact class
- validator used
- pass/fail status
- failed dimension
- decision
