# EXECUTABLE_LOOP_COMPOUND_CONTINUATION_RUN_009

This fixture is the ninth canonical ugly packet-first continuation run.

Primary artifact:

- `fixtures/executable_loop_compound_continuation_run_009/run.json`

It proves one nastier ordered contour:

1. doctor target identity pressure blocks continuation inputs at stage 0
2. readiness repair completes and the run moves into partial supporting proof pressure
3. doctor pressure returns after that intermediate repair when target identity drifts again
4. proof then completes and the run moves into recovery pressure
5. recovery completes and the run crosses into accepted terminal truth

This run also proves two structural improvements at the same time:

- repair history is now first-class in the primary run artifact summary, not only inside the packet payload
- packet-first continuation now carries that history with fewer default side artifacts at the root level

The shortest reading is:

- `stage0`: `BLOCKED | repair_handoff | CONTINUATION_INPUTS_MISSING | DOCTOR_BLOCKED`
- `stage1`: `OK | closure | MISSING_PROOF_SECTIONS | PROOF_BUNDLE_PARTIAL`
- `stage2`: `BLOCKED | doctor | DOCTOR_NOT_GREEN | DOCTOR_BLOCKED`
- `stage3`: `OK | closure | RECOVERY_REVERIFICATION_INCOMPLETE | PROOF_BUNDLE_COMPLETE`
- `stage4`: `OK | refresh | NONE | CLOSURE_ACCEPTED`

The final primary artifact records:

- `repair_history.chain_length = 5`
- `repair_history.completed_step_ids = [restore_readiness_truth, complete_missing_proof_sections, complete_recovery_reverification]`
- `repair_history.last_result = NON_RESUMABLE_BOUNDARY_REACHED`

And the root fixture now keeps packet-first continuation relatively compressed:

- `repair_packet.json` remains
- `repair_handoff.json` is no longer default-emitted
- `repair_receipt.json` is no longer default-emitted
