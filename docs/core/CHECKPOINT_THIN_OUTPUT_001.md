# CHECKPOINT_THIN_OUTPUT_001

Run one combined pressure slice for `checkpoint + thin-output` on a non-green contour.

## Purpose

This is a narrow check that a verified checkpoint becomes visible in the thin output exactly where we need it:
- the contour is non-green
- the checkpoint is verified
- the checkpoint belongs to the same run/task contour

## Canonical artifacts

- `fixtures/checkpoint_run_003/checkpoint_verify.json`
- `fixtures/executable_loop_runtime_non_resumable_run_004/starting_state.json`
- `fixtures/executable_loop_runtime_non_resumable_run_004/report.json`
- `fixtures/executable_loop_runtime_non_resumable_run_004/repair_packet.json`
- `fixtures/checkpoint_thin_output_run_001/thin_output.json`

## Expected reading

The thin output record should show:
- `outcome_class = NON_RESUMABLE`
- `restore_available = true`
- a restore-aware suggested command

That means the verified checkpoint is not just stored in the repo.
It is surfaced in the human-facing diagnosis at the moment a non-green contour needs it.
