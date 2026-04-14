# DOCTOR_CONTINUATION_RUN_001

Run one pressure slice where helper import drift flows from doctor into continuation truth.

## Purpose

This is the kernel check behind the helper import drift fix.
We want to see that the failure does not stay trapped inside an isolated doctor record.
It must enter the continuation path as machine-readable repair truth.

## Canonical artifacts

- `fixtures/doctor_continuation_run_001/state.json`
- `fixtures/doctor_continuation_run_001/doctor.json`
- `fixtures/doctor_continuation_run_001/repair_packet.json`
- `fixtures/doctor_continuation_run_001/prompt.json`

## Expected reading

The updated state should move to `DOCTOR_BLOCKED`.
The repair packet should then expose:
- `current_step_id = restore_readiness_truth`
- `next_step_required_inputs = [helper_path]`
- `next_step_subsurface_ids = [helper_entrypoint_record]`

The generated prompt should preserve that same bounded repair scope.
