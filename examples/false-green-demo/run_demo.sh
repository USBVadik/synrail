#!/usr/bin/env bash
set -euo pipefail

cat <<'EOF'
# False-Green Demo

Agent: done, tests passed

Step 1: weak proof attempt
$ python3 alpha.py check
Synrail: Status: Proof Invalid
Reason: verification command not executed / freshness mismatch
Next: repair final_result.json

Step 2: bounded repair
- run the real verification
- strengthen final_result.json with truthful provenance

Step 3: accepted closure
$ python3 alpha.py check --clean-surface
Synrail: Status: Accepted
EOF
