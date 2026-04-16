#!/usr/bin/env bash
set -euo pipefail

# Example only:
# - uses the wrapper so each side effect is individually guarded

SYNRAIL_ARTIFACT_ROOT="${SYNRAIL_ARTIFACT_ROOT:-.synrail}"
SYNRAIL_WRAPPER="${SYNRAIL_WRAPPER:-tools/reference/synrail_guarded_side_effect_v0.sh}"

REMOTE_HOST="${REMOTE_HOST:-example-host}"
REMOTE_PATH="${REMOTE_PATH:-/srv/example-app}"
PM2_PROCESS="${PM2_PROCESS:-example-app}"

echo "Running guarded file sync..."
"$SYNRAIL_WRAPPER" --artifact-root "$SYNRAIL_ARTIFACT_ROOT" -- \
  rsync -avz ./ "$REMOTE_HOST:$REMOTE_PATH/"

echo "Running guarded PM2 restart..."
"$SYNRAIL_WRAPPER" --artifact-root "$SYNRAIL_ARTIFACT_ROOT" -- \
  ssh "$REMOTE_HOST" "pm2 restart '$PM2_PROCESS'"
