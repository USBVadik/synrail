# Acceptance Hardening 001

## Purpose

Harden acceptance logic as an explicit runtime-owned truth object before external alpha.

This slice adds:

- explicit `acceptance_criteria.json`
- explicit `acceptance_validation.json`
- light `criteria_revision_id`
- closure blocking when criteria are stale or invalid

## What changed

The runtime now stores one explicit acceptance-criteria record in the alpha artifact root and validates it against:

- current project profile
- current run task class
- current acceptance gate set
- current proof-section standard

Closure now carries the validation result and will not accept when criteria drift is detected.

## Proofs

### 1. Init writes acceptance criteria

See:

- `../fixtures/alpha_acceptance_init_run_001/lane/acceptance_criteria.json`

This proves acceptance logic is no longer only implicit inside closure code.

### 2. Valid criteria do not create a false reject

See:

- `../fixtures/acceptance_hardening_run_001/validation_valid.json`
- `../fixtures/acceptance_hardening_run_001/closure_valid.json`

Result:

- validation = `VALID`
- closure = `ACCEPTED`

This matters because the hardening layer does not make an already accepted contour fail just because criteria are now explicit.

### 3. Weakened or misbound criteria do not create a false accept

See:

- `../fixtures/acceptance_hardening_run_001/validation_stale_gate.json`
- `../fixtures/acceptance_hardening_run_001/closure_stale_gate.json`
- `../fixtures/acceptance_hardening_run_001/validation_stale_task_class.json`
- `../fixtures/acceptance_hardening_run_001/closure_stale_task_class.json`

Results:

- weakened gate set -> `CRITERIA_GATE_SET_STALE`
- wrong task class -> `CRITERIA_TASK_CLASS_STALE`
- closure -> `CLAIMED_NOT_ACCEPTED`
- closure blocker -> `ACCEPTANCE_CRITERIA_STALE`

This matters because acceptance no longer trusts a stale or weakened criteria source.

### 4. Runtime check now carries criteria validation

See:

- `../fixtures/acceptance_check_run_002/lane/acceptance_validation.json`
- `../fixtures/acceptance_check_run_002/lane/closure.json`
- `../fixtures/acceptance_check_run_002/check_stdout.txt`

This proves the new layer is not only a helper-side artifact. It now flows through the `synrail check` contour.

## Boundary

This slice does not add:

- richer continuation families
- richer repair history
- richer operator evidence
- new policy branches

It only hardens the source of acceptance truth.
