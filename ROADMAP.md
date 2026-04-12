# Synrail Roadmap

This roadmap is intentionally short-horizon.

`Synrail` has only recently been extracted into its own repository, so the next moves should strengthen identity and usability before expanding scope.

## Current phase

Current phase:

- prove one killer path clearly enough that the extracted repo earns its weight

That means the near-term work is mostly about:

- one narrow adoption loop
- measurable advantage over a simpler baseline
- shrinking toward the minimum undeniable core
- keeping structure in service of proof rather than polish

## Near-term priorities

### 1. Prove the killer path

Goal:

- make one `Synrail` path compelling enough to justify the kernel

Examples:

- keep focus on closure-grade exact-task work
- optimize for truthful closure, not broad feature breadth
- reject work that does not strengthen the main adoption loop

### 2. Compare against a simpler baseline

Goal:

- test whether `Synrail` really beats a disciplined lightweight operator loop

Examples:

- compare blocker-to-closure cycle count
- compare false-success rate
- compare recovery cost after misleading agent output
- run one compact head-to-head comparison before claiming product advantage

### 3. Shrink toward the minimum undeniable core

Goal:

- keep only the pieces that truly carry the killer path

Examples:

- preserve attestation
- preserve exact-task identity
- preserve artifact/proof-bundle truth
- demote anything that is only explanatory polish

### 4. Keep the boundary clean

Goal:

- prevent downstream capability work from slipping into the kernel repo

Examples:

- reject changes that mainly belong to one downstream bot
- reject changes that mainly describe one proving-ground environment
- keep adapter references generic where possible

### 5. Keep repo polish subordinate to proof

Goal:

- avoid mistaking clean structure for product proof

Examples:

- do small repo-native improvements only when they support reviewability
- do not use docs growth as substitute for value proof
- keep shell cleanliness in service of the killer path

Current reading:

- the private-stable target is now defined and reached
- a first repeatability signal now exists for closure-grade exact-task runs
- the next proof/value work should now be organized around the killer path, the simpler baseline, and the minimum undeniable core

## Explicitly not current priorities

These may matter later, but they are not the current focus:

- building a full UI or dashboard
- adding downstream agent capability logic
- importing historical incident archives
- broad packaging or automation layers
- turning reference helpers into a large orchestration product
- broad repo polish for its own sake
- new semantic layers that do not improve closure economics

## Decision rule

If a proposed change makes the repo:

- stronger on the killer path
- easier to compare against baseline
- smaller at the undeniable core
- more faithful to the kernel boundary

it is likely on-roadmap.

If it mostly adds breadth, downstream behavior, battlefield history, or polish-without-proof, it is probably off-roadmap for this phase.

## Active review anchor

The smallest current anchor set is:

- `docs/boundary/EXECUTABLE_STACK_READING_001.md`
- `docs/boundary/KILLER_PATH_001.md`
- `docs/boundary/BASELINE_COMPARISON_RECORD_001.md`
- `docs/boundary/MINIMUM_UNDENIABLE_CORE_001.md`
- `docs/boundary/CORE_COMPRESSION_PASS_001.md`

Everything else should support this set rather than compete with it for attention.

The next practical operating layer around that anchor is:

- `docs/boundary/APPLICATION_POLICY_001.md`
- `docs/boundary/HYBRID_SUBSET_001.md`
