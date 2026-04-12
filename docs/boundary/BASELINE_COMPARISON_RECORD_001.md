# Baseline Comparison Record 001

## Scenario identity

- scenario: narrow exact-task router/trigger bugfix under governed exact-retry conditions
- narrow task class: bounded router/trigger fixes
- why this scenario was selected:
  - it is the strongest current killer-path candidate
  - it already produced repeated closure-grade artifacts
  - it exposed real false-success pressure, surface ambiguity, and recovery cost

## Baseline replay

- baseline shape:
  - one bounded task statement
  - one agent attempt
  - one manual sanity check
  - one retry-or-stop decision
- baseline likely outcome:
  - early ambiguity and meaningful risk of accepting a narrative-only “success”
- baseline likely blocker-to-closure cycle count:
  - apparently low at first, but likely to rise later after recovery from a wrong acceptance
- baseline likely false-success risk:
  - high on this scenario
- baseline likely recovery cost:
  - medium to high once wrong-surface or no-diff reality is discovered after the fact
- baseline likely operator confusion:
  - meaningful, because the same scenario repeatedly produced confident success narrative before reliable artifact truth

## Synrail path

- governed path used:
  - exact-task identity
  - target-surface attestation
  - trusted baseline discipline
  - artifact capture
  - proof-bundle review
  - explicit closure acceptance/rejection
- Synrail outcome:
  - two accepted closure-grade exact-task successes on the same narrow class
- Synrail blocker-to-closure cycle count:
  - high during campaign unblocking, but explicitly visible and truth-preserving
- Synrail false-success exposure:
  - materially reduced, because repeated narrative-only success was rejected
- Synrail recovery cost:
  - front-loaded and explicit rather than deferred into hidden wrong acceptance
- Synrail operator confusion:
  - lower at decision time, even when execution was messy
- Synrail overhead introduced:
  - high
  - attestation, artifact handling, run classification, proof review, and bounded executor repair all added real coordination cost

## Metric comparison

### 1. Blocker-to-closure cycle count

- baseline:
  - likely appears cheaper at first, but with a real chance of hidden later recovery loops
- Synrail:
  - visibly more cycles
- reading:
  - baseline wins on superficial speed; Synrail wins on truthful cycle accounting

### 2. False-success rate

- baseline:
  - likely higher
- Synrail:
  - lower on this scenario
- reading:
  - this is the strongest current advantage for `Synrail`

### 3. Proof completeness at decision time

- baseline:
  - light and operator-dependent
- Synrail:
  - materially stronger
- reading:
  - `Synrail` clearly wins here

### 4. Recovery cost after misleading output

- baseline:
  - likely deferred and more chaotic
- Synrail:
  - higher up front, but cheaper once misleading output appears because rejection rules already exist
- reading:
  - `Synrail` appears better on this scenario

### 5. Coordination overhead

- baseline:
  - clearly lower
- Synrail:
  - clearly higher
- reading:
  - this is the strongest current cost against `Synrail`

## Honest verdict

- verdict:
  - `Synrail better`

## Why

- on this exact killer path, the main product risk was not “too few steps”
- it was false completion and narrative trust under messy execution conditions
- `Synrail` was expensive, but it repeatedly converted that mess into reviewable blocker truth and then into accepted closure-grade artifacts
- the simpler baseline would likely have felt cheaper while still carrying a meaningful chance of accepting the wrong thing or discovering the real state later and more chaotically

## What this changes

- `Synrail` now has a first honest product-comparison reading on its strongest current path
- the repo no longer relies only on internal framing to claim value
- the next compression question becomes sharper:
  - which parts of `Synrail` created this advantage, and which parts were just overhead

## What this does not prove

- it does not prove broad product superiority
- it does not prove low overhead
- it does not prove that `Synrail` beats the simpler baseline on easier or cleaner scenarios
- it only shows that on the current killer path, the extra control appears justified
