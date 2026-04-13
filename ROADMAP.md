# Synrail Roadmap

This roadmap is intentionally short-horizon.

`Synrail` has now crossed the line from extraction shell into a small executable control system. That changes the next job.

The repo no longer needs another growth tranche. It needs a product-tightening tranche that stays pressure-tested.

## Current phase

Current phase:

- harden the current kernel into a more usable product contour while keeping cost and evidence pressure on it

That means the near-term work is now mostly about:

- first-class continuation and re-entry instead of manual repaired replay
- stronger runtime handoff between policy, selection, and execution
- comparator economics as a guardrail instead of a sidecar
- measuring the cost of `Synrail` itself where it changes product choices
- sharpening doctor only where it reduces expensive false-readiness decisions

## Near-term priorities

### 1. Make comparator economics central

Goal:

- stop treating comparison as a descriptive sidecar and turn it into a product discipline

Examples:

- add machine-readable economics fields to comparison records
- compare operator minutes, interventions, repair cycles, invalidations, and closure latency
- keep verdicts tied to both proof value and control cost

Current status:

- enough economics now exists to guide product decisions
- the next strongest moves should spend that signal on runtime/product tightening rather than grow economics for its own sake

### 2. Make continuation first-class

Goal:

- stop treating repaired re-entry as mostly canonical evidence and turn it into explicit operator/runtime behavior

Examples:

- add named runtime continuation entrypoints
- carry continuation truth in the same primary run artifacts
- reduce operator stitching from blocked, partial, and degraded states

Current status:

- named runtime continuation now exists for:
  - `PROOF_BUNDLE_PARTIAL`
  - `RECOVERY_PENDING`
  - `DOCTOR_BLOCKED`
- repair handoff now exists as one machine-readable continuation contract that can name missing inputs and bounded runtime defaults
- named `resume` can now consume that handoff directly and stop at `repair_handoff` when the continuation contract is still incomplete
- one richer repair packet now exists above that handoff, and the runtime can now auto-synthesize it from current truth so continuation can carry context, plan, repair inputs, and runtime output defaults in one machine-readable bundle
- packet-first continuation is now the default operator path around `resume`
- one uglier packet-driven compound continuation path now exists through staged packets plus named `resume`
- one third uglier packet-first continuation path now also exists through selection/preparation handoff, runtime-owned packets, invalid proof, degraded recovery, and accepted closure
- one fourth uglier packet-first continuation path now also exists through selection/preparation handoff, repair-handoff blocking, recovery repair, and one explicit terminal not-resumable finish
- the next strongest move is no longer basic packet synthesis; it is turning the richer packet and packet-first `resume` into the cleanest default continuation contract the runtime has

### 3. Run one ugly compound scenario end-to-end

Goal:

- test the kernel under messy reality rather than only bounded clean examples

Examples:

- start from blocked readiness
- repair readiness honestly
- hit partial proof or degraded confidence
- repair again and return to accepted closure only if the proof basis really supports it

### 4. Prove or demote the hybrid mode quickly

Goal:

- avoid letting the middle mode become policy soup

Examples:

- run two or three stronger hybrid cases soon
- if the signal remains weak, keep hybrid explicitly provisional rather than expanding its semantics

Current measured status:

- hybrid is now `DEMOTED`
- hybrid now has one `SYNRAIL_BETTER`, one `UNCLEAR`, and one `BASELINE_GOOD_ENOUGH` case
- hybrid should now be treated as an explicit exception pattern rather than a default middle lane

### 5. Instrument the cost of Synrail itself

Goal:

- see where the kernel earns its weight and where it may be too expensive

Examples:

- record where invalidations happen most often
- record where operator thought tax is highest
- record how costly repaired re-entry is in human steps or minutes

Current pressure-tested slice:

- one cost-aware mode selector now exists so obvious non-winning paths can be steered back to baseline before entering a heavier contour

### 7. Strengthen packet-first continuation truth

Goal:

- make continuation more runtime-owned and less dependent on operator reconstruction

Current pressure-tested slice:

- repair packets now carry explicit artifact-quality hints in addition to missing-input truth
- repair packets now carry narrower stale sub-surface hints inside those artifacts
- repair packets now also carry repair-receipt context so runtime continuation can see which repair step actually completed and which stale sub-surfaces remain after that step
- three truly not-resumable continuation families now exist:
  - selection-blocked
  - terminal accepted
  - terminal rejected
- one fresh forward-orchestration non-resumable family now also exists:
  - `NOT_RESUMABLE_FRESH_ORCHESTRATION`
- one lower-replay packet-first continuation run now proves that sibling auto-discovery can drive `resume` back to accepted closure with much less raw flag replay
- one minimal-continuation-core run now proves that packet-first `resume` can return from `DOCTOR_BLOCKED` to accepted closure from only `state + repair_packet`
- one uglier packet-first continuation run now proves explicit repair order, stale-artifact hints, mid-continuation doctor failure, and return to accepted closure
- one further packet-first continuation run now proves that repair receipts, explicit step progression, blocked recovery completion, and final truthful terminal packet emission can all live on the same runtime surface
- one next packet-first continuation run now proves that recovery completion supply, doctor target-identity pressure, richer repair receipts, and accepted closure can all live on the same runtime surface with stage-aware sibling discovery
- repair receipts now also carry one packet-native repair-history chain across multiple continuation stages instead of only one last-step marker
- packet-first `resume` now trusts embedded packet truth strongly enough that normal continuation no longer depends on temporary unpacked selection or repair-handoff side files
- one further uglier packet-first continuation run now proves that doctor target-identity pressure, partial proof pressure, recovery pressure, and accepted closure can all live on one ordered repair chain
- one tenth uglier packet-first continuation run now proves that repeated doctor pressure can survive packet-chained minimal-core continuation and still return to accepted closure
- one continuation-adoption delta now proves that this compressed continuation contour reduced visible root side-file tax without losing repeated doctor pressure or accepted terminal truth

Next likely strengthening moves:

- sharpen artifact-quality hints so they name even more precise stale sub-surfaces inside larger artifacts
- pressure-test more non-resumable families beyond lighter-mode selection and terminal acceptance or rejection
- keep compressing packet-first `resume` so more continuation truth stays inside runtime-owned packet surfaces rather than adjacent side files
- keep validating the minimal lovable continuation core so continuation does not expand faster than its real operator value

### 6. Sharpen doctor on expensive false-readiness modes

Goal:

- make doctor smaller-but-truer rather than broader-but-ceremonial

Examples:

- reduce wrong-target assumptions
- reduce false clean-surface confidence
- reduce exact prompt or task identity mismatch on exact runs

Current pressure-tested slice:

- doctor now catches one path-validity false-green on credential envs
- doctor now catches one exact artifact mismatch case, not only missing exact artifacts
- doctor now also catches one wrong-target-surface mismatch before execution starts

## Current reading

The repo has already earned several things:

- a narrow wedge for expensive-to-be-wrong closure work
- a bounded executable kernel with machine-readable state, gates, closure, refresh, and re-entry
- canonical accepted, blocked, degraded, and repaired surfaces

The next pressure now belongs on:

- value proof
- cost truth
- compound repair truth
- explicit hybrid secondary status until stronger evidence exists

not on:

- new explanatory layers
- broad orchestration growth
- public packaging

## Explicitly not current priorities

These may matter later, but they are not the current focus:

- new lattice or meta readings without runtime or economic payload
- broader CLI surface as a substitute for uglier runtime proof
- richer family expansion for completeness alone
- expanding hybrid semantics before evidence improves
- full UI or dashboard work
- downstream agent capability logic
- broad repo polish for its own sake

## Decision rule

If a proposed change makes the repo:

- better at measuring whether extra control is worth it
- stronger under ugly compound reality
- more honest about hybrid-mode confidence
- clearer about the cost of the kernel itself
- stricter on expensive false-readiness decisions

it is likely on-roadmap.

If it mostly adds breadth, explanation, or polish without new runtime or economic truth, it is probably off-roadmap for this phase.

## Active review anchor

The smallest current anchor set is now:

- `docs/boundary/EXECUTABLE_STACK_READING_001.md`
- `docs/boundary/TRIO_READING_001.md`
- `docs/boundary/OUTCOME_LATTICE_001.md`
- `docs/boundary/TRANSITION_LATTICE_001.md`
- `docs/boundary/REENTRY_LATTICE_001.md`
- `docs/core/BASELINE_HARNESS_001.md`

Everything else should support this set rather than compete with it for attention.

The next practical operating layer around that anchor is:

- `docs/boundary/APPLICATION_POLICY_001.md`
- `docs/boundary/HYBRID_SUBSET_001.md`
- `docs/boundary/HYBRID_STATUS_001.md`

Current continuation-pressure work should keep optimizing for:

- repair-history truth that survives across multi-step packet-first continuation
- uglier continuation families where doctor pressure can return after intermediate repair
- continuation compression that removes side artifacts when packet truth already carries enough state

The next product-proof layer should now prefer:

- substitute-kill tests against concrete simpler stacks instead of only abstract baseline comparison
- finding where Synrail is materially necessary against real substitutes and where it is still only internally convincing
