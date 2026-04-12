# Sanitized Narrow Incident Flow Example

## Scenario

A user reports a narrow production regression:

- a summary feature that had recently been localized is now replying in English again

The operator already has one bounded runtime clue:

- the regression is limited to one scheduled summary path

## Step 1. Bounded incident intake

Use:

```bash
tools/reference/intake_incident_hypothesis.sh \
  INCIDENT_TREND_SUMMARY_LANG_001 \
  production-target \
  "The active summary path regressed to English output" \
  "Start with the scheduled summary path and its user-facing text templates" \
  /tmp/incident_hypothesis.md \
  "Observed live summary arrived in English"
```

What this gives:

- a bounded search-space reducer

What it does not give:

- proof that the diagnosis is correct
- proof that the bug is fixed

## Step 2. Target-surface attestation

Use:

```bash
tools/reference/require_attested_target_surface.sh
```

What this gives:

- confirmation that the intended target surface is the one being inspected

What it does not give:

- proof that the target behavior is repaired

## Step 3. Bounded fix work

Do only the narrow review and patch work justified by the hypothesis.

In this example, that means:

- inspect the active summary path
- inspect the user-facing text templates
- patch only the regression area

## Step 4. Production confirmation

After deploy or restart, record one real-world outcome:

```bash
tools/reference/confirm_live_production_fix.sh \
  INCIDENT_TREND_SUMMARY_LANG_001 \
  "Scheduled trend summary arrives for the same user-facing path" \
  "Summary is delivered in Russian" \
  "Summary arrived in Russian" \
  /tmp/production_confirmation.md \
  "Restarted the production process after patching the summary path"
```

What this gives:

- one explicit external runtime confirmation

What it does not give:

- proof of broad feature completeness

## Step 5. Evaluation

Use:

- `docs/reference/INCIDENT_FLOW_EVALUATION_TEMPLATE.md`

Example reading:

- bounded clue was used first: `YES`
- attestation happened before target-runtime claims: `YES`
- production confirmation happened after deploy: `YES`
- closure claim waited for runtime confirmation: `YES`
- blocker-to-closure cycle count: `1`

## Why this example matters

This example shows the intended shape of a narrow incident flow:

- not broad rediscovery
- not narrative-only confidence
- not “patch delivered therefore fixed”

Instead:

- bounded clue
- attested surface
- narrow work
- real runtime confirmation
- explicit evaluation
