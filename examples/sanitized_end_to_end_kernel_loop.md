# Sanitized End-to-End Kernel Loop Example

This example shows one compact `Synrail` flow from:

- machine-readable state
- to proof bundle
- to closure decision
- to refresh after degradation
- to baseline comparison

The example is intentionally small and sanitized.

## Scenario

Use one narrow proof-sensitive task class:

- `bounded_router_trigger_fix`

This is a good fit because:

- false completion is meaningful
- proof completeness matters
- recovery after misleading output is not free

## Step 1. Initialize run state

```bash
tmpdir=$(mktemp -d)
state="$tmpdir/state.json"

python3 tools/reference/synrail_spine_v0.py init \
  --run-id RUN_EXAMPLE_001 \
  --task-class bounded_router_trigger_fix \
  --output "$state"
```

At this point, the run is:

- `INITIALIZED`
- target surface unknown
- doctor unknown
- closure open

## Step 2. Simulate the minimum ready state

For a compact example, prepare a state that already has:

- attested target surface
- green doctor
- confirmed exact-task identity
- completed execution

```bash
python3 - <<'PY' "$state"
import json, sys
p = sys.argv[1]
state = json.load(open(p))
state["target_surface"]["status"] = "ATTESTED"
state["doctor"]["status"] = "PASS"
state["integrity"]["exact_task_identity_ok"] = True
state["execution"]["status"] = "COMPLETED"
json.dump(state, open(p, "w"), indent=2)
PY
```

## Step 3. Assemble a proof bundle

Use a real final-result artifact plus explicit bundle inputs.

```bash
bundle="$tmpdir/bundle.json"
readback="$tmpdir/readback.txt"
scenario="$tmpdir/scenario.txt"

printf 'readback ok\n' > "$readback"
printf 'scenario ok\n' > "$scenario"

python3 tools/reference/synrail_cli_v0.py bundle-check \
  --final-result /Users/usbdick/Documents/New\ project/docs/context/runtime_artifacts/NODE2_IMAGE_TRIGGER_FIX_001_CAMPAIGN_RUN_012.json \
  --task-class bounded_router_trigger_fix \
  --baseline-identity trusted_clean_clone \
  --execution-surface-identity node2_attested_surface \
  --prompt-identity exact_prompt_001 \
  --task-identity NODE2_IMAGE_TRIGGER_FIX_001 \
  --readback "$readback" \
  --scenario-proof "$scenario" \
  --output "$bundle"
```

Expected reading:

- bundle status = `COMPLETE`

## Step 4. Decide closure

```bash
closure="$tmpdir/closure.json"

python3 tools/reference/synrail_cli_v0.py closure \
  --state-file "$state" \
  --bundle-file "$bundle" \
  --output "$closure" \
  --update-state
```

Expected reading:

- closure verdict = `ACCEPTED`
- run state moves to `CLOSURE_ACCEPTED`

## Step 5. Refresh after degradation

Now simulate a real degradation event:

- doctor falls from `PASS` to `FAIL`

```bash
refresh="$tmpdir/refresh.json"

python3 tools/reference/synrail_cli_v0.py refresh \
  --state-file "$state" \
  --event-type DOCTOR_UPDATE \
  --doctor-status FAIL \
  --output "$refresh" \
  --update-state
```

Expected reading:

- closure downgraded to `CLAIMED_NOT_ACCEPTED`
- blocking reason = `DOCTOR_NOT_GREEN`
- next safe step = `run doctor and clear blocking failure classes`

This is the anti-drift behavior:

- lower-level evidence worsened
- higher-level closure claim was invalidated automatically

## Step 6. Compare against baseline

Use the sanitized fixture pair under `fixtures/`:

- `fixtures/comparison_input_strong_baseline_v0.json`
- `fixtures/comparison_input_strong_synrail_v0.json`

```bash
comparison="$tmpdir/comparison.json"

python3 tools/reference/synrail_baseline_harness_v0.py \
  --baseline-file fixtures/comparison_input_strong_baseline_v0.json \
  --synrail-file fixtures/comparison_input_strong_synrail_v0.json \
  --output "$comparison"
```

Expected reading:

- verdict = `SYNRAIL_BETTER`

## What this example shows

This is the smallest current worked loop where `Synrail` behaves like an executable kernel:

1. state exists as machine-readable artifact
2. bundle exists as machine-readable artifact
3. closure exists as machine-readable verdict
4. refresh can invalidate stale closure
5. baseline comparison can evaluate the path explicitly

## What this example does not show

It does not yet show:

- one-command end-to-end orchestration
- full doctor runtime
- full remote attestation workflow
- rich recovery branching

Those belong to later layers.
