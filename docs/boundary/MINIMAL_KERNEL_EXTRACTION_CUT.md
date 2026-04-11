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

- Hetzner transport specifics
- Google VM / Node 2 specifics
- PM2 process details
- Bedrock/Aider invocation particulars
- helper-path contamination details
- credential-source specifics for one environment

The kernel may require reports about these things.

The kernel should not define itself by them.

## What stays proving-ground-only

The following remain proving-ground-only and should not shape the extracted repo as product identity:

- `NODE2_IMAGE_TRIGGER_FIX_001`
- `USBAGENT_V2_1_STABLE`
- one-off runtime incidents
- incident-specific hypothesis records
- production confirmation records for one downstream bot
- dirty repo archaeology
- temporary recovery handoffs for one battlefield knot

## Current honest blocker to extraction

The main blocker is no longer best described as a credential-surface problem.

The current blocker is:

- no accepted proof-complete exact-task closure yet under the current minimal kernel

More precisely:

- architectural separation is already strong
- product separation is already strong
- operational separation is still incomplete because closure value has not yet been proven through a completed kernel-governed cycle

## What would unlock the cut

The smallest credible unlock is now:

1. one real narrow production incident goes strictly through `incident_operator_flow.sh`
2. that incident reaches accepted closure or accepted live-fix confirmation honestly
3. the post-incident evaluation shows the flow is at least not worse on `blocker-to-closure cycle count`
4. the same discipline then survives at least one more narrow incident

This is still weaker than the full campaign target, but strong enough to make a separate-repo cut stop looking premature.

## Decision rule

Do not extract around the current proving ground.

Extract around the kernel behaviors that remain valid even after the proving ground changes.
