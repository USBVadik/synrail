#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

if [[ -n "${SYNRAIL_BIN:-}" ]]; then
  SYNRAIL="$SYNRAIL_BIN"
elif [[ -x "$REPO_ROOT/.venv/bin/synrail" ]]; then
  SYNRAIL="$REPO_ROOT/.venv/bin/synrail"
elif [[ -x "$REPO_ROOT/.venv/Scripts/synrail.exe" ]]; then
  SYNRAIL="$REPO_ROOT/.venv/Scripts/synrail.exe"
elif command -v synrail >/dev/null 2>&1; then
  SYNRAIL="$(command -v synrail)"
else
  echo "Synrail demo: install the development CLI first; see the First Run Guide." >&2
  exit 2
fi

if [[ -n "${SYNRAIL_PYTHON:-}" ]]; then
  PYTHON="$SYNRAIL_PYTHON"
elif command -v python3 >/dev/null 2>&1; then
  PYTHON="$(command -v python3)"
elif command -v python >/dev/null 2>&1; then
  PYTHON="$(command -v python)"
else
  echo "Synrail demo: Python is required to write the repaired proof." >&2
  exit 2
fi

DEMO_ROOT="$(mktemp -d "${TMPDIR:-/tmp}/synrail-false-green.XXXXXX")"
DEMO_PROJECT="$DEMO_ROOT/project"
mkdir -p "$DEMO_PROJECT"
trap 'rm -rf "$DEMO_ROOT"' EXIT

(
  cd "$DEMO_PROJECT"
  "$SYNRAIL" start "Add a verified greeting." \
    --artifact-root .synrail \
    --project-root "$DEMO_PROJECT" >/dev/null
)

printf 'Done. Tests passed.\n' > "$DEMO_PROJECT/.synrail/final_result.json"

echo "# Live False-Green Demo"
echo
echo "Agent: done, tests passed"
echo
echo "Step 1: Synrail checks the weak claim"
echo '$ synrail check --artifact-root .synrail'
weak_output="$(cd "$DEMO_PROJECT" && "$SYNRAIL" check --artifact-root .synrail)"
weak_status="$(printf '%s\n' "$weak_output" | grep -m1 '^Status: ' || true)"
weak_next="$(printf '%s\n' "$weak_output" | grep -m1 '^Do this now: ' || true)"
printf 'Synrail: %s\n' "$weak_status"
printf '%s\n' "$weak_next"

if [[ "$weak_status" != "Status: Proof Invalid" ]]; then
  echo "Demo assertion failed: weak proof was not blocked as expected." >&2
  printf '%s\n' "$weak_output" >&2
  exit 1
fi

echo
echo "Step 2: perform the bounded repair and real local verification"
cat > "$DEMO_PROJECT/greeting.txt" <<'EOF'
Greeting:
hello from Synrail
End greeting.
EOF
verification_result="$(cd "$DEMO_PROJECT" && grep -n 'hello from Synrail' greeting.txt)"
printf '$ grep -n %s greeting.txt\n' "'hello from Synrail'"
printf '%s\n' "$verification_result"

DEMO_PROJECT="$DEMO_PROJECT" VERIFICATION_RESULT="$verification_result" "$PYTHON" - <<'PY'
import json
import os
from pathlib import Path

artifact_root = Path(os.environ["DEMO_PROJECT"]) / ".synrail"
state = json.loads((artifact_root / "state.json").read_text())
repaired_proof = {
    "request_id": state["run_id"],
    "task_class": state["task_class"],
    "status": "PROVEN",
    "change_disposition": "modified",
    "summary": "Added the bounded greeting and verified the exact line locally.",
    "modified_files": ["greeting.txt"],
    "git_diff": "",
    "diff_provenance": {
        "method": "direct_file_observation",
        "changed_file": "greeting.txt",
        "added_line": "hello from Synrail",
        "context_before": "Greeting:",
        "context_after": "End greeting.",
        "verification_command": "grep -n 'hello from Synrail' greeting.txt",
        "verification_result": os.environ["VERIFICATION_RESULT"],
    },
}
(artifact_root / "final_result.json").write_text(
    json.dumps(repaired_proof, indent=2, ensure_ascii=True) + "\n"
)
PY

echo
echo "Step 3: Synrail rechecks the repaired proof"
echo '$ synrail check --artifact-root .synrail'
accepted_output="$(cd "$DEMO_PROJECT" && "$SYNRAIL" check --artifact-root .synrail)"
accepted_status="$(printf '%s\n' "$accepted_output" | grep -m1 '^Status: ' || true)"
printf 'Synrail: %s\n' "$accepted_status"

if [[ "$accepted_status" != "Status: Accepted" ]]; then
  echo "Demo assertion failed: repaired proof was not accepted." >&2
  printf '%s\n' "$accepted_output" >&2
  exit 1
fi

echo
echo "Demo result: real weak proof blocked; real repaired proof accepted."
