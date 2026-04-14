# Reference Helpers

These scripts are intentionally small.

They are included to show narrow `Synrail` control behaviors clearly.

They are **not** a full orchestration platform.

For the quickest helper-selection view, start with:

- `USAGE_MATRIX.md`

For the current installable alpha path, start with:

- [`docs/core/ALPHA_LANE_001.md`](/Users/usbdick/Documents/New%20project/synrail/docs/core/ALPHA_LANE_001.md)

## What these helpers are for

Use them as:

- reference implementations
- operator-facing examples
- small boundary-preserving utilities

Do not treat them as:

- the full product
- a complete deployment system
- a generic automation framework

## Installable Alpha Shell

The repo now carries one thin installable `synrail` entrypoint on top of the existing reference helpers.

The current verified local install path is:

```bash
python3 -m venv --system-site-packages .venv
.venv/bin/python -m pip install -e . --no-build-isolation
```

The current verified restore-capable alpha lane is:

```bash
ARTIFACT_ROOT="$(pwd)/.synrail"
synrail init --artifact-root "$ARTIFACT_ROOT"
# once this root reflects one verified working state:
synrail save --artifact-root "$ARTIFACT_ROOT"
# after the agent writes final_result.json or final_result.txt:
synrail check --artifact-root "$ARTIFACT_ROOT"
# after applying only that bounded repair:
synrail retry --artifact-root "$ARTIFACT_ROOT"
synrail restore --artifact-root "$ARTIFACT_ROOT"
```

The current fresh first-run contour is smaller:

```bash
ARTIFACT_ROOT="$(pwd)/.synrail"
synrail init --artifact-root "$ARTIFACT_ROOT"
# write final_result.json or final_result.txt under $ARTIFACT_ROOT or the project root
synrail check --artifact-root "$ARTIFACT_ROOT"
synrail repair-step --artifact-root "$ARTIFACT_ROOT"
```

This shell is intentionally thin:

- it auto-discovers the standard artifact files under one artifact root
- it auto-detects one sane project profile for the current project root
- it defaults the alpha restore-point checkpoint id to `working`
- it exposes `synrail save` as a thin human-facing action that saves and confirms the default working restore point
- it exposes `synrail confirm-restore` as the preferred human-facing alias for explicit restore-point confirmation
- it exposes `synrail repair-step` as the preferred human-facing alias for the existing prompt bridge
- it exposes `synrail retry` as the preferred human-facing alias for the existing `resume` path
- it keeps `synrail continue` as a compatibility alias for the same path
- it keeps the existing dev/runtime helpers underneath
- it does not introduce a new runtime semantics branch

The current trusted local install path is now:

```bash
python3 -m venv --system-site-packages .venv
.venv/bin/python -m pip install -e . --no-build-isolation
```

The older `setup.py install` route still works as a compatibility fallback, but editable install is now the verified alpha path on this local toolchain.

Optional alpha telemetry now sits on the same artifact root:

```bash
synrail init --artifact-root "$ARTIFACT_ROOT" --telemetry-opt-in --tester-id your_name
synrail telemetry export --artifact-root "$ARTIFACT_ROOT"
```

That writes one bounded session replay plus one GitHub-Issues-ready markdown body without including file contents.

## Included helpers

### `attest_target_surface.sh`

Purpose:

- collect enough evidence to say whether the intended target surface is actually the one being inspected

Useful when:

- a fix, test, or deploy claim depends on the truth of the target environment

Guarantees:

- emits an explicit pass/fail attestation result
- records concrete surface facts

Does not guarantee:

- that the target is healthy
- that a fix is correct
- that production behavior is repaired

### `require_attested_target_surface.sh`

Purpose:

- enforce attestation as a gate before a target-surface claim is treated as reviewable

Guarantees:

- blocks the next step if attestation did not pass

Does not guarantee:

- quality of the patch or test
- correctness of the target repo contents

### `intake_incident_hypothesis.sh`

Purpose:

- capture one narrow runtime clue as a bounded hypothesis

Guarantees:

- records a search-space reducer explicitly

Does not guarantee:

- diagnosis truth
- fix proof
- runtime confirmation

### `confirm_live_production_fix.sh`

Purpose:

- record one post-deploy runtime check against an expected outcome

Guarantees:

- compares observed external behavior to an expected result
- emits an explicit confirmation result

Does not guarantee:

- full feature completeness
- broad system health

### `incident_operator_flow.sh`

Purpose:

- preserve the intended incident order:
  - intake
  - attestation
  - confirmation

Guarantees:

- makes the basic flow harder to skip accidentally

Does not guarantee:

- good diagnosis
- good patches
- closure on its own

### `synrail_spine_v0.py`

Purpose:

- provide a minimal executable spine prototype with machine-readable state and hard transition gates
- hold the current bounded orchestration contour directly

Guarantees:

- can initialize a run state
- can deny disallowed transitions
- can emit one structured blocked-transition report with explicit blocker precedence
- can apply doctor records back into the state machine
- can apply bundle and closure artifacts back into the state machine
- can run one bounded `doctor -> optional preparation -> bundle -> closure` contour with optional `refresh`, `compare`, and worked-envelope emission
- can now absorb one `mode_selection_receipt_v0` so a preparation-aware strong-path choice can enter that bounded contour directly
- can now emit one machine-readable repair handoff naming the missing continuation inputs and bounded runtime defaults for a non-green state
- can now auto-synthesize one richer repair packet from current runtime truth and continue from that packet instead of depending only on a long raw flag replay
- can now trust embedded packet truth strongly enough that selection and repair-handoff replay no longer need temporary unpacked side files in the normal `resume` path
- can now record one explicit runtime-resume origin so continuation from a non-green state is machine-readable on the same artifact surface
- can now block continuation explicitly at `repair_handoff` when the supplied continuation inputs are still incomplete
- can carry one blocked-readiness contour back into accepted closure when the missing identity and proof inputs are repaired
- can carry one partial-proof contour back into accepted closure when the missing proof sections are supplied
- can carry one degraded recovery contour back into accepted closure through refresh reconciliation
- can emit one primary canonical run artifact from the spine-owned contour
- can emit machine-readable state

Does not guarantee:

- full product orchestration
- complete schema validation
- final operator UX

### `synrail_bundle_v0.py`

Purpose:

- assemble a minimal machine-readable proof bundle from a final result artifact plus bundle inputs

Guarantees:

- emits one normalized bundle artifact
- classifies it as `COMPLETE`, `PARTIAL`, or `INVALID`

Does not guarantee:

- semantic closure acceptance
- deep scenario validation
- full closure-engine behavior

### `synrail_proof_plan_v0.py`

Purpose:

- name the governed-path proof surface before bundle assembly starts

Guarantees:

- emits the seven required proof sections
- emits one named artifact path set for bundle-related outputs

Does not guarantee:

- that the planned artifacts are semantically correct
- closure acceptance on its own

### `synrail_preparation_receipt_v0.py`

Purpose:

- record whether the planned governed-path proof surface reached a complete first bundle pass

Guarantees:

- compares one proof plan to one assembled bundle
- records whether the bundle is closure-ready on the first pass

Does not guarantee:

- closure acceptance on its own
- deep semantic proof validation

It can now also be called from the bounded orchestration path when preparation outputs are requested.

### `synrail_governed_cost_delta_v0.py`

Purpose:

- compare an unprepared and prepared governed path as one bounded cost-reduction slice

Guarantees:

- emits one machine-readable delta for operator minutes, interventions, repair cycles, and closure latency
- records whether first-pass proof readiness improved without a safety regression

Does not guarantee:

- broad economics proof across every governed path
- baseline-vs-Synrail comparison on its own

### `synrail_checkpoint_v0.py`

Purpose:

- treat checkpoint as one minimal kernel lifecycle rather than one loose snapshot helper

Guarantees:

- can create one checkpoint record from a current contour
- can verify required checkpoint artifacts, schema validity, and state consistency
- can restore a checkpoint artifact set and require restore verification before success
- can now roll back checkpoint-owned restore artifacts when restore verification fails on a conflicting target surface

Does not guarantee:

- broad snapshotting across every future runtime dependency
- final artifact-consistency semantics for every conflict case
- broad restore conflict handling beyond the current bounded checkpoint manifest

### `synrail_repair_packet_v0.py`

Purpose:

- emit one richer continuation packet for a non-green state

Guarantees:

- embeds one repair handoff
- embeds one explicit resumability reading
- embeds one compact continuation core for the default runtime contract
- embeds one continuation plan
- embeds one repair-input set
- embeds one runtime output-default set
- embeds one repair-receipt context when runtime truth already has prior continuation progression
- embeds one packet-native repair-history chain across multiple continuation stages
- can now rebuild one later repair packet from one earlier packet instead of forcing a full context replay each time
- embeds one explicit repair-termination reading so runtime can stop a stalled loop before the next blind retry
- records provided vs missing continuation inputs
- records whether the current contour is repairable or terminal

Does not guarantee:

- broad workflow planning
- deep multi-run coordination
- a mature continuation packet that captures every future runtime dependency

### `synrail_artifact_consistency_v0.py`

Purpose:

- check whether current-state runtime artifacts are still consistent with the source-of-truth state file

Guarantees:

- treats `state_file` as the current source of truth
- checks current-state derived artifacts for run/task/state mismatches
- returns one bounded dominant conflict with explicit precedence

Does not guarantee:

- every future artifact family is already covered
- deep historical consistency across old stage artifacts

### `synrail_artifact_repair_receipt_v0.py`

Purpose:

- emit one machine-readable repair receipt between packet-first continuation steps

Guarantees:

- records which repair step actually completed
- records which artifact and sub-surface hints remain stale afterward
- records one operator-facing evidence view naming the next exact stale sub-surfaces and required inputs
- records whether continuation crossed into one non-resumable boundary
- records one bounded repair-history progression
- records one explicit repair-history chain that can live inside later stage repair packets

Does not guarantee:

- broad repair orchestration on its own
- automatic packet synthesis on its own
- full runtime coordination without the spine

### `synrail_observability_v0.py`

Purpose:

- emit one bounded observability record from current runtime artifacts

Guarantees:

- records one report summary
- records one state-transition log
- records one repair-attempt log
- records one rejection log
- records one sanitized session export with no secret values

Does not guarantee:

- hosted telemetry
- broad tracing across every external system

### `synrail_alpha_telemetry_v0.py`

Purpose:

- record one opt-in alpha command sequence and export one bounded session replay

Guarantees:

- records command names and flag names without file contents
- records state at error, component error class, repair attempt count, version, and OS
- emits one GitHub-Issues-ready markdown body beside the replay JSON

Does not guarantee:

- automatic upload
- hosted dashboards
- sensitive-content capture

### `synrail_reproducibility_v0.py`

Purpose:

- compare two canonical run artifacts for one bounded reproducibility reading on key runtime truth

Guarantees:

- compares blocking result, stopping stage, reason, resulting state, repair-history, repair-packet family, and next safe step
- emits one machine-readable reproducibility verdict for the paired runs

Does not guarantee:

- broad determinism proof across every runtime family
- byte-for-byte artifact equality across repeated runs

### `synrail_second_operator_v0.py`

Purpose:

- inspect whether one packet-first continuation path is followable by a second operator without hidden author memory

Guarantees:

- records whether the visible entry is now only `state_file + repair_packet`
- records whether repair-step, required-input, and operator-focus truth are explicit enough for the continuation path
- emits one bounded second-operator verdict

Does not guarantee:

- a real user study on its own
- broad usability proof across every continuation family

### `synrail_thin_output_v0.py`

Purpose:

- compress one non-green runtime contour into one smaller operator-facing diagnosis without replacing state, report, or packet truth

Guarantees:

- emits one bounded `default` surface with summary, diagnosis, next step, and suggested command
- emits one bounded `dev` surface with compact technical lines from the same contour
- can now surface one verified matching checkpoint as a restore hint only when it belongs to the same run and task contour
- can now surface one concrete consistency-recovery action when the non-green contour already has an explicit restore-or-reemit plan

Does not guarantee:

- a broad interactive shell
- replacement of the underlying runtime artifacts as sources of truth

### `synrail_repair_prompt_bridge_v0.py`

Purpose:

- build one bounded next-agent prompt from the current repair packet

Guarantees:

- records current repair step, required inputs, allowed scope, forbidden scope, and must-pass checks
- keeps the follow-up prompt anchored to the packet-owned repair truth instead of a looser narrative summary

Does not guarantee:

- broad planning across multiple future repair steps
- semantic completion on its own

### `synrail_checkpoint_operator_reading_v0.py`

Purpose:

- check whether one restored verified-working contour stays readable without operator ambiguity once second-operator and thin-output surfaces are combined

Guarantees:

- verifies that the contour stays followable by a second operator
- verifies that the operator-facing output names the fresh forward boundary instead of suggesting named `resume`
- emits one bounded combined-reading verdict

Does not guarantee:

- a broad usability study across every fresh-orchestration contour
- replacement of the underlying second-operator or thin-output artifacts

### `synrail_consistency_recovery_v0.py`

Purpose:

- translate one artifact-consistency failure plus one optional verified checkpoint into one concrete restore-or-reemit recovery plan

Guarantees:

- records which artifact ids should be restored from checkpoint
- records which artifact ids should be re-emitted from `state_file`
- emits one explicit primary action when the mixed corrupt/stale derived surface is recoverable without operator ambiguity

Does not guarantee:

- broad artifact repair planning across every future artifact family
- recovery of the source `state_file` itself

### `synrail_consistency_recovery_prompt_v0.py`

Purpose:

- build one bounded next-agent prompt from one explicit restore-or-reemit recovery plan

Guarantees:

- records allowed scope directly from the listed restore and re-emit artifact ids
- records forbidden scope that explicitly keeps `state_file` out of bounds
- carries operator instructions into both the prompt body and must-pass list

Does not guarantee:

- broad remediation planning outside the current artifact recovery set
- semantic readiness or closure on its own

### `synrail_consistency_recovery_prompt_reading_v0.py`

Purpose:

- verify that one consistency-recovery prompt stays bounded to the listed restore-or-reemit plan

Guarantees:

- checks allowed scope against the recovery action set
- checks that recovery instructions survive into the prompt and must-pass lists
- emits one bounded prompt-drift verdict

Does not guarantee:

- broad prompt-quality proof across unrelated continuation families
- replacement of the recovery plan as the source of truth

### `synrail_operator_brief_v0.py`

Purpose:

- compress current runtime truth into one bounded operator-facing brief without replacing the packet, report, or state as sources of truth

Guarantees:

- records result, blocker, doctor verdict, resumability family, current repair step, required inputs, stale sub-surfaces, and one primary operator action
- records whether another `resume` still makes sense or whether the contour should stop and move into a new run

Does not guarantee:

- a broad interactive operator shell
- replacement of the underlying runtime artifacts

### `synrail_continuation_adoption_v0.py`

Purpose:

- inspect one continuation fixture and emit one compact adoption-friction record

Guarantees:

- records whether the root entry is packet-only
- records visible continuation side-file count
- records repeated doctor-block events across staged runs
- records whether repair history is still visible in the primary artifact

Does not guarantee:

- broad runtime economics
- substitute comparison on its own

### `synrail_continuation_adoption_delta_v0.py`

Purpose:

- compare two continuation adoption records and emit one compact friction delta

Guarantees:

- records side-file reduction
- records whether packet-only entry was gained
- records whether repeated doctor pressure and accepted terminal truth were preserved

Does not guarantee:

- broad usability proof across every continuation family
- full product economics on its own

### `synrail_closure_v0.py`

Purpose:

- emit a machine-readable closure verdict from run state plus proof bundle

Guarantees:

- identifies accepted vs claimed-not-accepted state
- emits a blocking reason when closure is not accepted
- emits one narrow next safe step

Does not guarantee:

- deep semantic scenario validation
- full refresh-chain automation
- full orchestration behavior

### `synrail_refresh_v0.py`

Purpose:

- refresh state after doctor, proof, closure, or recovery changes in deterministic order

Guarantees:

- updates machine-readable state
- emits a machine-readable refresh report
- invalidates over-green closure state when lower-level evidence worsens
- can reconcile one repaired recovery contour back into accepted closure after completed reverification

Does not guarantee:

- full dependency discovery
- broad orchestration behavior
- rich multi-run coordination

### `synrail_cli_v0.py`

Purpose:

- provide one small terminal-first operator entrypoint for the executable slices

Guarantees:

- exposes compact state reading
- exposes bundle, closure, and refresh commands through one CLI
- exposes one bounded orchestration path for `doctor -> optional preparation -> bundle -> closure`
- exposes one named `resume` path that now defaults to packet-first continuation through a sibling `repair_packet.json`
- exposes one named `resume` path that now treats the packet's embedded continuation core as the default continuation contract
- exposes one named `resume` path that now also supports stage-aware sibling discovery plus one narrow `resume_inputs.json` override file
- exposes one `repair-packet` path that can now inherit context from one previous packet for lower-replay multi-step continuation
- exposes one `repair-packet` command that groups continuation contract, continuation plan, repair inputs, output defaults, and current selection/preparation context
- exposes baseline comparison through the same CLI layer

Does not guarantee:

- full orchestration coverage
- interactive UX
- broad product shell behavior

### `synrail_repair_handoff_v0.py`

Purpose:

- emit one machine-readable continuation contract for a non-green state before runtime resume starts

Guarantees:

- names the current `from_state`
- names the current `blocking_reason`
- lists the required continuation inputs
- emits bounded runtime defaults for recovery-driven continuation when refresh reconciliation is still required

Does not guarantee:

- automatic repair of the missing inputs
- broad repair-packet synthesis
- continuation correctness on its own

### `synrail_mode_selector_v0.py`

Purpose:

- emit one cost-aware mode recommendation before the operator enters a heavier contour

Guarantees:

- can recommend `FULL_GOVERNED_PATH`, `LIGHTWEIGHT_BASELINE`, or `HYBRID_EXCEPTION`
- can expose one short measured reason and one narrow next safe step
- can optionally steer the strong path toward a prepared governed contour when bounded governed-path cost evidence supports it

Does not guarantee:

- full policy automation
- deep runtime execution
- automatic mode enforcement

### `synrail_mode_receipt_v0.py`

Purpose:

- emit one machine-readable receipt recording whether the operator followed the mode recommendation

Guarantees:

- records the recommended mode
- records the selected mode
- records whether the heavier contour was entered or skipped
- can record whether the selected governed path was explicitly taken with preparation

Does not guarantee:

- runtime correctness on its own
- economic correctness beyond the supplied recommendation artifact

### `synrail_runtime_v0.py`

Purpose:

- preserve compatibility for the bounded runtime contour while the contour itself moves closer to the spine

Guarantees:

- forwards to the spine-owned orchestration contour
- keeps older runtime-shaped entry usage compatible

Does not guarantee:

- ownership of the orchestration loop itself
- broad orchestration coverage
- multi-run scheduling

### `synrail_baseline_harness_v0.py` and `synrail_baseline_harness_v1.py`

Purpose:

- compare one baseline artifact against one Synrail artifact and emit a machine-readable verdict
- add a second comparison path that includes simple economics rather than only qualitative comparison

Guarantees:

- produces one repeatable comparison record
- avoids purely prose-based comparison outcomes
- `v1` also emits operator-cost and false-green-exposure deltas in machine-readable form

Does not guarantee:

- statistical proof
- deep scenario normalization
- broad benchmarking behavior

### `synrail_hybrid_status_v0.py`

Purpose:

- read the current economics aggregate plus hybrid comparison records and emit one explicit hybrid-mode status

Guarantees:

- emits one machine-readable `JUSTIFIED`, `PROVISIONAL`, or `DEMOTED` reading
- keeps hybrid policy tied to measured evidence rather than only to prose

Does not guarantee:

- final product economics
- broad policy discovery
- more hybrid evidence than the repo already has

### `synrail_cost_of_control_v0.py`

Purpose:

- aggregate multiple economics-aware comparison records into one cost-of-control reading

Guarantees:

- emits one machine-readable aggregate artifact
- names justified-cost, baseline-sufficient, and under-proven path buckets
- surfaces the current cost hotspots

Does not guarantee:

- live operator telemetry
- a complete economic model
- automatic CLI integration

### `synrail_validate_v0.py`

Purpose:

- validate one Synrail JSON artifact against one local schema

Guarantees:

- catches basic structural mismatches
- emits an explicit valid or invalid result

Does not guarantee:

- full JSON Schema coverage
- semantic correctness
- broad enforcement by itself

### `synrail_doctor_v1.py`

Purpose:

- emit one machine-readable readiness verdict for the intended run class

Guarantees:

- evaluates a narrow gate set
- can probe git cleanliness on a target surface
- can probe artifact-path parent existence
- can probe helper entrypoint presence
- can probe credential env presence
- can probe whether a path-based credential env points at something real
- can probe exact prompt identity file presence
- can probe expected exact task identity mismatch
- can probe expected target-surface identity mismatch
- emits a doctor record with blocking failure classes
- can write doctor status back into the run state

Does not guarantee:

- deep environment probing
- provider reachability validation
- full diagnostics coverage

### `synrail_mode_selector_v0.py`

Purpose:

- recommend the cheapest honest mode before the operator enters a heavier contour

Guarantees:

- reads current cost-of-control evidence
- can incorporate current hybrid-status demotion
- emits one machine-readable mode recommendation
- can steer weak or demoted-hybrid paths back to baseline by default

Does not guarantee:

- perfect scenario classification
- replacement of human judgment on novel scenarios
- automatic enforcement by itself

### `synrail_mode_receipt_v0.py`

Purpose:

- record one machine-readable receipt showing whether the operator followed a mode recommendation

Guarantees:

- records selected mode
- records whether a heavier contour was entered
- records estimated avoided operator cost when baseline is selected

Does not guarantee:

- that the recommendation itself was correct
- that the baseline path was executed well

## Operating rule

If a helper starts accumulating broad product logic, large orchestration behavior, or environment-specific sprawl, it should probably stop living under `tools/reference/` in this repo shape.

### `synrail_artifact_repair_receipt_v0.py`

Purpose:

- emit one machine-readable repair receipt that can also accumulate one packet-native repair-history chain across continuation stages

Guarantees:

- records the completed or still-active repair step
- records the next exact stale sub-surfaces the operator should focus on
- can be embedded back into the next repair packet so continuation history survives with less side-file replay

Does not guarantee:

- perfect operator guidance outside the bounded continuation families already modeled in the runtime

### `synrail_substitute_harness_v0.py`

Purpose:

- compare one concrete substitute stack against one Synrail path

Guarantees:

- uses the same bounded economics surface as the baseline harness
- emits a substitute-specific machine-readable verdict
- can say `SYNRAIL_BETTER`, `SUBSTITUTE_GOOD_ENOUGH`, or `UNCLEAR`

Does not guarantee:

- a full external benchmark program
- broad scenario normalization across teams or environments

### `synrail_substitute_pressure_v0.py`

Purpose:

- aggregate a small set of substitute comparison records into one pressure reading

Guarantees:

- records verdict counts across the current substitute tranche
- names the strongest Synrail edge and the current non-winning substitute stacks

Does not guarantee:

- broad market proof
- automatic substitute selection policy on its own

### `synrail_operator_brief_v0.py`

Purpose:

- compress one current runtime snapshot into one smaller operator-facing handoff

Guarantees:

- preserves blocker, current repair step, required inputs, stale sub-surfaces, and one primary next action
- stays derived from `state`, `report`, `repair_packet`, and optional `doctor`

Does not guarantee:

- replacement of the underlying runtime artifacts
- full multi-stage reading on its own

### `synrail_operator_brief_chain_v0.py`

Purpose:

- compress several operator briefs into one stage-by-stage repair reading for a multi-stage contour

Guarantees:

- preserves one ordered sequence of operator actions across an ugly continuation family
- records the final operator action and final resumability family

Does not guarantee:

- replacement of the underlying stage briefs
- broad operator workflow automation

### `synrail_operator_render_v0.py`

Purpose:

- turn one operator brief or one operator-brief chain into a small markdown handoff for a human operator

Guarantees:

- stays strictly derived from the operator brief surfaces
- preserves the main action, next step, current step, required inputs, and chain progression

Does not guarantee:

- any new source of runtime truth
- replacement of the underlying brief or chain records

### `synrail_operator_render_adoption_v0.py`

Purpose:

- measure whether one operator render is shorter than its source brief surface while still preserving the key operator markers

Guarantees:

- compares one source artifact to one render artifact
- records line reduction and missing marker truth explicitly

Does not guarantee:

- broad usability proof on its own
- real user comprehension beyond the bounded markers it checks

### `synrail_operator_render_adoption_delta_v0.py`

Purpose:

- aggregate a small set of operator-render adoption records into one bounded reading

### `synrail_operator_reading_v0.py`

Purpose:

- check whether one derived operator render still preserves the operator decision on a less-curated contour that already matters to a second operator

Guarantees:

- compares one `second_operator` reading, one operator brief, and one derived render
- records whether the render still carries the required stop/repair markers

Does not guarantee:

- broad usability proof across many operators
- replacement of the second-operator pressure slices

### `synrail_externality_pressure_v0.py`

Purpose:

- aggregate a short external-ish pressure pass for one uglier contour from reproducibility, second-operator, and operator-reading records

Guarantees:

- records whether the contour survives those three bounded external-ish readings together

Does not guarantee:

- broad external market proof
- replacement of harsher substitute testing
