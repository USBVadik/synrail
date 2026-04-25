#!/usr/bin/env bash
set -euo pipefail

# Example only:
# - smallest host-local pre-restart gate for a PM2-managed process

SYNRAIL_ARTIFACT_ROOT="${SYNRAIL_ARTIFACT_ROOT:-.synrail}"
SYNRAIL_GUARD="${SYNRAIL_GUARD:-tools/reference/synrail_deploy_guard.sh}"
PM2_PROCESS="${PM2_PROCESS:-example-app}"

"$SYNRAIL_GUARD" --artifact-root "$SYNRAIL_ARTIFACT_ROOT"
pm2 restart "$PM2_PROCESS"
