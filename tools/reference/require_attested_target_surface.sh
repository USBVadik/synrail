#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ATTEST_OUTPUT="$("$SCRIPT_DIR/attest_target_surface.sh" "$@")"

printf '%s\n' "$ATTEST_OUTPUT"

if ! printf '%s\n' "$ATTEST_OUTPUT" | grep -q '^attestation_result=PASS$'; then
  echo "attested_target_surface=FAIL" >&2
  exit 1
fi

echo "attested_target_surface=PASS"
