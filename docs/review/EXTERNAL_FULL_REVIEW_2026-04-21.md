# Synrail External Full Review

Status date: 2026-04-22
Repo: `synrail`
Review type: current local-roadmap closure audit prepared for external critics
Reviewed snapshot: exact selected repository snapshot prepared for critic handoff
Verification note: rerun the listed commands on the exact snapshot you send
This review should travel with the exact snapshot it describes, not with a drifting local working tree.

## Why this file exists

This file is meant to replace a scattered bundle of partial briefs with one critic-facing review of the current branch truth.

It is intentionally not a pitch deck.
It is not trying to smooth over the remaining weaknesses.
It is meant to help an external critic answer one question:

- is `Synrail` now a real product wedge with credible local proof, or still a heavy internal ritual that has not yet earned its weight?

## One-paragraph verdict

`Synrail` now looks like a real local proof-and-repair control kernel with one clearly earned wedge: honest handoff and bounded continuation on non-green states. It is stronger than it was in the previous review cycle because the default proof path is cheaper, runtime-backed closure is more real, restore is more matrix-backed, and roadmap decisions are better gated against noisy evidence. But the broad win is still not earned. Everyday economics remain baseline-favorable overall, proof independence is still measured-lane truth rather than broad truth, and the evidence base is still partly self-curated. The honest reading is "narrow wedge earned, broad product win not earned yet."

## Current self-assessment

This is an internal but deliberately critical reading of the current branch:

- concept strength: high
- implementation maturity: medium
- external proof strength: medium-low
- everyday economics: improved but still not won
- strongest wedge: handoff / continuation honesty
- strongest remaining weakness: everyday control burden relative to baseline

If a critic wants the shortest current summary:

- the project already looks like more than framing
- the kernel is real
- the strongest earned value is honest continuation and bounded repair
- the broad "this should be your default coding lane" claim is still not earned

## What Synrail is

`Synrail` is a local control kernel for coding-agent work.

It does not primarily try to make the model more capable at writing code.
Its main job is different:

- prevent false closure
- require trust-bearing acceptance
- keep non-green states bounded and legible
- preserve a followable next safe step for a later operator or agent
- make restore and recovery honest on covered workspace families

This is why the product should be read less as "an agent framework" and more as:

- a truth-and-closure kernel
- a bounded repair kernel
- a handoff-safety layer

## Current user contour

The intended local contour on the current branch is now:

1. `synrail`
2. `synrail start "Describe the bounded change"`
3. do the work
4. strengthen `.synrail/final_result.json` first, leave `readback.txt` and `scenario_proof.txt` untouched unless `synrail check` explicitly names one, and leave `cleanup_status` absent unless Synrail explicitly asks for cleanup attestation
5. `synrail check`
6. if blocked: fix only the named gap from `synrail check`; when refresh invalidation matches the active run, the default summary now points only at the stale obligation class
7. use `synrail repair-step` only if a standalone bounded repair prompt is actually useful
8. use `synrail restore` only when the contour explicitly calls for it
9. stop only at accepted closure

Important current properties:

- `start` materializes only `.synrail/final_result.json` by default
- fallback prose surfaces stay hidden by default
- `cleanup_status` now stays off the cheap happy path unless Synrail explicitly asks for cleanup attestation
- normal `synrail check` can satisfy `cleanup_status` from doctor-ready workspace truth without manual `final_result.json` repair
- `check` is the default non-green path
- `repair-step` is now a helper surface, not the default next hop
- when refresh invalidation matches the active run, the default summary now points only at the stale obligation class instead of broadly restating the whole non-green contour
- wrapper-aware hints now keep install and shell instructions honest when `synrail` is not on `PATH`

## What the last local roadmap actually shipped

The recent local roadmap was not another broad hardening wave.
It was a set of narrow tranches against specific product seams, without adding new semantic sections, new continuation families, or new runtime artifact surfaces.

The current branch now includes shipped progress on these lines:

1. behavioral cheapening by default
2. repeatable everyday economics benchmark
3. proof-independence stress
4. restore maturity across workspace families
5. shell compression toward a thinner first loop
6. evidence hygiene as a process rule
7. stronger handoff / continuation validation on uglier contours
8. cleanup truth on the cheap happy path
9. refresh-driven stale-obligation narrowing on non-green contours
10. send-ready external review pack and wrapper-aware first-run honesty

The right way to read this is:

- not "more machinery"
- but "more pressure on the same wedge"

## Code and implementation review

### What looks strong in the implementation

1. The shell is genuinely cheaper than before.

- `start` and `check` now center the default path on `final_result.json`
- fallback proof surfaces are hidden by default
- wrapper-aware command hints avoid lying about `synrail` availability on a fresh install

Relevant files:

- `tools/reference/synrail_cli_v0.py`
- `tools/reference/synrail_install_v0.py`
- `tests/test_controlled_start_smoke.py`
- `tests/test_install_smoke.py`

2. Final-result-first repair semantics are more coherent.

The branch now more consistently keeps partial-proof repair on the `final_result` artifact first when that artifact is still semantically weak, before materializing or targeting fallback proof surfaces.

Relevant files:

- `tools/reference/synrail_repair_handoff_v0.py`
- `tools/reference/synrail_repair_prompt_bridge_v0.py`
- `tools/reference/synrail_prompt_followup_v0.py`

3. Runtime-backed closure is more real than before.

Optional prose surfaces can now stay absent on measured lanes when strong `final_result` structure and runtime-backed verification already carry trust.
Cleanup truth can also ride doctor-ready runtime truth more honestly on the cheap path.

Relevant files:

- `tools/reference/synrail_bundle_v0.py`
- `tools/reference/synrail_bootstrap_v0.py`
- `tools/reference/synrail_closure_v0.py`
- `tools/reference/synrail_spine_v0.py`

4. Proof independence is materially stronger.

Strict proof-sensitive lanes now reject several forms of structured self-description that previously looked almost sufficient:

- labeled action narrative
- labeled restatement without evidence
- placeholder output like `Output: ok`
- exit-code-only observations
- command-confirmation prose without literal runtime evidence

Relevant files:

- `tools/reference/synrail_bundle_v0.py`
- `tests/test_truth_regressions.py`

5. Restore is more matrix-backed than before.

The local restore matrix now has regression coverage for:

- clean git
- dirty tracked git
- dirty untracked git
- mixed tracked and untracked git
- no-commit git via file-copy fallback
- non-git file-copy restore
- unsupported honest fail

Relevant files:

- `tools/reference/synrail_checkpoint_v0.py`
- `tests/test_gate_units.py`

6. Benchmark and evidence layers are more disciplined.

The current branch now explicitly tracks:

- fixed control mass
- behavioral control tax
- total control burden
- checks per accepted closure
- operator-visible actions
- got-lost moments

Roadmap-evidence moves are also gated on classified evidence sets rather than justified from a single bad run.

Relevant files:

- `tools/reference/synrail_baseline_harness_v1.py`
- `tools/reference/synrail_cost_of_control_v0.py`
- `tools/reference/synrail_alpha_evidence_ownership_v0.py`

### What still looks prototype-like

1. Some of the strength still comes from carefully curated local packs and fixtures.

That is not fake, but it is not the same thing as broad live product proof.

2. The shell is thinner, but still not fully frictionless.

It is much better than the earlier three-starter-file contour, yet a critic can still reasonably argue that the outer loop remains heavier than the narrow wedge strictly requires.

3. The strongest semantics are still concentrated on measured lanes.

That is the right disciplined move for now, but it still means the broad proof story is not yet universal.

4. The codebase is now wide enough that cross-module alignment matters.

This branch handles that better than before, but the project still depends on careful semantic alignment between:

- shell wording
- benchmark accounting
- repair policy
- proof bundle semantics
- critic-facing claims

That is a manageable maturity problem, but it is a real one.

## Verification status

This audit reran the current test suite on the local snapshot and got:

- `462 tests`
- `OK`

That is important because the recent work touched shell, proof, repair, benchmark, docs, and outward-facing review material all at once.

The green suite does not prove broad product victory.
It does strongly reduce the risk that the latest tranches simply broke existing local truth.

## Product and concept review

### What looks genuinely earned

#### 1. There is now a real product wedge

The project no longer reads like an elaborate policy wrapper around ordinary agent work.
It now has a clearer earned wedge:

- honest bounded repair
- truthful non-green states
- second-operator followability
- stronger runtime-backed closure

The strongest of these is still handoff / continuation honesty.

#### 2. Two repeatable everyday winners now exist, and one narrow focused family now has five justified low-drag paths

The current repeatable everyday benchmark pack reads:

- `2` scenarios: `SYNRAIL_BETTER`
- `4` scenarios: `BASELINE_GOOD_ENOUGH`
- `0` scenarios: `UNCLEAR`

The stronger narrow reading is inside the current focus family:

- focus family: `small_template_text_fix`
- focused family record count: `5`
- focused verdict: `SYNRAIL_BETTER`
- focused stability: `LOW_VARIANCE_REPEATABLE`
- focused cheap-enough status: `FOCUSED_CLASS_CHEAP_ENOUGH`
- focused behavior-cheapness status on the canonical pack: `FOCUSED_CLASS_BEHAVIOR_CHEAP_BY_DEFAULT`
- focused behavior-cheapness status under same-family pressure can fall to `FOCUSED_CLASS_BEHAVIOR_NOT_YET_CHEAP_BY_DEFAULT` while kernel cheapness still reads `FOCUSED_CLASS_KERNEL_CHEAP_ENOUGH`

That is not a broad economics win.
It is a useful intermediate result because the pack now contains one narrow repeatable low-drag family instead of reading as "all burden, zero real justification."
The newer same-family pressure slice also makes the economics split more honest by showing behavior drift can reappear without collapsing the kernel-cheap reading.

#### 3. The project is more disciplined about not growing machinery

This matters more than it sounds.

The recent roadmap closure did not add:

- new semantic proof sections
- new continuation families
- new runtime artifact surfaces
- a broader shell platform story

That is a genuine positive signal.
It suggests the team is learning to harden the wedge without reflexively growing the system.

### What is improved but still not earned

#### 1. Everyday economics are still not won

This is still the main enemy metric.

The honest class verdict remains:

- `BASELINE_GOOD_ENOUGH`

That means a critic is still right to ask:

- is the control burden worth it on bounded everyday work?
- is the current five-record focused-family win a wedge or still mostly a curiosity?

#### 2. Proof independence is still measured-lane truth

The latest hardening is real, but still narrow.
The right critic question is still:

- does this hold outside the current strict local lanes, or mostly inside the current measured attack pack?

#### 3. Restore is improved, but still explicitly narrow

Restore is no longer the old "claim more than coverage" weakness.
But it is still a narrow matrix and should still be read that way.

The honest current formula is:

- local coverage exists
- broad maturity is not claimed

#### 4. The evidence base is stronger, but not independent enough yet

The evidence-ownership split is real.
The roadmap gate is real.
The benchmark packs are useful.

But this is still partly self-curated system truth.
That is why fresh external pressure remains important.

## Current benchmark reading

Across the current six-scenario repeatable everyday pack, `Synrail` currently adds on average:

- `1` operator minute
- `0` checks per accepted closure
- `1` mandatory mental step
- `1` trust-bearing artifact
- `0` required visible surfaces
- `0` skippable visible surfaces
- `1` operator-visible action
- `0` got-lost moments
- `2` fixed control-mass units
- `1` behavioral control-tax unit
- `3` total control-burden units

It currently gains on average:

- `29` points of artifact completeness

The right reading is:

- the cheapened contour is materially lighter than before
- the broader pack has two repeatable low-drag winners, while the focused family now has five justified low-drag paths
- the canonical focused family reads as cheap enough and behavior-cheap by default
- same-family pressure now shows behavior cheapness can still break independently while kernel cheapness remains intact
- the class is still baseline-favorable overall

This pack should be treated as a bounded internal benchmark, not as broad external economic proof.

## Review of the core idea

The strongest conceptual move in `Synrail` is not "make the model write better code."
It is this:

- do not let a coding agent sign off its own weak result as done
- if the run is non-green, keep the next safe step bounded
- if a second operator takes over, keep the state followable without author memory

That is a strong and relatively uncommon product angle.

The idea is strongest where:

- false closure matters
- bounded recovery matters
- second-operator continuity matters

It is weakest where:

- the task is trivial
- the baseline is already safe enough
- the burden of extra governance can outweigh the saved loss

That is why the project currently feels more convincing as:

- a trust-and-handoff kernel

than as:

- a universally better default coding lane

## What external critics should try to falsify

If a critic wants to be maximally useful, the highest-value attacks are:

1. Everyday heaviness
- which visible step in the everyday lane still feels least worth its weight?

2. Self-issued proof
- which artifact, proof surface, or shell claim still feels too author-shaped to trust?

3. Restore or handoff value
- in restore, re-entry, or second-operator continuation, what concrete value does `Synrail` create over a simpler substitute?

4. Measured-lane overfitting
- do the strongest proof claims hold outside the current measured local attack pack?

5. Non-author operability
- where would a second operator still need author intuition to move safely?

## What is deliberately not being claimed

This branch should not be sold as:

- broad proof universality
- broad restore maturity on arbitrary workspaces
- broad everyday economics victory
- a finished platform shell
- a final product story

The right claim level is narrower:

- a real kernel exists
- one strongest wedge is earned
- several important weaknesses are now better bounded and better measured
- the project is ready for another serious hostile outside pass

## What is ready now

These are the most defensible current positives:

1. one send-ready local review pack exists
2. the first-run install path is more honest
3. the shell is thinner and more portable-aware
4. proof semantics are stricter on measured lanes
5. restore is more matrix-backed
6. handoff/continuation honesty remains the strongest current differentiator
7. roadmap moves are better protected from noisy evidence

## What is still in plan, not victory

The current roadmap status still says the next high-value moves are:

1. hand the branch to critics before broadening product story
2. collect one fresh live external signal on the cheapened and evidence-gated branch
3. only after that decide whether to package broader or harden further

This is the right sequencing.

## What is deliberately frozen

The branch is currently trying not to grow in these directions:

- new continuation families
- richer repair history
- richer operator evidence for completeness only
- broad product shell growth
- hosted telemetry platform
- broad packaging work
- new conceptual layers without runtime consequence

That freeze is a strength, not a weakness.

## Supporting files for critics

If a critic wants to go deeper after reading this file, the best next files are:

- `docs/core/ALPHA_TEST_PACK_001.md`
- `docs/review/EXTERNAL_CRITIQUE_PACK_001.md`
- `docs/review/KNOWN_WEAKNESSES_001.md`
- `docs/review/ROADMAP_STATUS_001.md`
- `tests/test_truth_regressions.py`
- `tests/test_alpha_test_pack_smoke.py`
- `tests/test_claim_validation_pack.py`
- `tests/test_small_template_text_fix_benchmark_pack.py`
- `tests/test_cost_of_control_v0.py`
- `fixtures/repeatable_everyday_benchmark_pack_001.json`
- `fixtures/cost_of_control_everyday_001.json`
- `fixtures/small_template_text_fix_benchmark_pack_001.json`
- `fixtures/cost_of_control_small_template_text_fix_001.json`
- `fixtures/small_template_text_fix_behavior_pressure_pack_001.json`
- `fixtures/cost_of_control_small_template_text_fix_behavior_pressure_001.json`

## Final verdict

The old question "is there any real product here?" is now much closer to settled.
The better current question is:

- can this kernel become cheap enough, trust-bearing enough, and behavior-independent enough to win not only on handoff / continuation honesty, but also beyond the current narrow `small_template_text_fix` family without feeling like a heavy control stack?

That question is still open.
But the project now looks substantive enough that a strong critic can answer it against a real system rather than a vague concept.
