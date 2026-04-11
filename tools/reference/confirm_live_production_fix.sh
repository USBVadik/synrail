#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -lt 6 ] || [ "$#" -gt 8 ]; then
  echo "usage: confirm_live_production_fix.sh INCIDENT_ID SCENARIO_TEXT EXPECTED_OUTCOME OBSERVED_OUTCOME OUTFILE DEPLOY_NOTE [PM2_APP] [TARGET_REPO_PATH]" >&2
  exit 2
fi

INCIDENT_ID="$1"
SCENARIO_TEXT="$2"
EXPECTED_OUTCOME="$3"
OBSERVED_OUTCOME="$4"
OUTFILE="$5"
DEPLOY_NOTE="$6"
PM2_APP="${7:-target-app}"
TARGET_REPO_PATH="${8:-/srv/target-app}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ATTEST_OUTPUT="$("$SCRIPT_DIR/require_attested_target_surface.sh" "$TARGET_REPO_PATH")"
mkdir -p "$(dirname "$OUTFILE")"
TIMESTAMP_UTC="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

TARGET_HOST="$(printf '%s\n' "$ATTEST_OUTPUT" | awk -F= '/^target_primary_ipv4=/{print $2}' | tail -n 1)"
TARGET_HEAD="$(printf '%s\n' "$ATTEST_OUTPUT" | awk -F= '/^target_repo_head=/{print $2}' | tail -n 1)"
TARGET_BRANCH="$(printf '%s\n' "$ATTEST_OUTPUT" | awk -F= '/^target_repo_branch=/{print $2}' | tail -n 1)"
RUNTIME_SAMPLE="$(printf '%s\n' "$ATTEST_OUTPUT" | awk -F= '/^target_runtime_process_sample=/{print $2}' | tail -n 1)"

CONTROLLER_HOST="${CONTROLLER_HOST:-}"
CONTROLLER_KEY="${CONTROLLER_KEY:-$HOME/.ssh/codex_hetzner}"
TARGET_NESTED_KEY="${TARGET_NESTED_KEY:-/root/.ssh/google_compute_engine}"

if [ -z "$CONTROLLER_HOST" ]; then
  echo "confirmation_error=CONTROLLER_HOST_REQUIRED" >&2
  exit 2
fi

LOG_SNAPSHOT="$({
ssh -i "$CONTROLLER_KEY" "$CONTROLLER_HOST" "ssh -i $TARGET_NESTED_KEY -o BatchMode=yes -o ConnectTimeout=10 root@$TARGET_HOST '
  set -euo pipefail
  cd \"$TARGET_REPO_PATH\"
  pm2 describe \"$PM2_APP\" 2>/dev/null | sed -n \"1,80p\"
  printf \"---PM2_LOG_TAIL---\\n\"
  pm2 logs \"$PM2_APP\" --lines 30 --nostream 2>/dev/null | tail -n 30
'" 2>/dev/null || true
} )"

if [ -z "${LOG_SNAPSHOT}" ]; then
  LOG_SNAPSHOT="PM2_LOG_SNAPSHOT_UNAVAILABLE"
fi

CONFIRMATION_RESULT="FAIL"
MATCH_NOTE="external runtime observation does not yet agree with expected outcome"
if [ "$OBSERVED_OUTCOME" = "$EXPECTED_OUTCOME" ]; then
  CONFIRMATION_RESULT="PASS"
  MATCH_NOTE="external runtime observation agrees with expected outcome"
fi

cat > "$OUTFILE" <<EOF2
# PRODUCTION_CONFIRMATION_${INCIDENT_ID}

created_at_utc: ${TIMESTAMP_UTC}
incident_id: ${INCIDENT_ID}
record_type: production_runtime_confirmation
confirmation_result: ${CONFIRMATION_RESULT}
target_host: ${TARGET_HOST}
target_repo_path: ${TARGET_REPO_PATH}
target_repo_branch: ${TARGET_BRANCH}
target_repo_head: ${TARGET_HEAD}
pm2_app: ${PM2_APP}

## Deploy note

${DEPLOY_NOTE}

## Attestation snapshot

action: require_attested_target_surface
runtime_process_sample: ${RUNTIME_SAMPLE}

## Live scenario

scenario_text: ${SCENARIO_TEXT}
expected_outcome: ${EXPECTED_OUTCOME}
observed_outcome: ${OBSERVED_OUTCOME}

## Confirmation rule

- patch delivery is not enough
- restart success is not enough
- external runtime confirmation on the real bot is required
- ${MATCH_NOTE}

## PM2 / live log snapshot

${LOG_SNAPSHOT}

## Conclusion

This artifact may count toward production-fix acceptance only if confirmation_result is PASS.
EOF2

printf '%s\n' "$ATTEST_OUTPUT"
echo "production_confirmation_record=$OUTFILE"
echo "confirmation_result=$CONFIRMATION_RESULT"
