# PROMPT_RETRY_GUARD_001

This run proves that a repeated helper-drift retry does not broaden the generated repair prompt.

Inputs:
- initial doctor-blocked helper-drift packet and prompt
- synthetic `STEP_NOT_COMPLETED` receipt on the same step
- follow-up packet and prompt generated from that receipt

What we check:
- current repair step stays the same across retries
- allowed scope stays the same
- required inputs stay the same
- next safe step stays the same

Expected truth:
- `verdict = RETRY_SCOPE_STABLE`
- `missing_markers = []`
