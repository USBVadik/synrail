# Sanitized Application Policy Examples

This example shows how the current `Synrail` policy chooses between:

- full governed path
- lightweight baseline
- hybrid subset

The examples are intentionally small and generic.

## Example 1: Full governed path

Scenario:

- a narrow remote bugfix
- the active runtime surface is ambiguous
- the agent reports success confidently
- wrong closure would be expensive

Reading:

- false-success risk is high
- surface ambiguity is real
- artifact truth is nontrivial
- recovery from a wrong “done” would be costly

Decision:

- use the full governed path

Why:

- this is the kind of work where `Synrail` currently earns its cost

## Example 2: Lightweight baseline

Scenario:

- a small honesty-restoration fix
- the repair is a local fallback message
- the active code path is easy to inspect
- operator validation is cheap

Reading:

- false-success risk is low to moderate
- surface ambiguity is low
- artifact truth is easy to inspect
- wrong closure would be annoying, but not expensive

Decision:

- use the lightweight baseline

Why:

- this is the kind of case where the full governed path is likely overkill

## Example 3: Hybrid subset

Scenario:

- a small fix with some ambiguity
- the operator is not fully sure which active path is involved
- a wrong answer would waste time, but not create a severe closure failure

Reading:

- baseline feels too loose
- full governed path feels too expensive

Decision:

- use the hybrid subset

Suggested hybrid move:

1. restate one bounded task
2. verify one active artifact or active path
3. apply one bounded change
4. perform one explicit sanity check
5. stop if confidence is still weak

Why:

- this keeps some truth discipline without paying full `Synrail` cost

## Takeaway

The point is not to use the heaviest path by default.

The point is to match the truth discipline to the cost of being wrong.
