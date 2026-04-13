# EXECUTABLE_LOOP_MINIMAL_CONTINUATION_RUN_001

## Purpose

Prove that packet-first continuation now has one low-friction happy path.

This run exists to show that `resume` can now succeed from one compact continuation contract instead of depending on a wider set of continuation side artifacts.

## Artifacts

The canonical fixture lives at:

- `fixtures/executable_loop_minimal_continuation_run_001/starting_state.json`
- `fixtures/executable_loop_minimal_continuation_run_001/starting_repair_packet.json`
- `fixtures/executable_loop_minimal_continuation_run_001/run.json`

## Runtime shape

Start:

- `DOCTOR_BLOCKED`
- `CLAIMED_NOT_ACCEPTED`

Continuation entry:

- `resume --state-file state.json --repair-packet-file repair_packet.json`

Finish:

- `OK | accepted | NONE | CLOSURE_ACCEPTED | ACCEPTED`

## Why this is different

This contour no longer depends on extra root continuation files such as:

- `repair_handoff.json`
- `repair_receipt.json`
- `resume_inputs.json`
- `prompt_identity.txt`
- `task_identity.txt`

The packet itself now carries enough runtime truth for the normal continuation path.

## Current reading

The shortest honest reading is:

- packet-first continuation now has one smaller default contract
- that contract is now strong enough to carry a simple repaired continuation back to accepted closure
- and the operator path is now meaningfully lighter than the earlier packet-plus-sidecar continuation shape
