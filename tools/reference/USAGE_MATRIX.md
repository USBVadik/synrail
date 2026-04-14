# Reference Helper Usage Matrix

Use this page when you need the fastest answer to:

- which helper should I run
- when should I run it
- what does it require
- what does it not prove

## Matrix

| Helper | Use it when | Typical inputs | Main output | Does not prove |
| --- | --- | --- | --- | --- |
| `synrail` | You want the current alpha lane through one installable command instead of calling individual helpers by hand | one `artifact-root`, optional checkpoint id, and usually one `final_result.json` or `final_result.txt` under the artifact root or project root | standardized state, checkpoint, thin output, prompt, and restore artifacts under one root | broad product coverage, domain correctness without bounded inputs, every future install path |
| `synrail telemetry export` | You finished one alpha run and want one bounded replay plus one issue-ready summary without copying artifact contents by hand | one telemetry-enabled `artifact-root` | sanitized command sequence, state-at-error snapshot, issue-ready markdown body | hosted telemetry, automatic upload, sensitive-content capture |
| `attest_target_surface.sh` | You need to know whether the intended target surface is actually the one being inspected | controller/target surface details, target repo path, optional runtime pattern | attestation facts plus `PASS` or `FAIL` | patch correctness, target health, repaired behavior |
| `require_attested_target_surface.sh` | You want to gate the next step on successful target-surface attestation | same attestation inputs, usually via env/defaults | hard gate on `attested_target_surface=PASS` | diagnosis quality, test quality, deploy success |
| `intake_incident_hypothesis.sh` | A user or operator gives one narrow runtime clue and you want to reduce search space safely | incident id, target surface, bounded hypothesis text, search reduction, output path | bounded incident-hypothesis artifact | diagnosis truth, fix truth, runtime confirmation |
| `confirm_live_production_fix.sh` | A patch or restart already happened and you need one real-world outcome check | incident id, scenario text, expected outcome, observed outcome, output path | confirmation artifact with explicit result | full feature completeness, broad system health |
| `incident_operator_flow.sh` | You want the smallest wrapper that preserves the intended incident order | `start` or `confirm` plus the inputs for the underlying helper stage | bounded glue over intake/attestation/confirmation | closure by itself, good patch quality, good diagnosis by itself |

## Suggested order

For a narrow production incident, the usual order is:

1. `intake_incident_hypothesis.sh`
2. `require_attested_target_surface.sh`
3. bounded probe / bounded patch review / bounded fix work
4. `confirm_live_production_fix.sh`

If you want the light wrapper form, use:

1. `incident_operator_flow.sh start`
2. bounded work
3. `incident_operator_flow.sh confirm`

## Reading rule

If you are unsure whether a helper belongs in a step, prefer the narrower interpretation.

These helpers are here to make truth and gating behavior clearer.

They are not here to hide judgment or replace proof.

For the concrete installable contour, read [ALPHA_LANE_001.md](/Users/usbdick/Documents/New%20project/synrail/docs/core/ALPHA_LANE_001.md) and inspect [alpha_shell_run_002](/Users/usbdick/Documents/New%20project/synrail/fixtures/alpha_shell_run_002).
