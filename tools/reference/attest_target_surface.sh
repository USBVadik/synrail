#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -gt 1 ]; then
  echo "usage: attest_target_surface.sh [TARGET_REPO_PATH]" >&2
  exit 2
fi

TARGET_REPO_PATH="${1:-/root/USBAGENT_V2_1_STABLE}"
TARGET_HOST="${TARGET_HOST:-136.116.96.173}"
TARGET_USER="${TARGET_USER:-root}"
HETZNER_HOST="${HETZNER_HOST:-root@49.13.140.183}"
HETZNER_KEY="${HETZNER_KEY:-$HOME/.ssh/codex_hetzner}"

ssh -i "$HETZNER_KEY" "$HETZNER_HOST" "
  set -euo pipefail
  controller_hostname=\$(hostname)
  controller_ipv4=\$(hostname -I 2>/dev/null | cut -d\" \" -f1)
  if [ -f /root/.ssh/google_compute_engine ]; then
    google_key_state=PRESENT
  else
    google_key_state=MISSING
  fi

  target_probe=\$(ssh -i /root/.ssh/google_compute_engine -o BatchMode=yes -o ConnectTimeout=10 $TARGET_USER@$TARGET_HOST '
    set -euo pipefail
    target_hostname=\$(hostname)
    target_primary_ipv4=\$(hostname -I 2>/dev/null | cut -d\" \" -f1)
    if [ -d \"$TARGET_REPO_PATH\" ]; then
      repo_state=PRESENT
      cd \"$TARGET_REPO_PATH\"
      repo_head=\$(git rev-parse HEAD 2>/dev/null || echo REPO_HEAD_UNAVAILABLE)
      repo_branch=\$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo REPO_BRANCH_UNAVAILABLE)
      dirty_state=\$(git status --porcelain 2>/dev/null | wc -l | tr -d \" \")
    else
      repo_state=MISSING
      repo_head=REPO_HEAD_UNAVAILABLE
      repo_branch=REPO_BRANCH_UNAVAILABLE
      dirty_state=REPO_DIR_MISSING
    fi

    if ps -ef | grep -E \"/root/USBAGENT_V2_1_STABLE/main.py|python.*main.py|python.*bot\" | grep -v -E \"grep|bash -c set -euo|synrail_attest_ps\" >/tmp/synrail_attest_ps.txt 2>/dev/null; then
      runtime_process_state=PRESENT
      runtime_process_sample=\$(head -n 3 /tmp/synrail_attest_ps.txt | tr \"\n\" \";\")
    else
      runtime_process_state=NOT_OBSERVED
      runtime_process_sample=NONE
    fi
    rm -f /tmp/synrail_attest_ps.txt

    echo target_hostname=\$target_hostname
    echo target_primary_ipv4=\$target_primary_ipv4
    echo target_repo_path=$TARGET_REPO_PATH
    echo target_repo_state=\$repo_state
    echo target_repo_branch=\$repo_branch
    echo target_repo_head=\$repo_head
    echo target_repo_dirty_entries=\$dirty_state
    echo target_runtime_process_state=\$runtime_process_state
    echo target_runtime_process_sample=\$runtime_process_sample
  ')

  echo controller_surface=HETZNER_ORCHESTRATION_HOST
  echo controller_hostname=\$controller_hostname
  echo controller_primary_ipv4=\$controller_ipv4
  echo google_compute_engine_key=\$google_key_state
  printf '%s\n' \"\$target_probe\"

  target_repo_state=\$(printf '%s\n' \"\$target_probe\" | awk -F= '/^target_repo_state=/{print \$2}')
  if printf '%s\n' \"\$target_probe\" | grep -q '^target_hostname=' && [ \"\$target_repo_state\" = \"PRESENT\" ] && [ \"\$google_key_state\" = \"PRESENT\" ]; then
    attestation_result=PASS
  else
    attestation_result=FAIL
  fi

  echo attestation_result=\$attestation_result
"
