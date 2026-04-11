#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -lt 5 ] || [ "$#" -gt 6 ]; then
  echo "usage: intake_incident_hypothesis.sh INCIDENT_ID TARGET_SURFACE HYPOTHESIS_TEXT SEARCH_REDUCTION OUTFILE [RUNTIME_CLUE]" >&2
  exit 2
fi

INCIDENT_ID="$1"
TARGET_SURFACE="$2"
HYPOTHESIS_TEXT="$3"
SEARCH_REDUCTION="$4"
OUTFILE="$5"
RUNTIME_CLUE="${6:-NONE_PROVIDED}"

mkdir -p "$(dirname "$OUTFILE")"
TIMESTAMP_UTC="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

cat > "$OUTFILE" <<EOF2
# INCIDENT_HYPOTHESIS_${INCIDENT_ID}

created_at_utc: ${TIMESTAMP_UTC}
incident_id: ${INCIDENT_ID}
target_surface: ${TARGET_SURFACE}
record_type: bounded_incident_hypothesis
hypothesis_status: BOUNDED_HYPOTHESIS_ONLY

## Hypothesis

${HYPOTHESIS_TEXT}

## Runtime clue

${RUNTIME_CLUE}

## Accepted use

- narrow the search space to one likely active branch or file path
- justify one bounded probe or one bounded patch review
- reduce repeated broad rediscovery on the wrong surface

## Not accepted as proof

- not accepted as diagnosis by itself
- not accepted as fix proof by itself
- not accepted as deploy proof by itself
- not accepted as runtime confirmation by itself

## Search reduction

${SEARCH_REDUCTION}

## Next rule

Treat this artifact as a bounded hypothesis intake only.
The next step must still gather artifact truth on the attested target surface.
EOF2

echo "incident_hypothesis_record=$OUTFILE"
echo "incident_id=$INCIDENT_ID"
echo "hypothesis_status=BOUNDED_HYPOTHESIS_ONLY"
