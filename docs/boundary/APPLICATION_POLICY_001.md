# Application Policy 001

## Purpose

Define when to use the full `Synrail` governed path, when to use a lighter baseline, and when to use a hybrid subset.

This document exists so the wedge becomes operational policy rather than staying only a descriptive insight.

The first machine-readable selector surface for that policy now lives at:

- `fixtures/mode_recommendation_strong_001.json`
- `fixtures/mode_recommendation_weak_001.json`
- `fixtures/mode_recommendation_hybrid_001.json`

## Three modes

Current application policy now has:

1. two active default modes
2. one demoted exception pattern

## 1. Full governed path

Use the full governed path when the work has one or more of these properties:

- high false-success risk
- meaningful closure cost if accepted wrongly
- remote or ambiguous execution surface
- nontrivial artifact/proof ambiguity
- meaningful recovery cost after misleading output

Typical fit:

- narrow exact-task bugfixes
- controlled patch tasks
- messy execution paths where narrative confidence is not safe enough

Expected cost:

- highest coordination overhead

Expected value:

- highest truth discipline
- strongest reviewable closure

## 2. Lightweight baseline

Use the lightweight baseline when the work looks like this:

- small local repair
- low false-success risk
- cheap operator validation
- low consequence if the first answer is wrong
- little or no execution-surface ambiguity

Typical fit:

- small honesty-restoration incidents
- simple bounded fixes
- cases where one disciplined operator loop is already adequate

Expected cost:

- lowest coordination overhead

Expected value:

- fast and usually good enough

## 3. Hybrid subset

Use a hybrid subset when the full governed path is too expensive, but a pure lightweight baseline feels too loose.

Current status:

- `DEMOTED`
- `exception rather than default`

Suggested hybrid elements:

- clearer task identity
- one explicit artifact sanity check
- explicit stop instead of bluffing when confidence is weak

Typical fit:

- medium-risk incidents
- small fixes with some ambiguity
- cases where you want some truth discipline without paying full kernel cost

Expected cost:

- middle

Expected value:

- better than the lightweight baseline on ambiguity
- cheaper than the full governed path

Current policy constraint:

- do not auto-select hybrid just because the answers feel mixed
- keep baseline as the default unless one explicit ambiguity justifies extra control
- do not describe hybrid as a standing third policy lane

## Quick decision rule

Ask these questions in order:

1. would a wrong “done” be expensive?
2. is the execution surface ambiguous?
3. is artifact truth nontrivial to inspect?
4. would recovery from misleading output be costly?

If the answer is “yes” to one or more of those in a meaningful way:

- prefer the full governed path

If the answers are mostly “no”:

- prefer the lightweight baseline

If the answers are mixed:

- prefer the lightweight baseline unless you can name one explicit ambiguity the baseline would leave too loose
- only then reach for the hybrid subset

## Anti-misuse rule

Do not use the full governed path just because `Synrail` exists.

Do not avoid it just because it is heavier.

Do not let hybrid become a vague “middle by default”.

Choose the path whose truth economics match the scenario.

## Current policy reading

Current evidence suggests:

- full governed path is justified on the killer path
- lightweight baseline is often good enough on small honesty-restoration incidents
- hybrid subset now has one stronger measured win and one `BASELINE_GOOD_ENOUGH` medium-risk case, so it should be treated as a demoted exception pattern rather than a default mode

## Decision rule

Future product work should improve one of these:

- the effectiveness of the full governed path on its real wedge
- the clarity of when to stay lightweight
- the usefulness of the hybrid subset

If a change does not improve one of those, it is probably not current-priority policy work.
