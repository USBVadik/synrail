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
2. agent leaves the proof artifacts requested for the run
3. `synrail check`
4. if non-green: `synrail repair-step`
5. if repairable: `synrail retry`
6. if safer to return: `synrail restore`
7. if feedback is needed: `synrail telemetry export`

## Why it could matter

`Synrail` is useful only if it creates real leverage in cases where:

- false green is expensive
- verified working state matters
- non-green repair loops need to stay bounded
- a second operator may need to take over

## What is already real

- proof/closure separation
- acceptance criteria with explicit validation
- measured doctor coverage gate
- executable continuation arbiter
- truth-critical regression suite
- one cheap first-run alpha pack

## Current honest weaknesses

- semantic proof is still narrow, not domain-complete
- measured doctor coverage is still corpus-bounded
- continuation arbitration is stronger, but still scoped
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
