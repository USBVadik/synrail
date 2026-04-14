# THIN_OUTPUT_CONSISTENCY_RECOVERY_001

This run proves that the thin operator-facing surface can name a concrete restore-or-reemit path for a non-green contour.

Inputs:
- non-green minimal continuation state
- verified matching checkpoint
- consistency recovery plan

What we check:
- thin output stays non-green
- restore availability is surfaced only for the matching verified checkpoint
- diagnosis includes the concrete recovery path instead of only raw consistency language

Expected truth:
- `outcome_class = DOCTOR_BLOCKED`
- `restore_available = true`
- `recovery_primary_action = RESTORE_CORRUPT_AND_REEMIT_STALE`
