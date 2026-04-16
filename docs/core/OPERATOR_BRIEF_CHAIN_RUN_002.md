# OPERATOR_BRIEF_CHAIN_RUN_002

## Purpose

Record the second canonical operator-brief chain on a contour that does not end in accepted terminal closure.

This slice exists to prove the complementary operator-chain behavior:

- not only how a repair sequence ends at a non-resumable accepted boundary
- but also how it should end when the contour remains repairable in theory yet the bounded repair loop must stop and restart

## Artifacts

The canonical fixture for this run now lives at:

- `fixtures/operator_brief_chain_run_002/operator_brief_chain.json`
- `fixtures/operator_brief_chain_run_002/stage0_operator_brief.json`
- `fixtures/operator_brief_chain_run_002/stage1_operator_brief.json`
- `fixtures/operator_brief_chain_run_002/stage2_operator_brief.json`

Source contours:

- `fixtures/executable_loop_compound_continuation_run_010/stage0_run.json`
- `fixtures/executable_loop_compound_continuation_run_010/stage1_run.json`
- `fixtures/second_operator_test_002/starting_run.json`

## Scenario

This chain preserves one ugly operator sequence:

1. `stage0`
   - proof is still partial
   - the operator should repair the current proof step
2. `stage1`
   - doctor pressure returns
   - the operator should still repair the current readiness step
3. `stage2`
   - the same doctor pressure remains
   - the repair loop is now terminated by `MAX_REPAIR_ATTEMPTS`
   - the operator should stop replaying this contour and start a new run

## Current result

The chain summary now says:

- `stage_count = 3`
- `action_counts.REPAIR_CURRENT_STEP = 2`
- `action_counts.STOP_AND_START_NEW_RUN = 1`
- `stop_stage_ids = [stage2]`
- `final_action = STOP_AND_START_NEW_RUN`
- `final_next_safe_step = restore the trusted baseline and expected target-surface identity`
- `final_resumability_family = REPAIRABLE_COMPOUND`

This matters because the final stage is not terminal accepted.

The contour is still structurally repairable, but the bounded loop has already exhausted its allowed retries.

## Why this matters

The first operator-brief chain proved:

- repair through several stages
- then follow a terminal accepted boundary

This second chain now proves:

- repair through several stages
- then stop the bounded loop and restart instead of pretending that more replay is still the right operator move

That is the more dangerous decision for the operator layer to get wrong.

## Current reading

The shortest honest reading is:

- the operator-chain layer now covers both honest endings of a multi-stage contour:
  - follow the terminal boundary
  - stop and start a new run
- and the stop case is now grounded in explicit runtime termination truth instead of a prose-only operator judgment
