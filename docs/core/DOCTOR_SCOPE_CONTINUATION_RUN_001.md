# DOCTOR_SCOPE_CONTINUATION_RUN_001

This run checks that the new out-of-scope doctor blocker flows honestly through continuation, thin output, and prompt generation.

Inputs:
- verified working state restored from `checkpoint_run_003`
- doctor failure from `doctor_pressure_test_007`
- continuation packet rebuilt from the blocked state

What we check:
- the state moves to `DOCTOR_BLOCKED`
- continuation does not treat the old `--clean-surface` flag as already satisfying the current dirty-surface blocker
- thin output reads this contour as `SCOPE_VIOLATION`
- the generated prompt stays bounded to `clean_execution_surface_record`

Expected truth:
- `ready_for_resume = false`
- `missing_inputs = [clean_surface_confirmation]`
- `outcome_class = SCOPE_VIOLATION`
- `verdict = FOLLOWUP_SCOPE_PRESERVED`
