# CHECKPOINT_SCOPE_VIOLATION_001

This run checks that a verified checkpoint stays useful and readable on a `SCOPE_VIOLATION` contour.

Inputs:
- blocked scope contour from `doctor_scope_continuation_run_001`
- verified working checkpoint from `checkpoint_run_003`

What we check:
- thin output surfaces checkpoint availability on the same run/task contour
- the suggested command does not collapse into a vague repair hint
- a second operator can still follow the contour without author memory
- the combined checkpoint reading stays non-ambiguous

Expected truth:
- `outcome_class = SCOPE_VIOLATION`
- `restore_available = true`
- `suggested_command = restore-checkpoint or move to a clean in-scope surface, then resume`
- `verdict = FOLLOWABLE_WITHOUT_OPERATOR_AMBIGUITY`
