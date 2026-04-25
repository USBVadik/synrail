#!/usr/bin/env bash
set -euo pipefail

# Example only:
# - smallest host-local restart path for a systemd-managed service

SYNRAIL_ARTIFACT_ROOT="${SYNRAIL_ARTIFACT_ROOT:-.synrail}"
SYNRAIL_GUARD="${SYNRAIL_GUARD:-tools/reference/synrail_deploy_guard.sh}"
SYSTEMD_UNIT="${SYSTEMD_UNIT:-example-app.service}"

"$SYNRAIL_GUARD" --artifact-root "$SYNRAIL_ARTIFACT_ROOT"
systemctl restart "$SYSTEMD_UNIT"
