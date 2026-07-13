#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

if [[ -z "${NO_COLOR:-}" && ( -t 1 || "${SYNRAIL_DEMO_COLOR:-}" == "1" ) ]]; then
  COLOR_CYAN=$'\033[1;36m'
  COLOR_RED=$'\033[1;31m'
  COLOR_GREEN=$'\033[1;32m'
  COLOR_BOLD=$'\033[1m'
  COLOR_RESET=$'\033[0m'
else
  COLOR_CYAN=""
  COLOR_RED=""
  COLOR_GREEN=""
  COLOR_BOLD=""
  COLOR_RESET=""
fi

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
  echo "Synrail demo: Python is required for the behavioral fixture." >&2
  exit 2
fi

for required_command in git grep; do
  if ! command -v "$required_command" >/dev/null 2>&1; then
    echo "Synrail demo: $required_command is required for this behavioral fixture." >&2
    exit 2
  fi
done

# Keep the disposable commit isolated from host hooks, signing, and prompts.
export GIT_CONFIG_NOSYSTEM=1
export GIT_CONFIG_GLOBAL=/dev/null
export GIT_TERMINAL_PROMPT=0

DEMO_ROOT="$(mktemp -d "${TMPDIR:-/tmp}/synrail-false-green.XXXXXX")"
DEMO_PROJECT="$DEMO_ROOT/project"
mkdir -p "$DEMO_PROJECT"
trap 'rm -rf "$DEMO_ROOT"' EXIT

DEMO_PROJECT="$DEMO_PROJECT" "$PYTHON" - <<'PY'
import json
import os
import sys
from pathlib import Path

project = Path(os.environ["DEMO_PROJECT"])
(project / "app.py").write_text(
    "def add(a, b):\n"
    "    return a - b\n"
)
(project / "test_app.py").write_text(
    "import unittest\n"
    "\n"
    "from app import add\n"
    "\n"
    "\n"
    "class AddTests(unittest.TestCase):\n"
    "    def test_add(self):\n"
    "        self.assertEqual(5, add(2, 3))\n"
    "\n"
    "\n"
    "if __name__ == '__main__':\n"
    "    unittest.main()\n"
)
(project / "synrail.toml").write_text(
    "[verification.unit]\n"
    f"argv = [{json.dumps(sys.executable)}, \"-B\", \"-m\", \"unittest\", \"test_app\"]\n"
    "timeout_seconds = 60\n"
    "required = true\n"
)
(project / ".gitignore").write_text("__pycache__/\n.synrail/\n")
PY

(
  cd "$DEMO_PROJECT"
  git init -q
  git add app.py test_app.py synrail.toml .gitignore
  git -c core.hooksPath=/dev/null \
    -c commit.gpgsign=false \
    -c user.name="Synrail Demo" \
    -c user.email="synrail-demo@example.invalid" \
    commit -q -m "Seed behavioral verification demo"

  "$SYNRAIL" start \
    --artifact-root .synrail \
    --project-root "$DEMO_PROJECT" \
    --task-identity "Fix add() in app.py so the unit tests in test_app.py pass." \
    >/dev/null
)

# Intentionally plausible but wrong: the grep proof matches while behavior stays red.
cat > "$DEMO_PROJECT/app.py" <<'PY'
def add(a, b):
    # optimized fast path
    return a - b
PY

(
  cd "$DEMO_PROJECT"
  "$SYNRAIL" record app.py \
    --artifact-root .synrail \
    --summary "Fixed add() so the unit tests pass." \
    --verify "grep -n 'optimized fast path' app.py" \
    >/dev/null
)

printf '%b# Behavioral False-Green Demo%b\n' "$COLOR_CYAN" "$COLOR_RESET"
echo
printf '%bAgent:%b fixed add(); tests pass\n' "$COLOR_BOLD" "$COLOR_RESET"
echo "Agent proof: grep found the new fast-path line"
echo
echo "Step 1: Synrail runs the operator-owned unit test"
echo '$ synrail verify --artifact-root .synrail'
set +e
red_verify_output="$(cd "$DEMO_PROJECT" && "$SYNRAIL" verify --artifact-root .synrail 2>&1)"
red_verify_rc=$?
set -e
red_verify_status="$(printf '%s\n' "$red_verify_output" | grep -m1 '^Verification unit: ' || true)"
printf '%b%s%b\n' "$COLOR_RED" "$red_verify_status" "$COLOR_RESET"

if [[ $red_verify_rc -eq 0 || "$red_verify_status" != "Verification unit: FAIL (exit 1)"* ]]; then
  echo "Demo assertion failed: the operator-owned unit test was not red as expected." >&2
  printf '%s\n' "$red_verify_output" >&2
  exit 1
fi

echo
echo "Step 2: convenient proof cannot earn acceptance"
echo '$ synrail check --artifact-root .synrail'
set +e
blocked_output="$(cd "$DEMO_PROJECT" && "$SYNRAIL" check --artifact-root .synrail 2>&1)"
set -e
blocked_status="$(printf '%s\n' "$blocked_output" | grep -m1 '^Status: ' || true)"
printf '%bSynrail: %s%b\n' "$COLOR_RED" "$blocked_status" "$COLOR_RESET"

if [[ "$blocked_status" != "Status: Verification Failed" ]]; then
  echo "Demo assertion failed: red behavioral verification did not block acceptance." >&2
  printf '%s\n' "$blocked_output" >&2
  exit 1
fi

echo
echo "Step 3: repair the behavior, not the story"
# The real repair changes the behavior that the operator-owned test requires.
cat > "$DEMO_PROJECT/app.py" <<'PY'
def add(a, b):
    # optimized fast path
    return a + b
PY
(
  cd "$DEMO_PROJECT"
  "$SYNRAIL" record app.py \
    --artifact-root .synrail \
    --summary "Fixed add() so the unit tests pass." \
    --verify "grep -n 'optimized fast path' app.py" \
    >/dev/null
)
echo '$ synrail verify --artifact-root .synrail'
green_verify_output="$(cd "$DEMO_PROJECT" && "$SYNRAIL" verify --artifact-root .synrail)"
green_verify_status="$(printf '%s\n' "$green_verify_output" | grep -m1 '^Verification unit: ' || true)"
printf '%b%s%b\n' "$COLOR_GREEN" "$green_verify_status" "$COLOR_RESET"

if [[ "$green_verify_status" != "Verification unit: GREEN"* ]]; then
  echo "Demo assertion failed: repaired behavior did not pass verification." >&2
  printf '%s\n' "$green_verify_output" >&2
  exit 1
fi

echo '$ synrail check --artifact-root .synrail'
accepted_output="$(cd "$DEMO_PROJECT" && "$SYNRAIL" check --artifact-root .synrail)"
accepted_status="$(printf '%s\n' "$accepted_output" | grep -m1 '^Status: ' || true)"
printf '%bSynrail: %s%b\n' "$COLOR_GREEN" "$accepted_status" "$COLOR_RESET"

if [[ "$accepted_status" != "Status: Accepted" ]]; then
  echo "Demo assertion failed: verified repair was not accepted." >&2
  printf '%s\n' "$accepted_output" >&2
  exit 1
fi

echo
printf '%bDemo result:%b plausible proof blocked while tests were red; verified behavior accepted.\n' \
  "$COLOR_CYAN" "$COLOR_RESET"
