# DOCTOR_COVERAGE_MAP_001

## Purpose

Map what the current bounded doctor does, what it only partially covers, and what remains outside the current kernel scope.

## Covered

- trusted baseline identity present
- wrong target identity mismatch
- dirty execution surface under git
- artifact-path parent viability
- credential env missing
- credential env points at a missing path
- exact prompt/task identity missing or mismatched
- helper entrypoint missing
- helper entrypoint exists but is syntactically broken for bounded Python and shell entrypoints

## Partial

- non-git clean-surface truth still relies on explicit observation rather than deep surface attestation
- helper integrity is bounded to existence and parseability, not full runtime import graph correctness
- credential truth is bounded to env/path presence, not provider auth verification

## Uncovered

- deep config graph validity
- runtime library import drift beyond the helper entrypoint probe
- hidden side effects inside a helper that still parses cleanly
- broad environment truth beyond the current expensive readiness fail modes

## Current expensive gap closed in this tranche

The targeted fix in this tranche is:

- `helper exists` no longer counts as enough readiness truth when the entrypoint is already syntactically broken

This matters because that kind of false green is cheap to miss and expensive to discover only after execution begins.

## Current reading

The current doctor is still bounded.

But it is now more precise against one expensive false-readiness class instead of merely wider on paper.
