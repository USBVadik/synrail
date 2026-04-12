# Synrail Roadmap

This roadmap is intentionally short-horizon.

`Synrail` has now crossed the line from extraction shell into a small executable control system. That changes the next job.

The repo no longer needs another growth tranche. It needs a pressure-testing tranche.

## Current phase

Current phase:

- pressure-test whether the current kernel is actually worth its extra control cost

That means the near-term work is now mostly about:

- comparator economics instead of comparison prose
- ugly compound reality instead of only clean family examples
- proving or demoting the hybrid mode quickly
- measuring the cost of `Synrail` itself
- sharpening doctor only where it reduces expensive false-readiness decisions

## Near-term priorities

### 1. Make comparator economics central

Goal:

- stop treating comparison as a descriptive sidecar and turn it into a product discipline

Examples:

- add machine-readable economics fields to comparison records
- compare operator minutes, interventions, repair cycles, invalidations, and closure latency
- keep verdicts tied to both proof value and control cost

### 2. Run one ugly compound scenario end-to-end

Goal:

- test the kernel under messy reality rather than only bounded clean examples

Examples:

- start from blocked readiness
- repair readiness honestly
- hit partial proof or degraded confidence
- repair again and return to accepted closure only if the proof basis really supports it

### 3. Prove or demote the hybrid mode quickly

Goal:

- avoid letting the middle mode become policy soup

Examples:

- run two or three stronger hybrid cases soon
- if the signal remains weak, keep hybrid explicitly provisional rather than expanding its semantics

Current measured status:

- hybrid is now `DEMOTED`
- hybrid now has one `SYNRAIL_BETTER`, one `UNCLEAR`, and one `BASELINE_GOOD_ENOUGH` case
- hybrid should now be treated as an explicit exception pattern rather than a default middle lane

### 4. Instrument the cost of Synrail itself

Goal:

- see where the kernel earns its weight and where it may be too expensive

Examples:

- record where invalidations happen most often
- record where operator thought tax is highest
- record how costly repaired re-entry is in human steps or minutes

Current pressure-tested slice:

- one cost-aware mode selector now exists so obvious non-winning paths can be steered back to baseline before entering a heavier contour

### 5. Sharpen doctor on expensive false-readiness modes

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
