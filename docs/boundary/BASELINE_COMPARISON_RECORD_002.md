# Baseline Comparison Record 002

## Scenario identity

- scenario: narrow honesty-restoration incident with a truthful fallback replacing an overclaimed capability
- narrow task class: bounded production incident / honesty-restoration guard
- why this scenario was selected:
  - it is meaningfully less favorable to `Synrail` than the exact-task killer path
  - it tests whether the kernel still earns its cost when the repair is small and the baseline is more plausible

## Baseline replay

- baseline shape:
  - one bounded incident report
  - one targeted code inspection
  - one small patch or fallback guard
  - one manual runtime check
- baseline likely outcome:
  - probably acceptable
- baseline likely blocker-to-closure cycle count:
  - likely low
- baseline likely false-success risk:
  - moderate rather than high
- baseline likely recovery cost:
  - likely low to medium
- baseline likely operator confusion:
  - likely manageable

## Synrail path

- governed path used:
  - bounded incident intake
  - target-surface attestation
  - active-path verification
  - disciplined fallback repair
  - external runtime confirmation
- Synrail outcome:
  - truthful behavior restored
  - overclaimed capability stopped
- Synrail blocker-to-closure cycle count:
  - higher than the simpler baseline would likely require
- Synrail false-success exposure:
  - lower
- Synrail recovery cost:
  - front-loaded and well-governed
- Synrail operator confusion:
  - lower at review time
- Synrail overhead introduced:
  - moderate to high relative to the smallness of the repair

## Metric comparison

### 1. Blocker-to-closure cycle count

- baseline:
  - likely lower
- Synrail:
  - higher
- reading:
  - baseline likely wins on speed

### 2. False-success rate

- baseline:
  - probably acceptable if the operator is already disciplined
- Synrail:
  - lower
- reading:
  - `Synrail` still helps, but the margin is smaller than on the killer path

### 3. Proof completeness at decision time

- baseline:
  - lighter, but probably adequate for this scenario
- Synrail:
  - stronger
- reading:
  - `Synrail` wins, though perhaps by more than the scenario strictly needs

### 4. Recovery cost after misleading output

- baseline:
  - not obviously dangerous on this scenario
- Synrail:
  - more explicit and cleaner
- reading:
  - slight edge to `Synrail`, but not decisive

### 5. Coordination overhead

- baseline:
  - clearly lower
- Synrail:
  - clearly higher
- reading:
  - this cuts against `Synrail` much more strongly here than in Record 001

## Honest verdict

- verdict:
  - `baseline good enough`

## Why

- this scenario is important, but it is not the place where `Synrail` most clearly earns its full cost
- the simpler baseline could likely have restored honesty with less ceremony and acceptable risk
- `Synrail` still looks cleaner and more rigorous, but that advantage does not appear strong enough here to justify treating the full governed path as mandatory

## What this changes

- `Synrail` now has a second comparison reading on a less favorable scenario
- the product claim becomes more honest:
  - `Synrail` is strongest where false completion and proof ambiguity are expensive
  - it is less obviously worth its cost on small honesty-restoration incidents
- this strengthens the case for keeping the core narrow and not expanding the governed path everywhere

## What this does not prove

- it does not prove the baseline is better on the killer path
- it does not disprove `Synrail` value
- it only shows that the wedge is narrower than “better process everywhere”
