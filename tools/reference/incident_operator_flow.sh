#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat >&2 <<USAGE
usage:
  incident_operator_flow.sh start INCIDENT_ID TARGET_SURFACE HYPOTHESIS_TEXT SEARCH_REDUCTION HYP_OUTFILE [RUNTIME_CLUE] [TARGET_REPO_PATH]
  incident_operator_flow.sh confirm INCIDENT_ID SCENARIO_TEXT EXPECTED_OUTCOME OBSERVED_OUTCOME CONFIRM_OUTFILE DEPLOY_NOTE [PM2_APP] [TARGET_REPO_PATH]
USAGE
  exit 2
}

if [ "$#" -lt 1 ]; then
  usage
fi

MODE="$1"
shift
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

case "$MODE" in
  start)
    if [ "$#" -lt 5 ] || [ "$#" -gt 7 ]; then
      usage
    fi
    INCIDENT_ID="$1"
    TARGET_SURFACE="$2"
    HYPOTHESIS_TEXT="$3"
    SEARCH_REDUCTION="$4"
    HYP_OUTFILE="$5"
    RUNTIME_CLUE="${6:-NONE_PROVIDED}"
    TARGET_REPO_PATH="${7:-/srv/target-app}"

    "$SCRIPT_DIR/intake_incident_hypothesis.sh" \
      "$INCIDENT_ID" \
      "$TARGET_SURFACE" \
      "$HYPOTHESIS_TEXT" \
      "$SEARCH_REDUCTION" \
      "$HYP_OUTFILE" \
      "$RUNTIME_CLUE"

    "$SCRIPT_DIR/require_attested_target_surface.sh" "$TARGET_REPO_PATH"

    echo "incident_flow_stage=START_COMPLETED"
    echo "incident_flow_next_step=BOUNDED_PROBE_OR_PATCH_REVIEW"
    ;;
  confirm)
    if [ "$#" -lt 6 ] || [ "$#" -gt 8 ]; then
      usage
    fi
    INCIDENT_ID="$1"
    SCENARIO_TEXT="$2"
    EXPECTED_OUTCOME="$3"
    OBSERVED_OUTCOME="$4"
    CONFIRM_OUTFILE="$5"
    DEPLOY_NOTE="$6"
    PM2_APP="${7:-target-app}"
    TARGET_REPO_PATH="${8:-/srv/target-app}"

    "$SCRIPT_DIR/confirm_live_production_fix.sh" \
      "$INCIDENT_ID" \
      "$SCENARIO_TEXT" \
      "$EXPECTED_OUTCOME" \
      "$OBSERVED_OUTCOME" \
      "$CONFIRM_OUTFILE" \
      "$DEPLOY_NOTE" \
      "$PM2_APP" \
      "$TARGET_REPO_PATH"

    echo "incident_flow_stage=CONFIRM_COMPLETED"
    ;;
  *)
    usage
    ;;
esac
