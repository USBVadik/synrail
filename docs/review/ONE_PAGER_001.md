# One Pager 001

## What Synrail is

`Synrail` is a narrow proof-first control product for coding-agent workflows.

Its core claim is:

- claimed done is not accepted done

## The problem

In many real agent loops, the weak default is:

1. the agent says it is done
2. the result sounds plausible
3. the operator accepts too early
4. failure is discovered later, after drift, confusion, or bad handoff

That creates four recurring pains:

- false green
- unclear non-green next step
- slow or unreliable restore
- too much dependence on author memory

## The wedge

`Synrail` is not trying to be:

- a platform
- a workflow engine
- a hosted telemetry product
- a broad orchestration shell

The wedge is narrower:

- block false success
- preserve one verified fallback
- make non-green next steps bounded
- make restore and re-entry cheaper and more honest

## What the product does today

Current support boundary:

- supported: one local trusted worktree on the same machine where the agent acts
- not yet supported: remote host / ops / production-target execution as a first-class alpha lane

Current alpha lane:

1. `synrail start`
2. strengthen `.synrail/final_result.json` first and keep `.synrail/readback.txt` plus `.synrail/scenario_proof.txt` fallback-only unless `synrail check` later names one
3. `synrail check`
4. if you need a small UI/runtime verification path for a rendered or route-facing change: `synrail runtime-helper`
5. if non-green: fix only the named gap and rerun `synrail check`; when refresh invalidation is known, the default summary now points only at the stale obligation class
6. if a standalone bounded repair prompt helps: `synrail repair-step`
7. if safer to return: `synrail restore --preview`, then `synrail restore` if it is still the right move
8. if feedback is needed: `synrail telemetry export` or `synrail bug-packet`

## Why it could matter

`Synrail` is useful only if it creates real leverage in cases where:

- false green is expensive
- verified working state matters
- non-green repair loops need to stay bounded
- a second operator may need to take over

## What is already real

- proof/closure separation
- acceptance criteria with explicit validation plus allowlisted verification recheck on the recorded local commands
- measured doctor coverage gate
- executable continuation arbiter
- path-trust-hardened restore preview and restore flow on the current narrow local matrix
- truth-critical regression suite
- one cheap first-run alpha pack plus claim-validation pack for second-operator followability and evidence ownership discipline

## Current honest weaknesses

- semantic proof is still narrow, not domain-complete
- measured doctor coverage is still corpus-bounded
- continuation arbitration is stronger, but still scoped
- the strongest everyday-economics signal is still the focused `small_template_text_fix` family; the broader everyday lane remains baseline-favorable overall
- shell cost is much lower now, but still must earn itself outside

## What we want from critics

We do not want “this is interesting.”

We want:

1. where is truth rigor still fake?
2. what still feels ceremonial?
3. where does the shell overclaim?
4. what part of the wedge is actually strong?
5. what should be cut before any broader alpha?

## Best starting points

- [ALPHA_TEST_PACK_001.md](../core/ALPHA_TEST_PACK_001.md)
- [EXTERNAL_CRITIQUE_PACK_001.md](./EXTERNAL_CRITIQUE_PACK_001.md)
- [KNOWN_WEAKNESSES_001.md](./KNOWN_WEAKNESSES_001.md)
