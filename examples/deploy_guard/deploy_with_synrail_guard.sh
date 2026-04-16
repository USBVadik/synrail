#!/usr/bin/env bash
set -euo pipefail

# Example only:
# - local Synrail artifacts live under one trusted artifact root
# - this script performs bounded side effects only after deploy authorization

SYNRAIL_ARTIFACT_ROOT="${SYNRAIL_ARTIFACT_ROOT:-.synrail}"
SYNRAIL_GUARD="${SYNRAIL_GUARD:-tools/reference/synrail_deploy_guard.sh}"

REMOTE_HOST="${REMOTE_HOST:-example-host}"
REMOTE_PATH="${REMOTE_PATH:-/srv/example-app}"
PM2_PROCESS="${PM2_PROCESS:-example-app}"

echo "Checking Synrail deploy authorization..."
"$SYNRAIL_GUARD" --artifact-root "$SYNRAIL_ARTIFACT_ROOT"

echo "Syncing files..."
rsync -avz ./ "$REMOTE_HOST:$REMOTE_PATH/"

echo "Re-checking Synrail deploy authorization before restart..."
"$SYNRAIL_GUARD" --artifact-root "$SYNRAIL_ARTIFACT_ROOT"

echo "Restarting PM2 process..."
ssh "$REMOTE_HOST" "pm2 restart '$PM2_PROCESS'"
