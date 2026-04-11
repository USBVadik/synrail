# INCIDENT_FLOW_EVALUATION_TEMPLATE

## Purpose

Use this template after the next real narrow production incident that is run strictly through:

- `tools/reference/incident_operator_flow.sh start ...`
- bounded probe / patch / deploy work
- `tools/reference/incident_operator_flow.sh confirm ...`

The goal is to test whether the new incident flow materially reduces `blocker-to-closure cycle count`.

## Incident identity

- incident_id: `<INCIDENT_ID>`
- task_class: `<BOUNDED_ROUTER_OR_TRIGGER_FIX | SMALL_BUGFIX | CONTROLLED_PATCH_TASK>`
- target_surface: `<TARGET_SURFACE>`

## Flow discipline check

Mark each as `YES` or `NO`:

- bounded hypothesis intake used first when a narrow runtime clue existed: `<YES|NO|NOT_APPLICABLE>`
- target-surface attestation completed before any Node 2 claim: `<YES|NO>`
- production confirmation completed after deploy/restart: `<YES|NO|NOT_APPLICABLE>`
- closure/fix claim delayed until external runtime confirmation: `<YES|NO|NOT_APPLICABLE>`

## Cycle count

- blocker state first named at cycle: `<N>`
- closure or accepted live-fix confirmation reached at cycle: `<N>`
- blocker-to-closure cycle count: `<N>`

## Comparison basis

Compare against the pre-wrapper image-trigger incident qualitatively or numerically where possible.

Questions:

- did the wrapper remove any broad rediscovery loops?
- did bounded intake shorten time-to-first-correct-branch?
- did production confirmation shorten the gap between deploy and accepted live-fix claim?
- did the incident produce fewer contradictory intermediate claims?

## Outcome

- reduction observed: `<YES|NO|UNCLEAR>`
- confidence: `<HIGH|MEDIUM|LOW>`
- explanation: `<SHORT_SUMMARY>`

## Next rule

If reduction is not observed, do not broaden the product response immediately.
First identify whether the failure came from:

- missing runtime clue quality
- poor attestation discipline
- patch-quality issues
- deploy friction
- weak confirmation path
