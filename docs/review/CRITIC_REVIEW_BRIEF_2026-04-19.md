# Synrail Critic Review Brief

Status date: 2026-04-19
Repo: `synrail`
Current branch: `codex/first-extraction-pr`
Current reviewed code commit: `db4a2d4`
Current regression status: `449 tests OK`

## Why this document exists

This brief is meant for honest external criticism.

It is not a pitch deck.
It is not trying to hide the remaining weaknesses.
It is a compressed explanation of:

- what `Synrail` is now
- what changed in the latest local roadmap tranche
- what is genuinely earned
- what is still narrow, weak, or unproven
- what critics should attack first if they want to falsify the current product story

## One-sentence verdict

`Synrail` is now a more credible local proof-and-repair control kernel than it was on the previous outside pass, but the broad win is still **not** earned: the strongest wedge remains handoff / continuation honesty, while everyday economics still lag baseline overall.

## What changed since the last outside pass

The current branch shipped a full local roadmap tranche without broadening control surface area.

Important constraint:

- this work did **not** add new semantic proof sections
- it did **not** add new continuation families
- it did **not** add new runtime artifact surfaces
- it did **not** expand the shell into a broader platform story

Instead it concentrated on seven narrow product seams:

1. cheaper default proof path
2. repeatable everyday economics reading
3. proof-independence stress
4. restore maturity across workspace families
5. thinner first-loop shell behavior
6. evidence hygiene as an actual roadmap-decision rule
7. uglier handoff / continuation validation

That is the right way to read the current branch: not as “more system”, but as “more disciplined pressure on the existing wedge”.

## Current product contour

At the user level the intended local contour is now:

1. `synrail`
2. `synrail start "Describe the bounded change"`
3. do the work
4. strengthen `.synrail/final_result.json` first
5. `synrail check`
6. if blocked: `synrail repair-step`
7. fix only the named gap
8. `synrail retry` or `synrail check`
9. stop only at accepted closure

Important change from earlier branches:

- `start` now materializes only `.synrail/final_result.json` by default
- `readback.txt` and `scenario_proof.txt` are now fallback-only surfaces
- if a later `synrail check` explicitly needs one of them, `Synrail` can prepare that fallback on demand

That means the first-loop proof path is now visibly thinner than the older “three starter proof files” contour.

## What is now genuinely earned

These are the strongest current positive claims.

### 1. Runtime-backed closure is more real than before

On the measured lanes, optional prose surfaces can now stay absent when trust is already carried by strong `final_result` structure plus runtime-backed verification.

This matters because `Synrail` is now less dependent on the agent writing extra narrative artifacts just to satisfy the kernel.

### 2. There is now one repeatable everyday winner

The current repeatable everyday benchmark pack is still baseline-favorable overall, but it no longer reads as “all overhead, no concrete win”.

Current pack truth:

- `1` scenario: `SYNRAIL_BETTER`
- `4` scenarios: `BASELINE_GOOD_ENOUGH`
- `0` scenarios: `UNCLEAR`

This is not a broad economics victory.
It is one repeatable low-drag win inside a still-baseline-favorable class.

That is a useful and honest intermediate result.

### 3. Proof independence is materially stronger

The strict proof-sensitive lanes now block several kinds of structured self-description that previously looked “almost sufficient”:

- labeled action narrative
- labeled restatement without evidence
- thin command-confirmation prose
- placeholder output like `Output: ok`
- exit-code-only observations

At the same time:

- concrete terse evidence still passes
- runtime-backed verification remains the primary trust path
- unknown task classes do not inherit the strict hostile policy automatically

This is a real step toward proof that carries trust independently of authored prose.

### 4. Restore is more honest and more locally grounded

The restore story is still narrow, but the local matrix is now explicit and regression-backed across:

- clean git workspace
- dirty tracked git workspace
- dirty untracked git workspace via file-copy fallback
- mixed tracked + untracked git workspace via file-copy fallback
- git workspace without a committed `HEAD` via file-copy fallback
- non-git file-copy restore
- unsupported contours that fail early and honestly

This is not the same as “restore is broadly mature”.
It does mean restore is now less claim-driven and more matrix-driven than before.

### 5. Handoff / continuation honesty is still the strongest wedge

This remains the clearest baseline advantage.

Recent validation now covers not just the neat packet-first path, but uglier contours with:

- repeated doctor pressure
- non-resumable boundaries
- missing continuation inputs under retry pressure

That makes the current handoff wedge look more like a product property and less like a lucky canonical demo.

### 6. Evidence hygiene is now a process rule, not only a classifier

The branch already had ownership classification for single reports.

Now it also has a decision gate for evidence sets:

- `ALLOW_KERNEL_MOVE`
- `ALLOW_KERNEL_MOVE_WITH_CAUTION`
- `REROUTE_NON_KERNEL`
- `MANUAL_REVIEW_REQUIRED`

That matters because roadmap moves can no longer be justified just because “a run ended badly”.

The intended rule is now explicit:

- clean `product` / `none` evidence can drive kernel moves
- explicitly strong `mixed` evidence can drive kernel moves with caution
- `harness` / `operator` / `agent` evidence should reroute
- evidence sets containing manual-review-only signals should stay manual-review-only

This is a meaningful maturity step for the development process itself.

## What is improved but still not earned

This section matters most.

### 1. Everyday economics are still not won as a class

The latest benchmark pack is better than before, but the honest class verdict is still:

- overall `BASELINE_GOOD_ENOUGH`

That means critics are still right to ask whether the control burden is worth it for trivial or additive work.

Current status is:

- one low-drag winner exists
- the class still does not beat baseline overall

### 2. Proof independence is still measured-lane truth, not broad truth

The latest hardening is real, but still narrow.

A critic should still ask:

- does this generalize beyond the current proof-sensitive local lanes?
- do the hostile guards capture the principle, or only the latest mistakes?
- does domain-specific work still slip through thin but structured phrasing?

### 3. Restore maturity is still matrix-local, not platform-wide

Restore is no longer an embarrassing honesty bug on the covered contours.
But it is still a narrow matrix and still potentially heavy from an operator point of view.

The current branch should be read as:

- explicit local coverage exists
- broader maturity is not yet claimed

### 4. Thin shell is closer to fact, but not fully done

The first-loop path is cleaner now.
The default help is thinner.
`start` and `check` now spend less attention budget on optional fallback chatter.

But compatibility and advanced surfaces still exist underneath, and critics may still reasonably feel that the shell is heavier than the wedge strictly requires.

### 5. The evidence base is stronger, but still partly self-curated

This branch is much better at preventing noisy reports from impersonating kernel evidence.
That does not magically make the evidence base clean.

Critics should still press on:

- how much of this is local and self-authored?
- how much is fresh outside signal?
- how many of the current wins are still canonical rather than independently repeated?

## Strongest current positives

If I had to name the three strongest current positives:

1. handoff / continuation honesty
2. runtime-backed closure on the measured cheapened lane
3. the fact that the branch improved trust and reduced clutter without growing new kernel machinery

## Strongest current negatives

If I had to name the three strongest current negatives:

1. everyday economics still lose to baseline overall
2. proof-independence confidence is still corpus-bounded
3. restore and shell ergonomics may still feel too heavy relative to the narrow wedge

## What critics should attack first

If I were trying to falsify the project honestly, I would attack these points in this order:

1. **Everyday economics**
   - Is one benchmark-pack winner just a local exception?
   - Does the system still feel visibly heavier than baseline on ordinary bounded tasks?

2. **Proof independence**
   - Can you still get acceptance through structured self-description on a contour the current tests did not anticipate?
   - Are the stricter proof rules learning principle or overfitting?

3. **Restore maturity**
   - Does the local restore matrix still become confusing or too destructive on less tidy workspaces?
   - Is the operator story around restore still too heavy?

4. **Second-operator reality**
   - Can a non-author still follow the non-green contour without hidden author memory on a genuinely messy run?

5. **Evidence discipline**
   - Does the team actually obey the new evidence gate in practice, or only in local helper code and docs?

## Suggested reviewer questions

These are the questions I would explicitly want critics to answer.

1. Is the current wedge now strong enough to matter, or still too narrow?
2. Is the benchmark story materially improving, or still mostly ceremony relative to baseline?
3. Are the latest proof hardening moves catching the right things?
4. Is restore now “honest but narrow”, or actually “mature enough for the wedge”?
5. Does the current shell feel thinner in use, or just thinner in wording?
6. Is handoff / continuation genuinely the best reason this project should exist?
7. If you had to cut the system down again, what would you preserve and what would you delete immediately?

## Recommended reading path for critics

If a critic has only 20–30 minutes, I would suggest:

1. Read:
- [README.md](/Users/usbdick/Documents/New%20project/synrail/README.md)
- [FIRST_RUN_GUIDE.md](/Users/usbdick/Documents/New%20project/synrail/docs/core/FIRST_RUN_GUIDE.md)
- [ROADMAP_STATUS_001.md](/Users/usbdick/Documents/New%20project/synrail/docs/review/ROADMAP_STATUS_001.md)
- [TECHNICAL_MAP_001.md](/Users/usbdick/Documents/New%20project/synrail/docs/review/TECHNICAL_MAP_001.md)

2. Inspect code:
- [alpha.py](/Users/usbdick/Documents/New%20project/synrail/alpha.py)
- [synrail_cli_v0.py](/Users/usbdick/Documents/New%20project/synrail/tools/reference/synrail_cli_v0.py)
- [synrail_bundle_v0.py](/Users/usbdick/Documents/New%20project/synrail/tools/reference/synrail_bundle_v0.py)
- [synrail_checkpoint_v0.py](/Users/usbdick/Documents/New%20project/synrail/tools/reference/synrail_checkpoint_v0.py)
- [synrail_alpha_evidence_ownership_v0.py](/Users/usbdick/Documents/New%20project/synrail/tools/reference/synrail_alpha_evidence_ownership_v0.py)

3. Inspect tests:
- [test_controlled_start_smoke.py](/Users/usbdick/Documents/New%20project/synrail/tests/test_controlled_start_smoke.py)
- [test_truth_regressions.py](/Users/usbdick/Documents/New%20project/synrail/tests/test_truth_regressions.py)
- [test_gate_units.py](/Users/usbdick/Documents/New%20project/synrail/tests/test_gate_units.py)
- [test_everyday_benchmark_pack.py](/Users/usbdick/Documents/New%20project/synrail/tests/test_everyday_benchmark_pack.py)
- [test_claim_validation_pack.py](/Users/usbdick/Documents/New%20project/synrail/tests/test_claim_validation_pack.py)
- [test_alpha_evidence_ownership.py](/Users/usbdick/Documents/New%20project/synrail/tests/test_alpha_evidence_ownership.py)

## My current honest assessment

My best-faith assessment of the current branch is:

- the old question “is there even a product wedge here?” is now mostly answered `yes`
- the strongest current wedge is still handoff / continuation honesty
- runtime-backed closure now looks more credible than it did on the last outside pass
- the branch got better by reducing default clutter and tightening trust rules, not by growing new machinery
- the broad everyday story is still not won

So the right external question is no longer:

> is this all just system theater?

The better external question now is:

> is the current wedge strong enough, cheap enough, and independent enough from agent behavior to justify the control stack on at least one bounded everyday contour?

That is the question critics should answer now.
