# CONSISTENCY_RECOVERY_PROMPT_001

This run checks whether a restore-or-reemit path can be handed to the next agent call without broadening scope.

Inputs:
- consistency recovery plan from `artifact_consistency_recovery_run_001`
- non-green thin output from `thin_output_consistency_recovery_run_001`

What we check:
- the prompt only names the restore and re-emit artifact actions
- state_file stays explicitly forbidden
- the operator instructions survive into the prompt body and must-pass list

Expected truth:
- `verdict = RECOVERY_PROMPT_BOUNDED`
- `allowed_scope = [report, repair_packet]`
