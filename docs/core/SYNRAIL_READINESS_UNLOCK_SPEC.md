# SYNRAIL_READINESS_UNLOCK_SPEC

## Purpose

Define what it means for an exact-retry readiness blocker to be truly unlocked inside `Synrail`.

This document exists so the move from denied transition to allowed transition is judged by explicit conditions.

## Core rule

A readiness unlock is accepted only when the blocked transition can be re-evaluated and changed from denial to allowance through explicit evidence.

## Unlock target for the current task

For `NODE2_IMAGE_TRIGGER_FIX_001`, the current unlock target is:

- `BLOCKED_READINESS -> READY_FOR_EXACT_RETRY`

## Unlock conditions

The unlock is achieved only when all of the following are true:

1. credential-surface recovery event is accepted
2. credential doctor no longer returns `NOT_ACCEPTABLE_CREDENTIAL_SURFACE`
3. exact-retry doctor no longer returns a readiness-blocking verdict
4. exact-retry lane no longer remains blocked on credential surface
5. exact-retry transition gate changes from `DENY_WITH_RECOVERY_PATH` to `ALLOW`
6. runtime truth surface no longer lists the credential blocker as active for exact retry

## Unlock non-conditions

The unlock is not achieved merely because:

- downstream auth error disappears once
- a session starts
- an operator believes credentials are present
- one surface changes but the doctor/gate chain is stale

## Result of unlock

When unlock succeeds, the product may say:

- exact retry is now ready to be attempted
- the next allowed transition is execution, not more readiness recovery

It still may not say:

- the exact task is fixed
- the exact task is closed

## Decision rule

If any unlock condition remains unmet, the readiness unlock is not accepted.
