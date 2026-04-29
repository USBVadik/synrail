#!/usr/bin/env bash
# synrail_deploy_guard.sh — Last-resort guard for PM2/systemd/restart hooks.
#
# Usage:
#   synrail_deploy_guard.sh [--artifact-root .synrail]
#
# Exit codes:
#   0 = deploy authorized, proceed with restart
#   1 = deploy blocked, do NOT restart
#
# Integration examples:
#
#   PM2 pre-restart hook (ecosystem.config.js):
#     module.exports = {
#       apps: [{
#         name: "mybot",
#         script: "bot.py",
#         pre_restart: "synrail_deploy_guard.sh --artifact-root .synrail"
#       }]
#     }
#
#   Manual guard before any deploy step:
#     synrail_deploy_guard.sh && scp bot.py remote: && ssh remote pm2 restart bot
#
#   Shell alias:
#     alias safe-restart='synrail deploy-check && pm2 restart mybot'

set -euo pipefail

ARTIFACT_ROOT="${1:-.synrail}"

# Strip --artifact-root flag if passed
if [ "$ARTIFACT_ROOT" = "--artifact-root" ]; then
    ARTIFACT_ROOT="${2:-.synrail}"
fi

DEPLOY_RECEIPT="$ARTIFACT_ROOT/deploy_receipt.json"
STATE_FILE="$ARTIFACT_ROOT/state.json"
TARGET_IDENTITY_FILE="$ARTIFACT_ROOT/target_identity.txt"

JSON_GET_RESULT=""
STRICT_TEXT_RESULT=""

json_get() {
    local field="$1"
    local file="$2"
    local label="$3"
    local output

    if ! output=$(python3 - "$field" "$file" "$label" <<'PY'
import json
import sys
from pathlib import Path

field, file_path, label = sys.argv[1:4]
path = Path(file_path)

try:
    payload = json.loads(path.read_text())
except OSError as exc:
    print(f"DEPLOY BLOCKED: could not read {label} JSON at {path}: {exc}")
    raise SystemExit(1)
except json.JSONDecodeError as exc:
    print(
        f"DEPLOY BLOCKED: could not parse {label} JSON at {path}: "
        f"{exc.msg} (line {exc.lineno} column {exc.colno})"
    )
    raise SystemExit(1)

value = payload.get(field, "")
if value is None:
    value = ""
print(value)
PY
); then
        printf '%s\n' "$output"
        return 1
    fi

    JSON_GET_RESULT="$output"
}

read_strict_text() {
    local file="$1"
    local label="$2"
    local output

    if ! output=$(python3 - "$file" "$label" <<'PY'
import sys
from pathlib import Path

file_path, label = sys.argv[1:3]
path = Path(file_path)

try:
    print(path.read_text().strip())
except OSError as exc:
    print(f"DEPLOY BLOCKED: could not read {label} at {path}: {exc}")
    raise SystemExit(1)
PY
); then
        printf '%s\n' "$output"
        return 1
    fi

    STRICT_TEXT_RESULT="$output"
}

# Check 1: deploy receipt must exist
if [ ! -f "$DEPLOY_RECEIPT" ]; then
    echo "DEPLOY BLOCKED: no deploy receipt found at $DEPLOY_RECEIPT"
    echo "Run 'synrail deploy' after your run is accepted to authorize deployment."
    exit 1
fi

# Check 2: receipt must say DEPLOY_AUTHORIZED
json_get "result" "$DEPLOY_RECEIPT" "deploy receipt"
RECEIPT_RESULT="$JSON_GET_RESULT"
if [ "$RECEIPT_RESULT" != "DEPLOY_AUTHORIZED" ]; then
    echo "DEPLOY BLOCKED: deploy receipt exists but result is '$RECEIPT_RESULT', not 'DEPLOY_AUTHORIZED'."
    exit 1
fi

# Check 3: if state file exists, run_id must match
if [ ! -f "$STATE_FILE" ]; then
    echo "DEPLOY BLOCKED: no state file found at $STATE_FILE"
    exit 1
fi

json_get "state" "$STATE_FILE" "run state"
CURRENT_STATE="$JSON_GET_RESULT"
if [ "$CURRENT_STATE" != "CLOSURE_ACCEPTED" ]; then
    echo "DEPLOY BLOCKED: current state is '$CURRENT_STATE', not 'CLOSURE_ACCEPTED'."
    echo "Re-run Synrail acceptance before any deployment side effect."
    exit 1
fi

json_get "run_id" "$DEPLOY_RECEIPT" "deploy receipt"
RECEIPT_RUN_ID="$JSON_GET_RESULT"
json_get "run_id" "$STATE_FILE" "run state"
STATE_RUN_ID="$JSON_GET_RESULT"
if [ -n "$RECEIPT_RUN_ID" ] && [ -n "$STATE_RUN_ID" ] && [ "$RECEIPT_RUN_ID" != "$STATE_RUN_ID" ]; then
    echo "DEPLOY BLOCKED: deploy receipt is for run '$RECEIPT_RUN_ID' but current state is run '$STATE_RUN_ID'."
    echo "The receipt is stale. Run 'synrail deploy' for the current accepted run."
    exit 1
fi

json_get "target_identity" "$DEPLOY_RECEIPT" "deploy receipt"
RECEIPT_TARGET_IDENTITY="$JSON_GET_RESULT"
if [ -z "$RECEIPT_TARGET_IDENTITY" ]; then
    echo "DEPLOY BLOCKED: deploy receipt does not contain a target identity."
    exit 1
fi

if [ ! -f "$TARGET_IDENTITY_FILE" ]; then
    echo "DEPLOY BLOCKED: no current target identity found at $TARGET_IDENTITY_FILE"
    exit 1
fi

read_strict_text "$TARGET_IDENTITY_FILE" "current target identity"
CURRENT_TARGET_IDENTITY="$STRICT_TEXT_RESULT"
if [ -z "$CURRENT_TARGET_IDENTITY" ]; then
    echo "DEPLOY BLOCKED: current target identity is empty."
    exit 1
fi

if [ "$RECEIPT_TARGET_IDENTITY" != "$CURRENT_TARGET_IDENTITY" ]; then
    echo "DEPLOY BLOCKED: deploy receipt target '$RECEIPT_TARGET_IDENTITY' does not match current target '$CURRENT_TARGET_IDENTITY'."
    echo "The receipt is stale. Run 'synrail deploy' for the current accepted run."
    exit 1
fi

# All checks passed
echo "DEPLOY OK: authorized for run $RECEIPT_RUN_ID"
exit 0
