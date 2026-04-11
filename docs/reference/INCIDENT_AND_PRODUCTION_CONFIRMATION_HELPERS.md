# INCIDENT_AND_PRODUCTION_CONFIRMATION_HELPERS

## Purpose

Add two narrow helpers to the active `Synrail` kernel scope:

- bounded incident-hypothesis intake
- post-deploy production runtime confirmation

These helpers exist to reduce wasted rediscovery time and to prevent patch delivery from being mistaken for a real production fix.

## Standard workflow placement

These helpers are no longer optional side tools.

For narrow production incidents, the standard placement is now:

1. if a user/operator brings one narrow runtime clue:
   - run `tools/reference/intake_incident_hypothesis.sh`
2. before any target-surface diagnosis/fix/test/deploy claim:
   - run `tools/reference/require_attested_target_surface.sh`
3. after live patch delivery or process restart:
   - run `tools/reference/confirm_live_production_fix.sh`

That means:

- bounded hypothesis intake is the default incident-entry step when a narrow clue exists
- production confirmation is the default exit step for a live production-fix claim

## Minimal operator wrapper

Path:

- `tools/reference/incident_operator_flow.sh`

Purpose:

- keep the standard incident order physically intact
- reduce accidental skipping of intake or attestation
- provide one tiny wrapper around the already-approved helpers rather than a new orchestration layer

Modes:

```bash
tools/reference/incident_operator_flow.sh start ...
tools/reference/incident_operator_flow.sh confirm ...
```

Rule:

- `start` performs:
  - bounded hypothesis intake
  - target-surface attestation
- `confirm` performs:
  - production runtime confirmation

This wrapper is convenience glue only.

It does not replace artifact truth, attestation, or external runtime confirmation.

## Helper 1. Incident hypothesis intake

Path:

- `tools/reference/intake_incident_hypothesis.sh`

Purpose:

- accept one narrow operator-provided runtime clue as a bounded hypothesis
- reduce search space without treating the clue as proof

Usage:

```bash
tools/reference/intake_incident_hypothesis.sh \
  INCIDENT_ID \
  TARGET_SURFACE \
  HYPOTHESIS_TEXT \
  SEARCH_REDUCTION \
  OUTFILE \
  [RUNTIME_CLUE]
```

Rule:

- the output artifact may justify one narrow probe or one narrow patch review
- it may not count as diagnosis proof, fix proof, deploy proof, or runtime confirmation
- in the standard incident workflow, use this before broad rediscovery when a narrow runtime clue already exists

## Helper 2. Production runtime confirmation

Path:

- `tools/reference/confirm_live_production_fix.sh`

Purpose:

- require target-surface attestation first
- capture a live PM2/runtime snapshot after deploy or restart
- record one real-scenario external runtime outcome
- decide whether the production-fix claim is confirmed

Usage:

```bash
tools/reference/confirm_live_production_fix.sh \
  INCIDENT_ID \
  SCENARIO_TEXT \
  EXPECTED_OUTCOME \
  OBSERVED_OUTCOME \
  OUTFILE \
  DEPLOY_NOTE \
  [PM2_APP] \
  [TARGET_REPO_PATH]
```

Rule:

- `confirmation_result=PASS` only when the external runtime observation agrees with the expected outcome
- patch delivery alone is not enough
- restart success alone is not enough
- in the standard production bugfix workflow, this is the mandatory post-deploy step before a live-fix claim is accepted

## Why this is in scope

These helpers stay within the minimal executable kernel because they directly improve closure economics on the active narrow task class:

- they shorten broad rediscovery when a narrow runtime clue already exists
- they force a final external runtime truth check after deploy
- they reduce the gap between patch delivery and trustworthy production confirmation

## First exercised artifacts

- incident hypothesis intake:
  - first exercised on a proving-ground image-trigger incident
- production confirmation:
  - first exercised on a proving-ground production confirmation path
