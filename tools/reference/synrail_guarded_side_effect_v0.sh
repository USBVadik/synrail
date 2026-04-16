#!/usr/bin/env bash
# synrail_guarded_side_effect_v0.sh — run a side effect only after deploy authorization.

set -euo pipefail

ARTIFACT_ROOT=".synrail"

usage() {
    echo "usage: synrail_guarded_side_effect_v0.sh [--artifact-root .synrail] -- <command> [args...]" >&2
}

while [ "$#" -gt 0 ]; do
    case "$1" in
        --artifact-root)
            if [ "$#" -lt 2 ]; then
                usage
                exit 2
            fi
            ARTIFACT_ROOT="$2"
            shift 2
            ;;
        --)
            shift
            break
            ;;
        *)
            break
            ;;
    esac
done

if [ "$#" -eq 0 ]; then
    usage
    exit 2
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
"$SCRIPT_DIR/synrail_deploy_guard.sh" --artifact-root "$ARTIFACT_ROOT"
exec "$@"
