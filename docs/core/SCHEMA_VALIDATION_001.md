# Schema Validation 001

## Purpose

Define the first executable schema-validation slice for `Synrail`.

This document exists so machine-readable artifacts are not only produced, but can also be checked for structural validity before they are trusted.

## Artifact

The first validation slice now lives at:

- `tools/reference/synrail_validate_v0.py`

## What it does

The validator v0 can:

1. read one JSON schema from `schemas/`
2. read one JSON document artifact
3. validate a small supported rule set:
   - `type`
   - `required`
   - `properties`
   - `additionalProperties: false`
   - `const`
   - `enum`
   - `minLength`
   - `minimum`
   - `items`
4. emit:
   - `VALID`
   - `INVALID`

## Why this matters

Without schema validation, machine-readable artifacts can still drift structurally while looking legitimate enough to pass casual inspection.

Validation is the first move toward making artifact shape:

- explicit
- checkable
- less prose-dependent

## v0 limitations

The validator currently does not perform:

- full JSON Schema support
- cross-document semantic validation
- orchestration-level enforcement

It is intentionally small and focused on the schema features already used in this repo.

## Decision rule

Future validation work should improve:

- structural trust in generated artifacts
- low-friction operator checks
- consistency across kernel slices

without turning validation into a large dependency-heavy subsystem too early.
