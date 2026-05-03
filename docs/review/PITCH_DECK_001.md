# Pitch Deck 001

This is a deck-style summary for live conversation.

## Slide 1 — Title

Synrail

Proof-first control for reliable agent execution.

## Slide 2 — The problem

Agent workflows fail in a predictable way:

- the agent claims success
- the operator sees a plausible narrative
- the system accepts too early
- failure is discovered later, after drift and confusion

## Slide 3 — The thesis

Claimed done is not accepted done.

`Synrail` treats:

- doctor readiness
- proof quality
- closure acceptance
- restore/continuation

as explicit runtime truth surfaces.

## Slide 4 — The wedge

We are not trying to replace every workflow tool.

The wedge is narrower:

- stop false success
- preserve verified working state
- make non-green next steps explicit
- make continuation less dependent on author memory

## Slide 5 — What the product is today

Today it is:

- one proof-governed kernel
- one thin controlled-start alpha shell
- one first real workflow
- one external tester pack

Not a platform.
Not a broad shell.
Not a hosted service.

## Slide 6 — How it works

Current support boundary:

- supported: one local trusted worktree on the same machine where the agent acts
- not yet supported: remote host / ops / production-target execution as a first-class alpha lane

Current contour:

1. `synrail start`
2. strengthen `final_result.json` first and keep `readback.txt` plus `scenario_proof.txt` fallback-only unless `synrail check` later names one
3. `synrail check`
4. if the change touches rendered UI, a page template, or a server-side route handler and you want lightweight local runtime evidence: `synrail runtime-helper`
5. if non-green: fix only the named gap and rerun `synrail check`; when refresh invalidation is known, the default summary now points only at the stale obligation class
6. use `synrail repair-step` only if a standalone bounded repair prompt is actually helpful
7. if restore point exists and returning is safer: `synrail restore --preview`, then `synrail restore` if it is still the right move
8. if needed: `synrail telemetry export` or `synrail bug-packet`

## Slide 7 — Core architecture

Kernel layers:

- spine state machine
- doctor gate
- proof bundle
- closure
- acceptance criteria
- continuation packet + arbiter
- observability / telemetry export

## Slide 8 — Evidence that this is real

We now have:

- explicit acceptance criteria and validation
- measured doctor coverage gate
- executable continuation arbiter
- truth-critical regression suite
- tester-pack smoke
- canonical external tester-pack fixture
- claim-validation pack for second-operator followability and evidence ownership discipline
- refresh-driven stale-obligation guidance in thin output

## Slide 9 — Why this could matter

Compared with simpler baseline flows, `Synrail` can create value when:

- false green is expensive
- restore needs to be fast and honest
- second-operator handoff matters
- bounded repair loops matter more than happy-path demos

## Slide 10 — Honest weaknesses

Still weak / still narrow:

- semantic proof is not domain-complete
- measured doctor coverage is corpus-bounded
- continuation arbitration is still scoped to selected conflict surfaces
- shell still has some operator tax
- outside alpha signal is still more important than more local polish

## Slide 11 — What we want from critique

We want external reviewers to tell us:

- where truth rigor is still fake
- where the shell still feels ritualistic
- whether the wedge is actually strong enough
- what should be cut before any broader expansion

## Slide 12 — The ask

Do not ask whether this could become a platform.

Ask instead:

- is the kernel meaningfully stronger than baseline on its wedge?
- does the current alpha lane earn expansion?
- what should we freeze, cut, or harden before broader alpha?
