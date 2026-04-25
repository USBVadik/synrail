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

# Check 1: deploy receipt must exist
if [ ! -f "$DEPLOY_RECEIPT" ]; then
    echo "DEPLOY BLOCKED: no deploy receipt found at $DEPLOY_RECEIPT"
    echo "Run 'synrail deploy' after your run is accepted to authorize deployment."
    exit 1
fi

# Check 2: receipt must say DEPLOY_AUTHORIZED
RECEIPT_RESULT=$(python3 -c "import json; print(json.load(open('$DEPLOY_RECEIPT')).get('result',''))" 2>/dev/null || echo "")
if [ "$RECEIPT_RESULT" != "DEPLOY_AUTHORIZED" ]; then
    echo "DEPLOY BLOCKED: deploy receipt exists but result is '$RECEIPT_RESULT', not 'DEPLOY_AUTHORIZED'."
    exit 1
fi

# Check 3: if state file exists, run_id must match
if [ ! -f "$STATE_FILE" ]; then
    echo "DEPLOY BLOCKED: no state file found at $STATE_FILE"
    exit 1
fi

CURRENT_STATE=$(python3 -c "import json; print(json.load(open('$STATE_FILE')).get('state',''))" 2>/dev/null || echo "")
if [ "$CURRENT_STATE" != "CLOSURE_ACCEPTED" ]; then
    echo "DEPLOY BLOCKED: current state is '$CURRENT_STATE', not 'CLOSURE_ACCEPTED'."
    echo "Re-run Synrail acceptance before any deployment side effect."
    exit 1
fi

RECEIPT_RUN_ID=$(python3 -c "import json; print(json.load(open('$DEPLOY_RECEIPT')).get('run_id',''))" 2>/dev/null || echo "")
STATE_RUN_ID=$(python3 -c "import json; print(json.load(open('$STATE_FILE')).get('run_id',''))" 2>/dev/null || echo "")
if [ -n "$RECEIPT_RUN_ID" ] && [ -n "$STATE_RUN_ID" ] && [ "$RECEIPT_RUN_ID" != "$STATE_RUN_ID" ]; then
    echo "DEPLOY BLOCKED: deploy receipt is for run '$RECEIPT_RUN_ID' but current state is run '$STATE_RUN_ID'."
    echo "The receipt is stale. Run 'synrail deploy' for the current accepted run."
    exit 1
fi

RECEIPT_TARGET_IDENTITY=$(python3 -c "import json; print(json.load(open('$DEPLOY_RECEIPT')).get('target_identity',''))" 2>/dev/null || echo "")
if [ -z "$RECEIPT_TARGET_IDENTITY" ]; then
    echo "DEPLOY BLOCKED: deploy receipt does not contain a target identity."
    exit 1
fi

if [ ! -f "$TARGET_IDENTITY_FILE" ]; then
    echo "DEPLOY BLOCKED: no current target identity found at $TARGET_IDENTITY_FILE"
    exit 1
fi

CURRENT_TARGET_IDENTITY=$(python3 -c "from pathlib import Path; print(Path('$TARGET_IDENTITY_FILE').read_text().strip())" 2>/dev/null || echo "")
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
