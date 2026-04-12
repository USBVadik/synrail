# Reentry Lattice 001

## Purpose

State the shortest honest current reading of which reverse edges the executable `Synrail` kernel can already carry back toward greener states.

This document exists so the repo can summarize not only:

- outcome classes
- forward transitions
- degradation paths

but also whether the kernel can return from a less-green contour after the blocking condition is repaired.

## Current re-entry anchors

The current re-entry lattice is anchored by four canonical repair families, three named runtime continuation contours, one richer repair-packet layer, and one explicit repair-handoff layer:

1. blocked readiness to accepted closure
2. partial proof to accepted closure
3. degraded recovery to accepted closure
4. one ugly compound blocked-plus-partial-plus-degraded contour back to accepted closure
5. one partial-proof runtime continuation back to accepted closure
6. one degraded-recovery runtime continuation back to accepted closure
7. one doctor-blocked runtime continuation back to accepted closure
8. one machine-readable repair handoff layer plus one ugly compound continuation family through named `resume`
9. one richer repair-packet layer plus one second uglier compound continuation family through named `resume`

That is still bounded, but it is already materially stronger than one or two repaired contours.

It shows the kernel is not only a reject or downgrade engine.

## 1. Blocked readiness to accepted closure

Current readable path:

- blocked starting surface:
  - `fixtures/executable_loop_blocked_run_001/run.json`
- repaired re-entry surface:
  - `fixtures/executable_loop_reentry_run_001/run.json`

Readable transition:

- `TARGET_SURFACE_ATTESTED`
- `CLAIMED_NOT_ACCEPTED`
- `EXACT_TASK_IDENTITY_NOT_CONFIRMED`
- restore exact-task identity
- `READY`
- `EXECUTION_COMPLETED`
- `PROOF_BUNDLE_COMPLETE`
- `CLOSURE_ACCEPTED`

What this proves:

- a blocked readiness contour is not automatically terminal
- the kernel can accept a repaired run without pretending the original blocked attempt was fine
- the reverse edge now exists as a canonical machine-readable repo surface

Why this matters:

- it strengthens `Synrail` as a closure-guidance system, not only a denial system
- it gives the repo one explicit repaired contour, not only accepted, partial, degraded, and blocked end states

## 2. Partial proof to accepted closure

Current readable path:

- partial starting surface:
  - `fixtures/executable_loop_run_002/run.json`
- repaired re-entry surface:
  - `fixtures/executable_loop_partial_reentry_run_001/run.json`

Readable transition:

- `PROOF_BUNDLE_PARTIAL`
- `CLAIMED_NOT_ACCEPTED`
- complete `readback`
- complete `scenario_proof`
- `PROOF_BUNDLE_COMPLETE`
- `CLOSURE_ACCEPTED`

What this proves:

- a partial proof lane is not automatically terminal
- the kernel can accept a repaired run after the missing proof sections are actually supplied
- proof completion now exists as a canonical machine-readable repo surface

Why this matters:

- it strengthens `Synrail` as a closure-completion system, not only a stop-or-degrade system
- it gives the repo one explicit repaired proof contour, not only a recommendation to gather more evidence
- it now also has one named runtime continuation counterpart:
  - `fixtures/executable_loop_runtime_resume_run_001/run.json`

## 3. Degraded recovery to accepted closure

Current readable path:

- degraded starting surface:
  - `fixtures/executable_loop_run_001/run.json`
- repaired re-entry surface:
  - `fixtures/executable_loop_degraded_reentry_run_001/run.json`

Readable transition:

- `RECOVERY_PENDING`
- `CLAIMED_NOT_ACCEPTED`
- complete recovery reverification
- `PROOF_BUNDLE_COMPLETE`
- `CLOSURE_ACCEPTED`

What this proves:

- a degraded recovery lane is not automatically terminal
- the refresh layer can reconcile a repaired recovery surface back into accepted closure
- recovery completion now exists as a canonical machine-readable repo surface

Why this matters:

- it strengthens `Synrail` as a recovery-completion system, not only an invalidation system
- it gives the repo one explicit repaired degraded contour, not only a warning that reverification is still missing
- it now also has one named runtime continuation counterpart:
  - `fixtures/executable_loop_runtime_resume_run_002/run.json`

## 4. Compound repair to accepted closure

Current readable path:

- compound starting surface:
  - `fixtures/executable_loop_compound_run_001/stage1_run.json`
- compound middle surface:
  - `fixtures/executable_loop_compound_run_001/stage2_run.json`
- repaired compound surface:
  - `fixtures/executable_loop_compound_run_001/run.json`

Readable transition:

- `DOCTOR_BLOCKED`
- repair exact prompt identity
- `PROOF_BUNDLE_PARTIAL`
- retain `RECOVERY_PENDING` in the same compound contour
- repair missing proof sections
- complete recovery reverification
- `CLOSURE_ACCEPTED`

What this proves:

- the kernel can now hold one ugly compound repair family rather than only one-step reverse edges
- readiness repair, proof repair, and recovery repair can now coexist in one canonical repo surface
- the current primary run artifact shape still works under compound re-entry

Why this matters:

- it reduces the gap between clean repair families and messier real execution
- it makes the re-entry lattice less ceremonial and more pressure-tested
- it now also has one named runtime continuation counterpart:
  - `fixtures/executable_loop_compound_continuation_run_001/run.json`

## 5. Packet-driven compound continuation to accepted closure

Current readable path:

- packet-blocked starting surface:
  - `fixtures/repair_packet_run_001/run.json`
- packet-driven compound surface:
  - `fixtures/executable_loop_compound_continuation_run_002/run.json`

Readable transition:

- `DOCTOR_BLOCKED`
- blocked packet at `repair_handoff`
- repair prompt/task identity
- `PROOF_BUNDLE_INVALID`
- repair `final_result`, `readback`, and `scenario_proof`
- `RECOVERY_PENDING`
- complete recovery reverification
- `CLOSURE_ACCEPTED`

What this proves:

- the richer repair packet now carries more than one raw continuation flag set
- named `resume` can now move from a blocked packet, through invalid proof, through degraded recovery, into accepted closure
- continuation planning for refresh now lives inside the packet rather than only in operator restatement

Why this matters:

- it reduces continuation fragility
- it makes compound continuation more product-real and less like a one-off stitched replay

## 6. Doctor-blocked runtime continuation to accepted closure

Current readable path:

- doctor-blocked starting surface:
  - `fixtures/executable_loop_runtime_resume_run_003/starting_state.json`
- runtime continuation surface:
  - `fixtures/executable_loop_runtime_resume_run_003/run.json`

Readable transition:

- `DOCTOR_BLOCKED`
- repair prompt/task identity
- rerun doctor readiness
- `READY`
- `EXECUTION_COMPLETED`
- `PROOF_BUNDLE_COMPLETE`
- `CLOSURE_ACCEPTED`

What this proves:

- the named runtime `resume` path is no longer limited to proof or recovery repair
- the kernel can continue from an early readiness-failure state through the same primary artifact surface
- doctor-blocked continuation now exists as a canonical machine-readable runtime family

Why this matters:

- it makes runtime continuation more product-real and less tied only to later-stage repairs
- it reduces the gap between canonical repaired evidence and explicit operator/runtime behavior

## What the re-entry lattice now supports

The current re-entry lattice supports a stronger kernel-level claim:

- `Synrail` can now hold:
  - one explicit reverse edge from a blocked readiness state back to accepted closure
  - one explicit reverse edge from a partial proof state back to accepted closure
  - one explicit reverse edge from a degraded recovery state back to accepted closure
  - one explicit compound repair family that crosses blocked, partial, and degraded contours on the way back to accepted closure
  - one packet-driven compound continuation family that crosses blocked, invalid, degraded, and accepted contours on the way back to honest closure

That is stronger than saying only:

- the kernel can stop
- the kernel can degrade
- the kernel can accept

because it shows the kernel can sometimes recover honestly after a prior block.

## What is still weaker than it should be

The re-entry lattice still has visible gaps:

- the current canonical reverse edges now cover readiness repair, proof completion, one recovery repair, and one ugly mixed family, but not the full set of future compound families
- named runtime `resume` now exists for partial-proof, degraded-recovery, and doctor-blocked continuation, and repair handoff plus repair packet now name the continuation contract more honestly, but packet synthesis is still narrower than a mature continuation surface should be
- hybrid compound repair is still much weaker than it should be

## How this relates to other readings

This document does not replace:

- `OUTCOME_LATTICE_001.md`
- `TRANSITION_LATTICE_001.md`

Because:

- `OUTCOME_LATTICE_001.md` is about stable outcome classes
- `TRANSITION_LATTICE_001.md` is about the broader forward and downgrade edges the kernel already holds
- this document is specifically about reverse movement back toward greener states

## Why this matters

With this re-entry lattice, the repo can now describe the executable kernel in four complementary ways:

1. wedge/value
2. outcome classes
3. transitions and degradations
4. reverse edges back toward acceptance

That is a healthier internal product surface than treating repair only as something implied by prose or ad hoc operator behavior.

## Decision rule

The next strongest kernel work should improve one of these:

1. add one repair-handoff layer that tells the operator exactly which inputs are needed for continuation
2. make the next ugly continuation contour run through that named runtime path instead of only through the broader orchestration surface
3. reduce ambiguity between “repairable blocked”, “repairable partial”, “repairable degraded”, and “still not re-enterable” states
4. strengthen the economics reading around compound re-entry rather than only its state semantics

If a change does not strengthen one of those, it is probably not the best next move for the executable kernel right now.
