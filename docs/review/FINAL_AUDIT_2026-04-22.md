# Final Audit — 2026-04-22

## Scope

This audit covers the current **local working tree** of `synrail` on branch `codex/first-extraction-pr`, evaluated on top of pushed commit `09f3bbf`.

It is intentionally broader than a commit review.
It covers:
- code and implementation state
- product and concept state
- benchmark and proof semantics
- critic-facing documentation and claim discipline
- live signal already captured in the repo

This is therefore a review of **current project truth**, not only of the last pushed GitHub state.

## Validation Snapshot

Validation run completed on the audited local state:
- full suite: `python3 -m unittest discover -s tests`
- result: `Ran 485 tests in 59.559s`
- status: `OK`

Focused suites also passed during this audit:
- `tests.test_cost_of_control_v0`
- `tests.test_everyday_benchmark_pack`
- `tests.test_small_template_text_fix_benchmark_pack`
- `tests.test_controlled_start_smoke`
- `tests.test_unseen_validation_pack`
- `tests.test_prompt_chain`
- `tests.test_untested_modules`
- `tests.test_agent_adoption`
- `tests.test_install_smoke`

AST parsing also succeeded for the key changed implementation modules, including:
- `tools/reference/synrail_cost_of_control_v0.py`
- `tools/reference/synrail_thin_output_v0.py`
- `tools/reference/synrail_operator_brief_v0.py`
- `tools/reference/synrail_repair_prompt_bridge_v0.py`
- `tools/reference/synrail_bundle_v0.py`
- `tools/reference/synrail_cli_v0.py`
- `tools/reference/synrail_install_v0.py`

## Executive Verdict

`Synrail` is no longer best described as a speculative control idea.
It now has a real, defendable kernel with visible product shape.

The strongest currently earned wedge remains:
- honest handoff / continuation
- runtime-backed closure
- bounded non-green repair

The most important progress in this tranche is different:
- the cheap default path is materially thinner
- the everyday economics lane is now machine-readable in a more disciplined way
- one focused everyday family now reads as a narrow repeatable class win rather than a one-off nice contour

The most honest current product verdict is:
- **narrow wedge earned**
- **broad win not earned**
- **focused everyday class win earned**
- **broader everyday class still baseline-favorable overall**

## Main Findings

### 1. The focused benchmark send surfaces are materially cleaner in the current local snapshot

The critic-facing docs already point to the focused benchmark tranche, including:
- `tests/test_small_template_text_fix_benchmark_pack.py`
- `fixtures/small_template_text_fix_benchmark_pack_001.json`
- `fixtures/cost_of_control_small_template_text_fix_001.json`
- `docs/review/Priority.md`

In the current local snapshot, these files are present alongside the critic-facing references.
That does **not** automatically make the external send package complete.
It does mean the earlier “docs point at focused benchmark surfaces that are not present locally” caveat no longer matches the current branch snapshot.

The narrower remaining send/readiness caution is different:
- cut the external handoff from an explicitly chosen snapshot, not from a drifting local working tree

### 2. The thin-output parser ambiguity is no longer visible in the current file

The current `synrail_thin_output_v0.py` snapshot exposes one `build_parser()` definition at the live CLI entrypoint.
That removes the earlier needless ambiguity in a sensitive user-facing output module.

This is a small cleanup, but it matters because critic-facing branch-hygiene caveats should not lag behind the code they describe.

## What Is Now Genuinely Earned

### 1. Cheap default proof path is materially stronger than before

The default happy path now genuinely centers on `final_result.json`.
The system no longer behaves as if authored prose is the natural first contour.

Current local truth:
- `start` materializes only `final_result.json` by default
- `readback.txt` is fallback-only
- `scenario_proof.txt` is fallback-only
- `cleanup_status` stays absent on the cheap happy path unless explicitly demanded
- `repair-step` is no longer the default next hop for normal non-green handling

This is not just doc wording.
It is reflected in smoke coverage and in live accepted runs already captured in the repo.

### 2. Everyday economics is now more disciplined than earlier phases

The broader repeatable everyday pack currently reads:
- `2` scenarios: `SYNRAIL_BETTER`
- `4` scenarios: `BASELINE_GOOD_ENOUGH`
- `0` scenarios: `UNCLEAR`

This is important because the lane is no longer hiding behind unresolved ambiguity.
It now expresses a cleaner product truth:
- some narrow cheapened wins exist
- broad everyday superiority is still not earned

The economics layer is also more honest than before because it now separates:
- `fixed_control_mass`
- `behavioral_control_tax`
- `total_control_burden`
- `operator_visible_actions`
- `got_lost_moments`

That separation is important.
It lets the project talk about kernel cheapness vs behavior cheapness more precisely instead of collapsing everything into one vague “overhead” number.

### 3. A focused everyday class win is now real

The current focus family is `small_template_text_fix`.
This is the most important new product fact in the economics lane.

This focused family now reads as:
- `SYNRAIL_BETTER`
- `LOW_VARIANCE_REPEATABLE`
- `FOCUSED_CLASS_CHEAP_ENOUGH`
- `FOCUSED_CLASS_BEHAVIOR_CHEAP_BY_DEFAULT`

That remains important because the project is no longer saying only:
- “we have a few nice everyday paths”

It can still say something narrower and stronger:
- “we have one bounded repeatable family that reads as a cheap enough and behavior-cheap enough class win”

But the reading is now also more honest than that headline alone suggests.
A same-family behavior-independence pressure slice now shows the focused class can remain `SYNRAIL_BETTER` and `FOCUSED_CLASS_KERNEL_CHEAP_ENOUGH` while behavior cheapness drops to `FOCUSED_CLASS_BEHAVIOR_NOT_YET_CHEAP_BY_DEFAULT` when an extra skippable surface reappears.

That is still not a broad everyday victory.
But it is a more critic-resistant product milestone because the branch can now distinguish the canonical low-drag wedge from the still-fragile behavior-independence story.

### 4. Proof independence is stronger and more critic-resistant

On strict proof-sensitive lanes, the system now rejects:
- thin labeled prose
- `Output: ok`
- exit-code-only observations
- empty command-confirmation claims
- thin structured self-description that still does not anchor to concrete observed evidence

At the same time, concise concrete runtime-backed evidence still passes.
That is the right direction.
The system is not becoming “richer in prose”; it is becoming stricter about what prose is allowed to count as trust-bearing.

### 5. Restore is now narrower and more honest

The local restore matrix now covers:
- clean git
- dirty tracked
- dirty untracked
- mixed file state
- non-git file-copy fallback
- no-commit git via explicit file-copy contour
- honest unsupported fail

This is not broad restore maturity yet.
But it is a meaningful change from “restore story by narrative” toward “restore story by constrained matrix”.

### 6. Thin shell and non-green path improved in product-relevant ways

The shell and first non-green loop are now better in substance, not just aesthetics.

Key changes:
- the default shell path is shorter and less cluttered
- `synrail check` now carries the first bounded repair more often itself
- `repair-step` is treated as helper surface, not everyday default
- change-impact invalidation narrows non-green summaries toward stale obligations rather than re-describing the whole contour

That makes the system feel less like a ceremony stack and more like an execution kernel.

### 7. Evidence hygiene is now closer to a real process rule

Roadmap motion is now explicitly tied to classified evidence sets rather than a single noisy run.
That matters because one of the easiest ways for this project to drift is to harden the kernel in response to harness pain or messy anecdotes.

This tranche pushes the project in the opposite direction:
- product-owned failures drive kernel moves
- noisy mixed cases are treated with more caution
- one bad run is no longer treated as automatic justification for new product hardening

## What Improved But Is Still Not Fully Earned

### 1. Broad everyday economics are still not won

This remains the clearest remaining product weakness.
The broader repeatable-everyday reading is still:
- `BASELINE_GOOD_ENOUGH`

That means the project cannot honestly claim:
- “Synrail is now cheap enough for everyday work in general”

The strongest defensible claim is narrower:
- one bounded focused everyday family now looks cheap enough and behavior-cheap enough on the canonical pack
- same-family pressure already shows that behavior cheapness is still less stable than kernel cheapness
- the broader class still does not

### 2. The strongest focused family is still narrow

`small_template_text_fix` is useful and important.
But critics should still be allowed to ask:
- is this family too narrow to carry large product weight?
- does it generalize beyond this bounded shape?
- does the win survive uglier or more tool-heavy everyday contours?

The right answer today is:
- this focused win is real
- but it is still intentionally narrow

### 3. Proof independence is still corpus-bounded, not universal

The current strict lanes are materially better than before.
But the project still should not claim universal proof independence.

The right wording is:
- proof independence has materially improved on measured strict lanes
- runtime-backed trust is more real than before
- authored prose is less able to sneak through as hidden trust
- full general proof independence is still not proven across broad contour space

### 4. Restore maturity is still matrix-bounded

Restore is now less embarrassing and more honest.
But the right claim is still:
- narrow, explicit, locally regression-backed restore coverage

The wrong claim would be:
- “restore is now mature in general”

## Code And Implementation Audit

### What looks strong

The codebase changes are not superficial.
They meaningfully touch:
- bootstrap and starter behavior
- bundle semantics
- cost-of-control aggregation
- thin output / refresh narrowing
- operator brief and repair bridge rendering
- install and agent adoption behavior
- critic-facing documentation

The strongest implementation qualities in this tranche are:
- better separation of economics dimensions
- stronger focused benchmark logic
- better narrowing of stale proof repair summaries
- reusable-proof-surface awareness in operator-facing repair artifacts
- no obvious breakage across a large test surface

### What still looks prototype-like

A few places still carry prototype smell:
- duplicate parser definition in `synrail_thin_output_v0.py`
- the project is still being presented from a very dirty local worktree rather than a clean integrated branch state
- some critic/send artifacts point at files not yet tracked in git

None of these look like product-kernel regressions.
But they do affect polish, trust and handoff cleanliness.

## Concept And Product Audit

### Strongest product idea

The strongest concept remains:
- this is not a “better coder” layer
- it is a **better closure / repair / handoff kernel**

That framing still looks correct.
The evidence continues to support it.

### Why the idea is stronger than an ordinary wrapper

The project is stronger than a typical AI wrapper because it has coherent discipline around:
- false closure
- runtime-backed trust
- bounded next safe step
- second-operator continuity
- restore honesty
- claim discipline

That combination still feels relatively rare and product-shaped.

### Where the concept is still at risk

The biggest risks remain:
- everyday economics still being too heavy outside narrow wins
- broadening claims faster than evidence broadens
- allowing send/readiness packaging to outrun tracked branch truth
- mistaking a narrow focused class win for a broad class win

## Live Evidence Status

The repo now already contains meaningful live external signal.
Most importantly:
- Gemini reached accepted closure on the cheapened trivial contour
- Claude also reached accepted closure on the same contour once the wrapper-level harness seam was removed
- the remaining Claude seam on Hetzner was narrowed from “product path unclear” to “host permission policy blocks even correct local path execution”

That is a real improvement in diagnosis quality.

The current local native-launch work also sharpened the repo-native fallback path:
- installer output now surfaces exact `python3 alpha.py` status / start / check commands
- generated local agent policy now includes an explicit repo-local fallback block
- an exploratory Hetzner probe showed Claude switching from wrapper denial to the correct `python3 alpha.py` path

The remaining blocker there is now clearly host approval policy, not missing product guidance.

## What Critics Should Try To Falsify

If an external critic wants to be maximally useful, the best pressure points are now:
- whether the focused `small_template_text_fix` class is truly representative of anything larger than itself
- whether the broader everyday economics lane remains too expensive to justify the control layer
- whether runtime-backed trust still depends on hidden authored framing outside the measured strict lanes
- whether restore ergonomics stay honest and followable under messier workspaces than the current narrow matrix
- whether second-operator continuity still works on uglier live states, not just curated continuation contours
- whether the project really follows the evidence-classification discipline in practice
- whether the current native-launch improvement can become truly boring-by-default on hostile agent hosts

## What The Project Can Honestly Claim Right Now

It can honestly claim:
- `Synrail` has a real closure / repair / handoff kernel
- the cheap default proof path is materially thinner than before
- optional prose is no longer the natural first contour on the happy path
- broader repeatable everyday results are now machine-readable and no longer hide behind unresolved ambiguity
- one bounded focused everyday family now reads as a repeatable cheap-enough and behavior-cheap-by-default canonical win, but same-family pressure already shows that behavior cheapness is not yet fully independent
- proof-sensitive strict lanes are meaningfully harder to game with thin self-description
- restore coverage is narrower and more honest than before
- evidence hygiene is more explicit and process-shaped than before

It should **not** yet claim:
- broad everyday superiority
- universal proof independence
- broadly mature restore behavior
- fully boring-by-default native launch on all agent hosts
- that all critic-facing send materials are already perfectly mirrored by tracked branch state

## Bottom Line

The current project state is strong enough to justify serious external criticism.
That alone is progress.

This is no longer best described as “an interesting control idea with lots of md files.”
It is now a real local execution kernel with:
- a strong handoff / continuation wedge
- materially better trust discipline
- a narrower and more honest restore story
- one genuine focused everyday class win
- better benchmark discipline than earlier phases

The most honest overall verdict is:
- **strong narrow product slice**
- **focused everyday class win earned**
- **broader everyday class still not won**
- **external critique now appropriate and valuable**

## Pre-Send Caveats

Before external handoff, the following should be acknowledged explicitly:
- the audit reflects the current local working tree, not only pushed GitHub state
- the external send should be cut from an explicitly chosen snapshot rather than a drifting local working tree

These are send/readiness issues, not evidence that the product kernel regressed.
But they should be named honestly.
