# MINIMAL_KERNEL_EXTRACTION_CUT

## Purpose

Define the smallest honest `Synrail` kernel slice that could later move into a dedicated repository without dragging most of the current proving-ground noise with it.

This document exists to make extraction planning concrete while the project is still proving value.

It is not an extraction approval.

## Core rule

The extraction cut must describe:

- what the kernel would contain
- what stays adapter-side
- what stays proving-ground-only
- what still blocks the cut from being adopted as a separate repository

## Minimal kernel cut

The smallest believable kernel cut now includes:

### 1. Control contracts

- `SAFE_PROMOTION`
- `FORMAL_VALIDATION`
- proof-bundle standard
- exact-task closure spec
- exact-task progression
- transition-gate standard
- recovery-event standard
- readiness-unlock spec
- kernel-status contract

### 2. Truth and acceptance surfaces

- runtime truth surface
- evidence precedence
- consistency check
- state refresh chain
- doctor verdict logic
- evaluation-lane acceptance logic

### 3. Adapter-facing boundary

- product boundary
- adapter interfaces
- target-surface attestation rule
- bounded incident-hypothesis intake rule
- post-deploy production-confirmation rule

### 4. Minimal operational helpers that now behave like kernel references

- `tools/reference/require_attested_target_surface.sh`
- `tools/reference/intake_incident_hypothesis.sh`
- `tools/reference/confirm_live_production_fix.sh`
- `tools/reference/incident_operator_flow.sh`

These helpers are still proving-ground implementations, but they now express narrow kernel behavior strongly enough to count as reference implementations for extraction planning.

## What stays adapter-side

The following should remain adapter-side or environment-side, not kernel identity:

- one environment's transport specifics
- one environment's target-runtime specifics
- PM2 process details
- Bedrock/Aider invocation particulars
- helper-path contamination details
- credential-source specifics for one environment

The kernel may require reports about these things.

The kernel should not define itself by them.

## What stays proving-ground-only

The following remain proving-ground-only and should not shape the extracted repo as product identity:

- one proving-ground exact-task campaign
- one downstream product repo
- one-off runtime incidents
- incident-specific hypothesis records
- production confirmation records for one downstream bot
- dirty repo archaeology
- temporary recovery handoffs for one battlefield knot

## Current honest blocker to extraction

The main blocker is no longer a missing proof-complete closure.

The current blocker is:

- disciplined execution of the first bounded extraction move without widening the cut

More precisely:

- architectural separation is already strong
- product separation is already strong
- operational separation is now strong enough for extraction
- the remaining risk is execution sloppiness during the first extraction move

## What would unlock the cut

The smallest credible unlock has now been reached through:

1. multiple real narrow production incidents that went strictly through `incident_operator_flow.sh`
2. accepted live-fix confirmations reached honestly through that flow
3. one accepted proof-complete exact-task closure under governed exact-retry conditions

What remains is disciplined extraction execution, not proof absence.

## Decision rule

Do not extract around the current proving ground.

Extract around the kernel behaviors that remain valid even after the proving ground changes.
