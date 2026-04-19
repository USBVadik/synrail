# Synrail Critic Review Brief

Status date: 2026-04-18
Repo: `synrail`
Current branch: `codex/first-extraction-pr`
Current reviewed commit: `c60854f`
Current regression status: `409 tests OK`

## Why this document exists

This brief is meant for an honest external review.
It is not a pitch deck and not a marketing summary.
It is a compressed explanation of:

- what Synrail is trying to solve
- what the current product wedge actually is
- how the system works in code
- what has been pressure-tested already
- what is still weak or unresolved
- what a critic should attack first if they want to falsify the project

If you want one sentence:

**Synrail is a local proof-first control kernel for bounded agent work.**
It tries to stop false-green closure by forcing execution through explicit readiness, proof, repair, and acceptance surfaces instead of narrative trust.

## Current hardening delta since the last outside pass

The current branch has tightened several critic-facing weak spots without broadening product surface area:

- runtime-backed proof now waives optional prose surfaces on the measured trivial lane, and the live agent can already follow that cheaper contour on the best current runs
- evidence ownership is now explicit: harness-only and weak mixed reports are no longer allowed to masquerade as clean kernel roadmap signal
- the newer hostile observation guards are now task-class scoped, so they no longer pretend to be universal policy on unmeasured contours
- the tester-pack now has a companion claim-validation pack that checks both second-operator followability and evidence-ownership discipline

These are real hardening moves, but they do **not** yet change the broad verdict: the wedge is more credible and cleaner than before, while trivial-task economics and broader validation still lag behind baseline.

## The problem Synrail is trying to solve

Local coding agents are increasingly capable, but they have recurring failure modes:

- they can complete work without leaving trustworthy evidence
- they can declare success on weak verification
- they can drift outside the requested scope
- they can repair in loops without converging
- they can leave humans with ambiguous state and no honest next step
- they can mix real changes, guessed claims, and broken environment assumptions into one narrative blob

The core Synrail claim is:

**a claim is not accepted reality until it has passed through explicit, bounded proof and closure rules.**

The system is designed to make the agent say:

- what changed
- how it was checked
- what is still missing
- what the narrowest next safe step is

instead of letting “looks done” act as closure.

## Product concept

Synrail is deliberately not a daemon, not an orchestration platform, and not a giant runtime supervisor.

It is a terminal-first control kernel that governs one bounded local change at a time.

The current product contour is intentionally narrow:

- one trusted local worktree
- one bounded task
- one explicit artifact root: `.synrail/`
- one explicit proof bundle
- one explicit closure decision

That narrowness is intentional.
The project is optimized around a wedge:

- stop false readiness
- stop false proof completion
- stop dishonest acceptance
- keep recovery bounded when the run is non-green

## What Synrail is not

Synrail is not currently:

- a general-purpose agent framework
- a remote-host or production-first execution controller
- a browser automation system
- a broad developer platform
- a long-running daemon
- a replacement for tests, curl, or normal local verification tools

It is also not trying to “understand all software work”.
Its current alpha lane is purposely small and local-first.

## Current supported lane

The currently supported alpha lane is:

- local trusted worktree
- same machine where the agent acts
- bounded change
- explicit proof files under `.synrail/`
- explicit check / repair / retry loop

Important non-goal right now:

- remote target / ops / production-target execution as a first-class alpha lane is **not yet supported**

This is stated in the repo and matters for honest review.
A critic should not assume Synrail is already claiming a broad operational control surface.

## The user-level workflow

At the user level the intended path is intentionally small:

1. `synrail`
2. `synrail start "Describe the bounded change"`
3. do the work
4. fill in the starter proof files in `.synrail/`
5. `synrail check`
6. if blocked: `synrail repair-step`
7. fix only the named gap
8. `synrail retry` or `synrail check`
9. stop only at accepted closure

Starter proof files currently are:

- `.synrail/final_result.json`
- `.synrail/readback.txt`
- `.synrail/scenario_proof.txt`

The UX philosophy is:

- first check is often non-green
- non-green is normal, not failure
- the system should identify a narrow blocker and a narrow next safe step

## Core conceptual model

The kernel currently centers around these layers:

1. Doctor
2. State / Spine
3. Bundle
4. Closure
5. Refresh
6. Continuation / Resume
7. Checkpoint

This exact freeze is documented in:
- `docs/boundary/CORE_SCOPE_001.md`

### 1. Doctor

Doctor is the readiness layer.
It is meant to stop false-green execution states before trust is granted.

Examples of the kinds of things it can block:

- missing readiness evidence
- helper drift
- fixture/corpus gaps
- identity mismatches
- environment states that are not trustworthy enough to justify acceptance

### 2. State / Spine

The state/spine layer is the canonical runtime truth source.
Derived artifacts are allowed, but they are not the root of truth.

The runtime truth surface is meant to answer, compactly:

- what is trusted now
- what is observed now
- what blocker is active now
- whether the next run class is acceptable
- what the next safe step is

See:
- `docs/core/SYNRAIL_RUNTIME_TRUTH_SURFACE.md`

### 3. Bundle

The bundle layer is the core proof assembler.
It decides whether the proof package is:

- structurally complete
- semantically sufficient
- still too thin to trust

This is where Synrail tries to separate “the fields are present” from “the evidence is actually good enough”.

### 4. Closure

Closure is the acceptance decision.
A run should not be accepted because the agent sounds confident.
It should be accepted because the bounded requirements are satisfied under kernel rules.

### 5. Refresh

Refresh exists because accepted truth can become stale.
If later signals invalidate closure assumptions, the system needs an honest re-entry path rather than silently pretending the previous green state still stands.

### 6. Continuation / Resume

This layer tries to prevent ugly repair loops.
It records current bounded repair state and makes the next step followable without hidden author memory.

### 7. Checkpoint

Checkpoint is treated as a verified safe point, not a casual snapshot.
The project treats restore safety as a first-class control issue, not an afterthought.

## Key product idea: proof is an artifact bundle, not a narrative

This is the deepest conceptual choice in Synrail.

Instead of asking the agent for a free-form explanation of what happened, Synrail asks for a proof bundle built from explicit surfaces.

Current primary proof surfaces are:

- final result artifact
- readback artifact
- scenario proof artifact
- doctor artifact
- bundle artifact
- closure artifact

The system is trying to bias the loop away from:

- “I think it works”
- “I changed the file and it looks right”
- “I can explain why it should be fine”

and toward:

- bounded changed surface
- explicit verification evidence
- explicit missing section names
- explicit next safe step

## Agent adoption concept

One major practical insight from recent work is that local agents do not reliably “discover” control systems on their own.
So Synrail now includes repo-native agent adoption files:

- `AGENTS.md`
- `GEMINI.md`
- `CLAUDE.md`

The installer can inject a managed Synrail block so local agents naturally discover:

- `synrail`
- `synrail start`
- work
- `synrail check`

This turned out to matter a lot in practice.
A large amount of recent hardening work was about making Gemini and Claude actually enter the intended contour without special per-prompt coaching.

## Technical implementation

## Packaging and entrypoint

The installable CLI is very small at the package boundary.

Main package entrypoint:
- `setup.py`
- `alpha.py`

Current console script:
- `synrail=alpha:main`

`alpha.py` is intentionally thin and delegates directly to:
- `tools/reference/synrail_cli_v0.py`

That means the real product logic is in the reference CLI layer, not in a heavyweight application framework.

## CLI structure

The main CLI facade is:
- `tools/reference/synrail_cli_v0.py`

This file acts as a terminal-first orchestrator over many smaller modules.
It does not hold all logic inline; instead it dispatches to focused helper modules such as:

- `synrail_bootstrap_v0.py`
- `synrail_bundle_v0.py`
- `synrail_closure_v0.py`
- `synrail_refresh_v0.py`
- `synrail_doctor_v1.py`
- `synrail_repair_packet_v0.py`
- `synrail_repair_handoff_v0.py`
- `synrail_repair_prompt_bridge_v0.py`
- `synrail_thin_output_v0.py`
- `synrail_checkpoint_v0.py`
- `synrail_artifact_consistency_v0.py`
- `synrail_observability_v0.py`

This is not a plugin ecosystem yet.
It is closer to a kernel assembled from a large number of small, single-purpose reference modules.

## Artifact model

The canonical artifact root is `.synrail/`.

Representative artifacts include:

- `state.json`
- `project_profile.json`
- `bootstrap.json`
- `proof_request.json`
- `acceptance_criteria.json`
- `doctor.json`
- `bundle.json`
- `closure.json`
- `refresh.json`
- `report.json`
- `repair_packet.json`
- `repair_handoff.json`
- `observability.json`
- `bug_packet.json`
- `session_export.json`

These files are not just logging output.
They are the runtime truth surfaces the kernel uses to reason about what is trusted, what is blocked, and what repair is still allowed.

## Bundle semantics

The bundle layer does more than validate JSON shape.
It has semantic checks.

Recent examples of semantic bundle hardening:

- catching proof that is structurally complete but semantically thin
- supporting truthful `already_satisfied` no-op runs without inventing fake patches
- blocking adjacent scope rewrites for add-only tasks
- blocking presentation drift for add-only tasks when the user did not ask for styling

This semantic distinction is one of the most important parts of the codebase.

## Repair path

When a run is blocked, Synrail does not just say “failed”.
It tries to create a bounded repair packet and a narrow repair prompt.

Key modules:

- `synrail_repair_packet_v0.py`
- `synrail_repair_handoff_v0.py`
- `synrail_repair_prompt_bridge_v0.py`
- `synrail_repair_focus_v0.py`
- `synrail_thin_output_v0.py`

The goal is to prevent repair from broadening into exploratory chaos.
The intended behavior is:

- identify the exact stale or missing subsurface
- name the next bounded step
- keep the repair within the same run and task

## Runtime helper path

For UI and web-like tasks, recent work added a more explicit small runtime verification helper so agents are biased toward:

- `curl`
- direct render checks
- small local runtime paths

before escalating to heavier browser automation.

This came from real probe logs where agents were drifting toward noisier or unavailable tooling before attempting simpler local verification.

## Checkpoint and continuation

Checkpoint support is first-class in the current kernel scope.
The intent is not just to save state, but to preserve one verified safe point that can be restored and verified honestly.

Continuation is also treated as first-class, because a large class of agent failures are not hard crashes; they are repair loops, stale artifacts, or ambiguous re-entry states.

## Code map for reviewers

If a reviewer wants the fastest code-first path, I would recommend this order:

1. `/Users/usbdick/Documents/New project/synrail/alpha.py`
2. `/Users/usbdick/Documents/New project/synrail/tools/reference/synrail_cli_v0.py`
3. `/Users/usbdick/Documents/New project/synrail/tools/reference/synrail_bootstrap_v0.py`
4. `/Users/usbdick/Documents/New project/synrail/tools/reference/synrail_bundle_v0.py`
5. `/Users/usbdick/Documents/New project/synrail/tools/reference/synrail_closure_v0.py`
6. `/Users/usbdick/Documents/New project/synrail/tools/reference/synrail_refresh_v0.py`
7. `/Users/usbdick/Documents/New project/synrail/tools/reference/synrail_repair_packet_v0.py`
8. `/Users/usbdick/Documents/New project/synrail/tools/reference/synrail_repair_handoff_v0.py`
9. `/Users/usbdick/Documents/New project/synrail/tools/reference/synrail_repair_prompt_bridge_v0.py`
10. `/Users/usbdick/Documents/New project/synrail/tools/reference/synrail_thin_output_v0.py`
11. `/Users/usbdick/Documents/New project/synrail/tools/reference/synrail_checkpoint_v0.py`
12. `/Users/usbdick/Documents/New project/synrail/tools/reference/synrail_doctor_v1.py`

Then read tests that express current expectations:

- `/Users/usbdick/Documents/New project/synrail/tests/test_controlled_start_smoke.py`
- `/Users/usbdick/Documents/New project/synrail/tests/test_truth_regressions.py`
- `/Users/usbdick/Documents/New project/synrail/tests/test_prompt_chain.py`
- `/Users/usbdick/Documents/New project/synrail/tests/test_gate_units.py`
- `/Users/usbdick/Documents/New project/synrail/tests/test_agent_adoption.py`

## What has been pressure-tested recently

Recent hardening work was not just abstract refactoring.
It came from repeated live probes with local agents.

Important wins from those runs:

1. Agents can now discover Synrail more natively through repo policy files.
2. Wrong-binary / PATH confusion for agent lanes was hardened.
3. `final_result.json` authoring became more guided and less guess-heavy.
4. `scenario_proof` guidance was improved.
5. truthful no-op (`already_satisfied`) runs are now supported without fake diffs.
6. adjacent scope drift for add-only tasks is blocked.
7. nested parent-git ambiguity is surfaced more explicitly.
8. UI runtime guidance now nudges agents toward lighter local checks.
9. presentation drift inside the new additive line is now blocked for plain add-only tasks.

## Current strengths

These are the strongest current arguments in favor of the project.

### 1. It has a sharp wedge

Synrail is not trying to solve all agent governance.
It has a concrete wedge: prevent false-green local bounded-change closure.
That is a good product discipline.

### 2. It distinguishes structure from semantics

A lot of systems stop at “fields exist”.
Synrail has increasingly explicit semantic checks.
That is a meaningful technical choice.

### 3. It takes repair seriously

Many systems handle the happy path and then collapse into vague retry loops on non-green runs.
Synrail treats bounded repair and continuation as first-class runtime behavior.

### 4. It is genuinely local-first

The current install and run path works without turning the system into a cloud service or daemon architecture.

### 5. It is increasingly pressure-tested against real agent behavior

A significant amount of the recent code was not imagined in the abstract.
It came from observing how Gemini and Claude actually drift, cheat, over-style, guess, or misread state.

## Current weaknesses and honest limitations

This section matters most for external critics.

### 1. The system is still very artifact-heavy

The `.synrail/` surface is rich, but it is also cognitively heavy.
A critic may reasonably ask whether the control value justifies the artifact volume for the target user.

### 2. Runtime verification is still not strong enough by default

Even after recent improvements, agents still often gravitate toward source-based checks like `grep` instead of stronger browser-level verification.
The project has improved this, but this is still a live seam.

### 3. The supported lane is narrow

This is a strength strategically, but also a product limitation.
If a reviewer expects remote-host, deployment-first, or broader operational coverage, the answer right now is: not yet.

### 4. The codebase is highly reference-oriented

The implementation is modular and explicit, but also sprawling.
A critic may fairly say the reference-module pattern is harder to hold in working memory than a smaller core with stricter boundaries.

### 5. Some semantics are still heuristic

Recent guards like scope alignment and presentation alignment are intentionally heuristic.
That is probably the right current move, but it means critics should ask:

- are these heuristics too brittle?
- are they overfitting to the observed probe tasks?
- do they generalize?

The current branch already takes one step to limit that risk:

- hostile observation guards are now scoped to the measured proof-sensitive task families instead of applying as a universal default

That helps, but it is still not enough to call the overfitting risk solved.

### 6. Claude automation on server still has harness friction

Some recent friction around headless Claude runs on the server was more about the execution harness and permission model than Synrail itself.
That is still operationally relevant and worth criticizing honestly.

## What critics should try to falsify

If I were attacking this project honestly, I would try to break it here first:

1. **Cost vs value**
- Is the control burden justified for the class of tasks it governs?

2. **Semantic overfitting**
- Are the newer semantic guards learning the real principle, or just memorizing recent agent mistakes?

3. **Runtime truth quality**
- Does the system still allow too much acceptance based on source-level evidence instead of genuine runtime evidence?

4. **Repair convergence**
- In ugly non-green states, does the repair loop really stay bounded, or does it still drift into archaeology?

5. **Operator load**
- Can a non-author actually operate this without hidden author intuition?

6. **Scope discipline**
- Does Synrail really prevent small prompt drift from becoming accepted output drift?

7. **Kernel simplicity**
- Is the current kernel the minimum necessary control system, or is it already too baroque for its wedge?

## Suggested reviewer questions

Here are the questions I would explicitly like critics to answer.

1. Is the wedge real and valuable, or too narrow to matter?
2. Is the proof-bundle model materially better than a simpler checklist + tests approach?
3. Are the semantic bundle checks a strong differentiator, or just complexity inflation?
4. Does the repair/continuation model create real operator value, or mostly more artifacts?
5. Is the local-first no-daemon approach a strength, or does it leave too much orchestration burden on the user?
6. Does the codebase look like a product-tightening trajectory, or like growing system theater?
7. If you had to cut this down by 50%, what would you keep?
8. If you had to commercialize or package this, what would you simplify first?

## Minimal reproduction path for reviewers

If a reviewer wants to try the current product contour quickly:

```bash
python3 tools/reference/synrail_install_v0.py --venv .venv
source .venv/bin/activate
synrail
synrail start "Add one bounded local change."
# fill in .synrail/final_result.json, .synrail/readback.txt, .synrail/scenario_proof.txt
synrail check
synrail repair-step
synrail retry
```

If they want local agents to discover the path natively:

```bash
python3 tools/reference/synrail_install_v0.py --venv .venv --project-root "$(pwd)"
```

## Short reading plan for critics

If a critic only has 20-30 minutes, I would suggest:

1. Read:
- `/Users/usbdick/Documents/New project/synrail/README.md`
- `/Users/usbdick/Documents/New project/synrail/docs/core/FIRST_RUN_GUIDE.md`
- `/Users/usbdick/Documents/New project/synrail/docs/boundary/CORE_SCOPE_001.md`
- `/Users/usbdick/Documents/New project/synrail/docs/core/SYNRAIL_RUNTIME_TRUTH_SURFACE.md`

2. Inspect code:
- `/Users/usbdick/Documents/New project/synrail/alpha.py`
- `/Users/usbdick/Documents/New project/synrail/tools/reference/synrail_cli_v0.py`
- `/Users/usbdick/Documents/New project/synrail/tools/reference/synrail_bundle_v0.py`
- `/Users/usbdick/Documents/New project/synrail/tools/reference/synrail_repair_prompt_bridge_v0.py`

3. Inspect tests:
- `/Users/usbdick/Documents/New project/synrail/tests/test_truth_regressions.py`
- `/Users/usbdick/Documents/New project/synrail/tests/test_controlled_start_smoke.py`

That is enough to form a legitimate first-pass opinion.

## My honest current assessment

My own best-faith assessment is:

- the project now has a real wedge
- it is no longer just conceptual framing
- the live probe loop has materially improved it
- some of the strongest recent changes came directly from real agent misbehavior
- the kernel is getting more credible

But I would still expect serious critics to push hard on:

- control cost
- artifact volume
- heuristic semantics
- source-proof vs runtime-proof quality
- whether the codebase can be compressed without losing its edge

That is exactly the feedback worth getting now.

## Closing note to critics

Please do not review this as if it were already claiming to be a universal agent platform.
Review it as a small control kernel with a narrow wedge:

**Can this system honestly reduce false-green bounded local agent execution, without collapsing into either ritual or chaos?**

That is the real question.
