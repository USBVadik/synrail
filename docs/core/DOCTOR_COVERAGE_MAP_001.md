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
- credential env still uses obvious placeholder values
- exact prompt/task identity missing or mismatched
- helper entrypoint missing
- helper entrypoint exists but is syntactically broken for bounded Python and shell entrypoints
- helper entrypoint parses but imports a missing module
- credential JSON path exists but is already malformed
- explicitly observed-safe change set still contains out-of-scope modified files

## Partial

- non-git clean-surface truth still relies on explicit observation rather than deep surface attestation
- helper integrity is bounded to existence and parseability, not full runtime import graph correctness
- credential truth is bounded to env/path presence, not provider auth verification

## Uncovered

- deep config graph validity
- runtime library import drift beyond the helper entrypoint probe
- hidden side effects inside a helper that still parses cleanly
- semantic intent drift inside an in-scope file that still stays within the allowed path prefix
- broad environment truth beyond the current expensive readiness fail modes

## Current expensive gap closed in this tranche

The targeted fix in this tranche is:

- `helper exists` no longer counts as enough readiness truth when the entrypoint is already syntactically broken
- `credential path exists` no longer counts as enough readiness truth when the JSON surface is already malformed
- `credential env is present` no longer counts as enough readiness truth when the env still contains an obvious placeholder like `CHANGE_ME`
- `helper parses` no longer counts as enough readiness truth when the helper already imports a missing module
- `clean surface observed-safe` no longer counts as enough readiness truth when the explicit changed-file set already contains out-of-scope modifications

This matters because that kind of false green is cheap to miss and expensive to discover only after execution begins.

## Current reading

The current doctor is still bounded.

But it is now more precise against one expensive false-readiness class instead of merely wider on paper.
