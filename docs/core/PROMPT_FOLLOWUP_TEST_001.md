# PROMPT_FOLLOWUP_TEST_001

Run one follow-up pass on `generate-prompt` over an active repair step.

## Purpose

This is a narrow check that the generated follow-up prompt still preserves bounded scope on the next repair step.
It should keep:
- the current step
- the allowed repair scope
- the must-pass constraints
- the next-step reading from thin output

## Canonical artifacts

- `fixtures/executable_loop_compound_continuation_run_009/stage1_repair_packet.json`
- `fixtures/prompt_followup_test_001/thin_output.json`
- `fixtures/prompt_followup_test_001/prompt.json`
- `fixtures/prompt_followup_test_001/followup.json`

## Expected reading

The follow-up record should land at `FOLLOWUP_SCOPE_PRESERVED` with no missing markers.
That means the generated prompt is still a bounded bridge into the next repair attempt, not a scope-broadening narrative summary.
