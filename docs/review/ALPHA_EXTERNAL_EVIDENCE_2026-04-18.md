# Alpha External Evidence 2026-04-18

This document summarizes what the current external alpha runs do and do not prove about `Synrail` relative to a simpler baseline workflow.

It is intentionally narrow.

It does not try to sell the project.

It tries to answer one question:

- after these runs, is there enough evidence to say that `Synrail` can already be worth its cost on its narrow wedge?

## Short Verdict

**Partial yes, now materially stronger on the narrow wedge, but still not fully decisive.**

The current alpha runs are enough to support this weaker claim:

- `Synrail` is no longer just an internal theory artifact.
- On some bounded local workflows, it already shows real product value that a simpler baseline may not match as well.
- That case is now stronger after the second valid handoff success, another pair of accepted Gemini bugfix runs, and a real restore recovery win on the no-commit git contour.
- But the evidence is still mixed, because operator tax remains visible and restore is not yet validated across every workspace contour.

So the honest current verdict is:

- **promising wedge signal**
- **not yet a clear overall baseline win**
- **worth continued investment on the narrow local lane**
- **not yet justified for broad expansion**

## What The Runs Already Show

### 1. Happy-path closure is real, not hypothetical

Runs [003](/Users/usbdick/Documents/New%20project/synrail/fixtures/alpha_external_run_003/REPORT.md), [005](/Users/usbdick/Documents/New%20project/synrail/fixtures/alpha_external_run_005/REPORT.md), [006](/Users/usbdick/Documents/New%20project/synrail/fixtures/alpha_external_run_006/REPORT.md), [008](/Users/usbdick/Documents/New%20project/synrail/fixtures/alpha_external_run_008/REPORT.md), [010](/Users/usbdick/Documents/New%20project/synrail/fixtures/alpha_external_run_010/REPORT.md), [013](/Users/usbdick/Documents/New%20project/synrail/fixtures/alpha_external_run_013/REPORT.md), [015](/Users/usbdick/Documents/New%20project/synrail/fixtures/alpha_external_run_015/REPORT.md), [016](/Users/usbdick/Documents/New%20project/synrail/fixtures/alpha_external_run_016/REPORT.md), [017](/Users/usbdick/Documents/New%20project/synrail/fixtures/alpha_external_run_017/REPORT.md), [018](/Users/usbdick/Documents/New%20project/synrail/fixtures/alpha_external_run_018/REPORT.md), [021c](/Users/usbdick/Documents/New%20project/synrail/fixtures/alpha_external_run_021c/REPORT.md), [021d](/Users/usbdick/Documents/New%20project/synrail/fixtures/alpha_external_run_021d/REPORT.md), [021e](/Users/usbdick/Documents/New%20project/synrail/fixtures/alpha_external_run_021e/REPORT.md), [022](/Users/usbdick/Documents/New%20project/synrail/fixtures/alpha_external_run_022/REPORT.md), [023](/Users/usbdick/Documents/New%20project/synrail/fixtures/alpha_external_run_023/REPORT.md), [024](/Users/usbdick/Documents/New%20project/synrail/fixtures/alpha_external_run_024/REPORT.md), and [025](/Users/usbdick/Documents/New%20project/synrail/fixtures/alpha_external_run_025/REPORT.md) reached `Accepted` on real agent-driven loops.

That matters because it means:

- agents can enter the governed contour
- produce proof artifacts
- and reach accepted closure without a human hand-writing the result

This is enough to say the kernel is operational on a real bounded local path.

### 2. Handoff is a genuinely strong product signal

Runs [008](/Users/usbdick/Documents/New%20project/synrail/fixtures/alpha_external_run_008/REPORT.md) and [018](/Users/usbdick/Documents/New%20project/synrail/fixtures/alpha_external_run_018/REPORT.md) are now the strongest positive signals so far.

A second operator inherited an already-started, non-green run and still:

- oriented on `.synrail`
- understood the active task
- verified the changed surface
- completed the proof
- reached `Accepted`

This is a real wedge candidate because the baseline alternative is usually much weaker here:

- chat memory
- ad hoc notes
- or no structured continuation at all

The second positive handoff matters because it reduces the chance that run [008](/Users/usbdick/Documents/New%20project/synrail/fixtures/alpha_external_run_008/REPORT.md) was just a lucky one-off.

So on **continuation / handoff**, `Synrail` already looks materially stronger than baseline in the current Gemini-side evidence.

### 3. False-green did not reproduce in the tested bug-fix contour

Runs [006](/Users/usbdick/Documents/New%20project/synrail/fixtures/alpha_external_run_006/REPORT.md), [013](/Users/usbdick/Documents/New%20project/synrail/fixtures/alpha_external_run_013/REPORT.md), and [017](/Users/usbdick/Documents/New%20project/synrail/fixtures/alpha_external_run_017/REPORT.md) all add positive bug-fix closure evidence.

The agent made the minimal correct fix.

`Synrail` accepted it.

The hidden oracle also passed.

This does **not** prove that false-green protection is solved in general.

But it does show:

- the proof path is not obviously fake
- the current contour can survive multiple bounded bug-fix slices without collapsing into empty ceremony

### 4. Proof hardening looks materially better than in the early runs

Runs [010](/Users/usbdick/Documents/New%20project/synrail/fixtures/alpha_external_run_010/REPORT.md) and [016](/Users/usbdick/Documents/New%20project/synrail/fixtures/alpha_external_run_016/REPORT.md) are the clearest signals here.

They do **not** prove full proof independence.

But they do show that accepted readback is being pushed toward:

- line-level observation
- concrete test output
- real surface description

rather than simply letting narrative self-description glide through untouched.

### 5. The system is now strong enough to reveal real product bugs, not just harness noise

Runs [007](/Users/usbdick/Documents/New%20project/synrail/fixtures/alpha_external_run_007/REPORT.md), [011b](/Users/usbdick/Documents/New%20project/synrail/fixtures/alpha_external_run_011b/REPORT.md), [014](/Users/usbdick/Documents/New%20project/synrail/fixtures/alpha_external_run_014/REPORT.md), [014c](/Users/usbdick/Documents/New%20project/synrail/fixtures/alpha_external_run_014c/REPORT.md), [014d](/Users/usbdick/Documents/New%20project/synrail/fixtures/alpha_external_run_014d/REPORT.md), and [014e](/Users/usbdick/Documents/New%20project/synrail/fixtures/alpha_external_run_014e/REPORT.md) are especially important.

They found a core product failure:

- `save`
- `confirm-restore`
- `restore`

Run [007](/Users/usbdick/Documents/New%20project/synrail/fixtures/alpha_external_run_007/REPORT.md) showed that the old restore contour failed completely.

Runs [011b](/Users/usbdick/Documents/New%20project/synrail/fixtures/alpha_external_run_011b/REPORT.md), [014](/Users/usbdick/Documents/New%20project/synrail/fixtures/alpha_external_run_014/REPORT.md), [014c](/Users/usbdick/Documents/New%20project/synrail/fixtures/alpha_external_run_014c/REPORT.md), [014d](/Users/usbdick/Documents/New%20project/synrail/fixtures/alpha_external_run_014d/REPORT.md), and [014e](/Users/usbdick/Documents/New%20project/synrail/fixtures/alpha_external_run_014e/REPORT.md) sharpened that diagnosis:

- pre-run `save` now arms a fallback successfully
- deployed `confirm-restore` now succeeds on the corrected build
- `014c` showed that `restore` could still claim `RESTORED` while the workspace remained broken
- `014d` fixed that honesty bug: for a no-commit workspace it now fails explicitly with `workspace_snapshot.type = "none"` and `RESTORE_FAILED`
- `014e` closes that specific gap: on the same no-commit git contour, `workspace_snapshot.type = "file_copy"` and restore now genuinely recovers the broken file

That is bad news operationally.

But as evidence, it is actually useful:

- the alpha process is now surfacing real kernel weaknesses
- not merely speculative critique or style complaints

That means the testing program is already doing valuable work.

### 6. Open-ended project orientation is now partially governed, but still not literally `synrail`-first

Runs [019](/Users/usbdick/Documents/New%20project/synrail/fixtures/alpha_external_run_019/REPORT.md) and [020](/Users/usbdick/Documents/New%20project/synrail/fixtures/alpha_external_run_020/REPORT.md) give the first direct evidence on this contour.

They show that the situation is better than the earlier anecdotal fear:

- both agents stayed inside the governed project root
- both agents recovered the previous accepted run from `.synrail` artifacts
- neither needed a sibling-probe archaeology pass to answer the question

But they also show the remaining gap clearly:

- Gemini still over-explored after initial orientation, including unnecessary database/schema probing
- Claude was cleaner, but even Claude did not literally run `synrail` or `synrail status`; it read `.synrail` artifacts directly

So the honest current claim is:

- governed project recall is materially better
- explicit CLI-first orientation is still not yet learned strongly enough

Runs [019b](/Users/usbdick/Documents/New%20project/synrail/fixtures/alpha_external_run_019b/REPORT.md) and [020b](/Users/usbdick/Documents/New%20project/synrail/fixtures/alpha_external_run_020b/REPORT.md) retest that same contour after the orientation-guidance wording fix.

They split the result by lane:

- Gemini still over-explores, even after explicitly mentioning Synrail
- Claude now literally starts with `synrail`, then stays read-only and summarizes the governed state correctly

So the updated honest claim is:

- the fix is validated on the Claude lane
- the Gemini lane still needs stronger shaping than text-only guidance

Run [019c](/Users/usbdick/Documents/New%20project/synrail/fixtures/alpha_external_run_019c/REPORT.md) retests Gemini again after the stronger Gemini-specific tightening.

It improves the picture, but does not fully close it:

- Gemini now stays much closer to the governed state and no longer wanders into database/schema or sibling-probe archaeology
- the saved answer is short and correct
- but the lane still is not as small as Claude `020b`, and the run did not persist a clean `end` / `rc` trace

So the refined claim is:

- Claude now has a clear literal `synrail`-first orientation lane
- Gemini has materially improved orientation discipline
- but Gemini orientation is still not as operationally minimal, and its CLI/harness completion path still looks weaker

## What The Runs Do **Not** Yet Prove

### 1. They do not yet prove that `Synrail` clearly beats the simpler baseline overall

The strongest reasons are runs [007](/Users/usbdick/Documents/New%20project/synrail/fixtures/alpha_external_run_007/REPORT.md) and [011b](/Users/usbdick/Documents/New%20project/synrail/fixtures/alpha_external_run_011b/REPORT.md).

If restore is one of the wedge claims, then a failed restore contour is a direct strike against baseline advantage.

Right now the honest statement is:

- `Synrail` may already beat baseline on continuation/handoff honesty
- and it now has at least one strong external restore win on a previously failing contour
- but it does **not** yet beat baseline convincingly on restore/recovery across all workspace types

### 2. They do not yet prove that operator tax is low enough

Runs [002](/Users/usbdick/Documents/New%20project/synrail/fixtures/alpha_external_run_002/REPORT.md), [009](/Users/usbdick/Documents/New%20project/synrail/fixtures/alpha_external_run_009/REPORT.md), and [015](/Users/usbdick/Documents/New%20project/synrail/fixtures/alpha_external_run_015/REPORT.md) are the clearest counterweights.

On trivial docstring tasks, Gemini still needed multiple proof-oriented loops and remained slower than the simpler baseline.

Runs [003](/Users/usbdick/Documents/New%20project/synrail/fixtures/alpha_external_run_003/REPORT.md), [005](/Users/usbdick/Documents/New%20project/synrail/fixtures/alpha_external_run_005/REPORT.md), [008](/Users/usbdick/Documents/New%20project/synrail/fixtures/alpha_external_run_008/REPORT.md), and [009](/Users/usbdick/Documents/New%20project/synrail/fixtures/alpha_external_run_009/REPORT.md) still show visible ceremony such as:

- `repair-step`
- `check --clean-surface`
- explicit proof shaping

Run [015](/Users/usbdick/Documents/New%20project/synrail/fixtures/alpha_external_run_015/REPORT.md) improves that picture somewhat:

- help surface is smaller
- the visible `--clean-surface` dance dropped out
- but the trivial lane still does not look cheap enough to recommend over baseline

Run [021c](/Users/usbdick/Documents/New%20project/synrail/fixtures/alpha_external_run_021c/REPORT.md) improves the Claude side of that story further:

- the run reached `Accepted` on the current trivial-burden tranche in a single inferred pass
- `observability.json` shows zero repairs and zero rejections
- and the proof pack stayed concrete without visible churn

But even that stronger Claude result is still slower than the simpler baseline on this contour.

Run [021d](/Users/usbdick/Documents/New%20project/synrail/fixtures/alpha_external_run_021d/REPORT.md) adds the missing Gemini-side counterweight:

- on the same build and same trivial prompt, Gemini also reached `Accepted`
- `observability.json` again shows zero repairs and zero rejections
- and the accepted proof pack stayed concrete rather than ballooning

But the caveat matters:

- this positive Gemini result required a live interactive TTY session
- the cleaner headless Gemini lane from [021b](/Users/usbdick/Documents/New%20project/synrail/fixtures/alpha_external_run_021b/REPORT.md) is still broken on this host with `setRawMode EIO`

Run [021e](/Users/usbdick/Documents/New%20project/synrail/fixtures/alpha_external_run_021e/REPORT.md) sharpens that Gemini picture again:

- the same trivial task now also succeeds through an unattended Gemini invocation on the same host
- the run reaches `Accepted` in one pass with zero repairs and zero rejections
- and the elapsed time drops materially relative to the live TTY workaround in `021d`

Run [022](/Users/usbdick/Documents/New%20project/synrail/fixtures/alpha_external_run_022/REPORT.md) strengthens that trivial Gemini picture in a different way:

- the same unattended Gemini lane still reaches `Accepted` in one pass after the new trust-bearing `final_result.status` gate lands
- `.synrail/final_result.json` now carries `status: "PROVEN"` instead of the older decorative `SUCCESS`
- and `bundle.json` explicitly marks `final_result_status` as semantically sufficient, so the new kernel rule has already survived a real agent-driven run rather than only unit tests

So the refined statement is:

- trivial-task tax is getting better on both Claude and Gemini
- the contour is no longer Claude-only
- and Gemini now has a valid unattended success path on this host
- but trivial work is still not a general baseline win, and the lane still has one known-bad older harness shape from `021b`

Run [023](/Users/usbdick/Documents/New%20project/synrail/fixtures/alpha_external_run_023/REPORT.md) adds the first live check after the newer evidence-first cheapening tranche:

- Gemini still reaches `Accepted` in one pass and still emits `final_result.status = "PROVEN"`
- `diff_provenance` is richer than in `022`, because it now includes both `verification_command` and `verification_result`
- but the intended cheapening did not actually fire on this live run: Gemini still omitted `diff_provenance.method`, so `bundle.json` reports `has_structured_runtime_verification = false`
- as a result, both `readback.txt` and `scenario_proof.txt` were still authored and still semantically used, meaning the new waiver path is real in the kernel but not yet naturally realized by the live agent contour

So the refined statement becomes:

- the new evidence-first kernel is surviving real Gemini runs
- but the real agent behavior has not caught up fully enough to cash in the cheaper proof path yet
- which means the next fix is no longer “make the kernel allow the cheaper contour,” but “make live agents reliably complete the stronger structured provenance record”

Run [024](/Users/usbdick/Documents/New%20project/synrail/fixtures/alpha_external_run_024/REPORT.md) retests that exact question after the `db192c4` tranche that can infer `diff_provenance.method` from a strong enough direct-observation record:

- Gemini again reaches `Accepted` and again emits `final_result.status = "PROVEN"`
- but `bundle.json` still reports `normalized_method = ""` and `method_inferred = false`
- the new refinement is important: the remaining gap is no longer just one omitted `method` token; the live agent still authors only a thin direct-observation record with `changed_file`, `verification_command`, and `verification_result`, leaving out the changed-line/context fields needed for the stronger inferred contour
- so the waiver still does not materialize, and both `readback.txt` and `scenario_proof.txt` remain semantically active after a second `synrail check`

So the refined statement becomes:

- the newer inference tranche is safe on a real unattended Gemini contour
- but the next cheapening win now depends on stronger live provenance shaping, not on another missing kernel affordance
- which means the next fix should teach agents to author richer direct-observation provenance, or else let the kernel cash in stronger combinations like `git_diff + verification_result` more directly

Run [025](/Users/usbdick/Documents/New%20project/synrail/fixtures/alpha_external_run_025/REPORT.md) is the first live check after the new starter-shaping tranche:

- Gemini again reaches `Accepted` and again emits `final_result.status = "PROVEN"`
- this time the stronger contour really materializes: `bundle.json` reports `normalized_method = "direct_file_observation"`, `method_inferred = true`, and `has_structured_runtime_verification = true`
- the run does that without any `git_diff`; the accepted proof is carried by a structured direct-observation record with `added_line`, `verification_command`, and `verification_result`
- it also gets materially cheaper: one check, zero repairs, zero rejections, and roughly `0.4` minutes total, which is the closest Synrail has come yet to the `0.3` baseline estimate on this trivial contour
- but it is still not a full waiver win, because `readback.txt` and `scenario_proof.txt` are still authored and semantically active rather than disappearing into a purely structured evidence path

So the refined statement becomes:

- the live Gemini lane can now realize strong runtime corroboration, not just survive the kernel changes
- the cheaper direct-observation contour is no longer only theoretical; it is materially present on a real unattended run
- the remaining gap is narrower now: not “can live Gemini produce strong structured provenance?”, but “can that contour fully displace the prose proof surfaces?”

So the honest updated statement is:

- trivial-task tax is getting better
- the Claude lane now looks materially cleaner than earlier runs
- Gemini can also complete the cheapened contour successfully
- the new trust-bearing status semantics already generalize to a real unattended Gemini contour
- but trivial work is still not a general baseline win, and one older Gemini headless invocation shape is still broken enough to weaken the comparison quality

So we cannot yet say:

- first-run cheapness is good enough
- commands/artifacts consistently feel worth their cost

### 3. They do not yet prove full proof independence

Run [005](/Users/usbdick/Documents/New%20project/synrail/fixtures/alpha_external_run_005/REPORT.md) still passed with readback that was somewhat narrative-heavy.

That means the system is better than before, but still not fully independent of structured self-description.

Runs [010](/Users/usbdick/Documents/New%20project/synrail/fixtures/alpha_external_run_010/REPORT.md) and [016](/Users/usbdick/Documents/New%20project/synrail/fixtures/alpha_external_run_016/REPORT.md) make that picture better, but not solved.

So the current claim must stay modest:

- proof quality is improving
- but proof independence is not yet strong enough to call this solved

### 4. They do not yet isolate product value perfectly from harness issues

Runs [001](/Users/usbdick/Documents/New%20project/synrail/fixtures/alpha_external_run_001/REPORT.md), [004](/Users/usbdick/Documents/New%20project/synrail/fixtures/alpha_external_run_004/REPORT.md), and [021b](/Users/usbdick/Documents/New%20project/synrail/fixtures/alpha_external_run_021b/REPORT.md) were dominated by harness problems, not product behavior.

That means some of the current evidence is still noisy.

Run [021b](/Users/usbdick/Documents/New%20project/synrail/fixtures/alpha_external_run_021b/REPORT.md) usefully narrows that noise:

- Gemini non-interactive mode on this host crashes with `setRawMode EIO`
- the failure happens before `synrail start` or `synrail check`
- and a PTY-wrapped smoke retry still timed out without producing output

So the current Gemini trivial-lane regression on this server should be treated as harness-invalid rather than as negative Synrail product evidence.

Runs [021d](/Users/usbdick/Documents/New%20project/synrail/fixtures/alpha_external_run_021d/REPORT.md), [021e](/Users/usbdick/Documents/New%20project/synrail/fixtures/alpha_external_run_021e/REPORT.md), and [022](/Users/usbdick/Documents/New%20project/synrail/fixtures/alpha_external_run_022/REPORT.md) sharpen that interpretation further:

- the same trivial task succeeds both through a live interactive TTY session and through an unattended headless-safe invocation
- the positive `Synrail` result therefore coexists with the broken older `021b` invocation
- and after the latest status-semantics tranche, the unattended Gemini lane still succeeds while emitting a trust-bearing `PROVEN` final result
- which means the remaining problem is now more clearly a Gemini harness-shape seam than a direct product failure on this contour

### 5. They do not yet prove a literal `synrail` CLI-first entry ritual for open-ended orientation prompts

Runs [019](/Users/usbdick/Documents/New%20project/synrail/fixtures/alpha_external_run_019/REPORT.md) and [020](/Users/usbdick/Documents/New%20project/synrail/fixtures/alpha_external_run_020/REPORT.md) are encouraging, but they stop short of the strict ideal.

Both original runs used governed artifacts.

The retests refine that picture:

- [020b](/Users/usbdick/Documents/New%20project/synrail/fixtures/alpha_external_run_020b/REPORT.md) does provide clean evidence of a literal `synrail`-first start on Claude
- [019b](/Users/usbdick/Documents/New%20project/synrail/fixtures/alpha_external_run_019b/REPORT.md) shows that Gemini still does not reliably collapse orientation into that same small loop
- [019c](/Users/usbdick/Documents/New%20project/synrail/fixtures/alpha_external_run_019c/REPORT.md) shows that Gemini can be nudged into a materially narrower governed summary, but still not into the same tiny, cleanly persisted loop

That means the project is improving on recall and context recovery, but the operator-facing entry habit is still only partially internalized across agents.

## Per-Run Contribution

| Run | Contribution | How much it helps the case |
| --- | --- | --- |
| [001](/Users/usbdick/Documents/New%20project/synrail/fixtures/alpha_external_run_001/REPORT.md) | Harness failure only | Little direct product evidence |
| [002](/Users/usbdick/Documents/New%20project/synrail/fixtures/alpha_external_run_002/REPORT.md) | Shows trivial-task overhead clearly | Useful negative evidence |
| [003](/Users/usbdick/Documents/New%20project/synrail/fixtures/alpha_external_run_003/REPORT.md) | Shows happy-path closure on Claude lane | Moderate positive evidence |
| [004](/Users/usbdick/Documents/New%20project/synrail/fixtures/alpha_external_run_004/REPORT.md) | Invalid false-green probe | Not counted as product evidence |
| [005](/Users/usbdick/Documents/New%20project/synrail/fixtures/alpha_external_run_005/REPORT.md) | Accepted Gemini run + hidden oracle pass + parroting seam found | Strong mixed evidence |
| [006](/Users/usbdick/Documents/New%20project/synrail/fixtures/alpha_external_run_006/REPORT.md) | Replacement false-green probe passed honestly | Moderate positive evidence |
| [007](/Users/usbdick/Documents/New%20project/synrail/fixtures/alpha_external_run_007/REPORT.md) | Restore contour failed | Strong negative evidence |
| [008](/Users/usbdick/Documents/New%20project/synrail/fixtures/alpha_external_run_008/REPORT.md) | Handoff/continuation succeeded | Strong positive evidence |
| [009](/Users/usbdick/Documents/New%20project/synrail/fixtures/alpha_external_run_009/REPORT.md) | Trivial-task overhead is still heavy in live Gemini flow | Useful negative evidence |
| [010](/Users/usbdick/Documents/New%20project/synrail/fixtures/alpha_external_run_010/REPORT.md) | Proof hardening forced a more concrete accepted readback | Moderate positive evidence |
| [011b](/Users/usbdick/Documents/New%20project/synrail/fixtures/alpha_external_run_011b/REPORT.md) | Pre-run save improved, but restore still did not recover the broken state | Strong negative evidence |
| [012](/Users/usbdick/Documents/New%20project/synrail/fixtures/alpha_external_run_012/REPORT.md) | Claude-first handoff probe blocked by shell approval gate | Harness evidence only |
| [012b](/Users/usbdick/Documents/New%20project/synrail/fixtures/alpha_external_run_012b/REPORT.md) | Claude-first handoff rerun blocked by root bypass restriction | Harness evidence only |
| [013](/Users/usbdick/Documents/New%20project/synrail/fixtures/alpha_external_run_013/REPORT.md) | Independent Gemini bugfix reached accepted closure | Moderate positive evidence |
| [014](/Users/usbdick/Documents/New%20project/synrail/fixtures/alpha_external_run_014/REPORT.md) | Restore round-trip still failed even after pre-run snapshot arming | Strong negative evidence |
| [014c](/Users/usbdick/Documents/New%20project/synrail/fixtures/alpha_external_run_014c/REPORT.md) | Current deployed build still reports RESTORED while leaving the workspace broken | Strong negative evidence |
| [014d](/Users/usbdick/Documents/New%20project/synrail/fixtures/alpha_external_run_014d/REPORT.md) | Latest build now fails restore honestly on a no-commit workspace instead of reporting false success | Mixed but useful evidence |
| [014e](/Users/usbdick/Documents/New%20project/synrail/fixtures/alpha_external_run_014e/REPORT.md) | File-copy fallback restores the broken file and returns tests to green on the no-commit git contour | Strong positive evidence |
| [015](/Users/usbdick/Documents/New%20project/synrail/fixtures/alpha_external_run_015/REPORT.md) | Trivial lane improved, but still slower/heavier than baseline | Mixed evidence |
| [016](/Users/usbdick/Documents/New%20project/synrail/fixtures/alpha_external_run_016/REPORT.md) | Proof-heavy accepted run with more observational readback | Moderate positive evidence |
| [017](/Users/usbdick/Documents/New%20project/synrail/fixtures/alpha_external_run_017/REPORT.md) | Another fresh accepted bugfix on a distinct contour | Moderate positive evidence |
| [018](/Users/usbdick/Documents/New%20project/synrail/fixtures/alpha_external_run_018/REPORT.md) | Second valid handoff success | Strong positive evidence |
| [019](/Users/usbdick/Documents/New%20project/synrail/fixtures/alpha_external_run_019/REPORT.md) | Gemini can orient on a governed project without sibling drift, but still over-explores and does not visibly start with `synrail` | Mixed evidence |
| [020](/Users/usbdick/Documents/New%20project/synrail/fixtures/alpha_external_run_020/REPORT.md) | Claude can answer accurately from `.synrail` artifacts in a short read-only run, but still without a literal CLI-first entry | Moderate positive evidence |
| [019b](/Users/usbdick/Documents/New%20project/synrail/fixtures/alpha_external_run_019b/REPORT.md) | Gemini retest still over-explores even after the orientation guidance wording fix | Mixed evidence |
| [020b](/Users/usbdick/Documents/New%20project/synrail/fixtures/alpha_external_run_020b/REPORT.md) | Claude retest now literally starts with `synrail`, giving the first clean CLI-first orientation signal | Strong positive evidence |
| [019c](/Users/usbdick/Documents/New%20project/synrail/fixtures/alpha_external_run_019c/REPORT.md) | Gemini retest is materially narrower than `019b`, but still not as small or as cleanly persisted as the Claude lane | Moderate mixed-positive evidence |
| [021b](/Users/usbdick/Documents/New%20project/synrail/fixtures/alpha_external_run_021b/REPORT.md) | Isolates the current Gemini server regression as a `setRawMode EIO` harness failure before any Synrail step begins | Harness evidence only |
| [021c](/Users/usbdick/Documents/New%20project/synrail/fixtures/alpha_external_run_021c/REPORT.md) | Cleanest current trivial Claude retest: one inferred accepted pass, no repairs, no visible trust dance | Moderate positive evidence |
| [021d](/Users/usbdick/Documents/New%20project/synrail/fixtures/alpha_external_run_021d/REPORT.md) | Valid Gemini trivial retest through live TTY: accepted in one pass, but still much slower than baseline and weaker operationally than a clean headless lane | Moderate mixed-positive evidence |
| [021e](/Users/usbdick/Documents/New%20project/synrail/fixtures/alpha_external_run_021e/REPORT.md) | Valid unattended Gemini trivial retest: accepted in one pass on the same host, showing that a headless-safe Gemini path exists even though trivial work is still slower than baseline | Strong moderate positive evidence |
| [022](/Users/usbdick/Documents/New%20project/synrail/fixtures/alpha_external_run_022/REPORT.md) | Valid unattended Gemini retest after the new trust-bearing status tranche: accepted in one pass with `final_result.status = PROVEN`, showing that the new kernel semantics already hold on a real agent-driven contour | Strong moderate positive evidence |
| [023](/Users/usbdick/Documents/New%20project/synrail/fixtures/alpha_external_run_023/REPORT.md) | Valid unattended Gemini retest after the readback/scenario cheapening tranche: accepted in one pass with stronger `diff_provenance`, but the agent still filled both prose proof surfaces because the structured runtime record was not yet complete enough to trigger the waiver path | Strong mixed-positive evidence |
| [024](/Users/usbdick/Documents/New%20project/synrail/fixtures/alpha_external_run_024/REPORT.md) | Valid unattended Gemini retest after inferred-method normalization: accepted again, but the agent still authored too-thin direct provenance for inference to fire, so the waiver contour still did not materialize | Strong mixed-positive evidence |
| [025](/Users/usbdick/Documents/New%20project/synrail/fixtures/alpha_external_run_025/REPORT.md) | Valid unattended Gemini retest after direct-provenance starter shaping: accepted in one pass with inferred method and strong runtime verification, bringing the trivial lane close to baseline cost even though the prose proof surfaces still remain | Strong positive evidence |

## Current Best Honest Claim Against Baseline

Today the most defensible claim is:

- `Synrail` already looks **materially more useful than baseline** on **handoff / continuation honesty**.
- It also looks **increasingly credible** on bounded accepted closure for local bug-fix tasks.
- The trivial lane now looks cleaner than it did earlier on both Claude and Gemini, with one-pass accepted retests on the current build, an unattended Gemini success path, and now one strong-runtime-verification trivial win that comes close to baseline cost.
- And it now has a real restore win on the no-commit git contour via `file_copy`.
- But it is **not yet clearly better than baseline overall**, because trivial-task operator tax is still too visible, one older Gemini harness path is still broken on this host, and restore is not yet proven across every workspace type.

That is enough to justify:

- continuing the alpha program
- fixing the current restore bug as a top priority
- tightening proof quality and reducing ceremony

It is **not** enough to justify:

- broad expansion
- a wide platform story
- or a claim that `Synrail` has already won the baseline comparison on its whole wedge

## What Is Already Recorded In The Repo

The evidence is already stored in these run reports:

- [001](/Users/usbdick/Documents/New%20project/synrail/fixtures/alpha_external_run_001/REPORT.md)
- [002](/Users/usbdick/Documents/New%20project/synrail/fixtures/alpha_external_run_002/REPORT.md)
- [003](/Users/usbdick/Documents/New%20project/synrail/fixtures/alpha_external_run_003/REPORT.md)
- [004](/Users/usbdick/Documents/New%20project/synrail/fixtures/alpha_external_run_004/REPORT.md)
- [005](/Users/usbdick/Documents/New%20project/synrail/fixtures/alpha_external_run_005/REPORT.md)
- [006](/Users/usbdick/Documents/New%20project/synrail/fixtures/alpha_external_run_006/REPORT.md)
- [007](/Users/usbdick/Documents/New%20project/synrail/fixtures/alpha_external_run_007/REPORT.md)
- [008](/Users/usbdick/Documents/New%20project/synrail/fixtures/alpha_external_run_008/REPORT.md)
- [009](/Users/usbdick/Documents/New%20project/synrail/fixtures/alpha_external_run_009/REPORT.md)
- [010](/Users/usbdick/Documents/New%20project/synrail/fixtures/alpha_external_run_010/REPORT.md)
- [011](/Users/usbdick/Documents/New%20project/synrail/fixtures/alpha_external_run_011/REPORT.md)
- [011b](/Users/usbdick/Documents/New%20project/synrail/fixtures/alpha_external_run_011b/REPORT.md)
- [012](/Users/usbdick/Documents/New%20project/synrail/fixtures/alpha_external_run_012/REPORT.md)
- [012b](/Users/usbdick/Documents/New%20project/synrail/fixtures/alpha_external_run_012b/REPORT.md)
- [013](/Users/usbdick/Documents/New%20project/synrail/fixtures/alpha_external_run_013/REPORT.md)
- [014](/Users/usbdick/Documents/New%20project/synrail/fixtures/alpha_external_run_014/REPORT.md)
- [014b](/Users/usbdick/Documents/New%20project/synrail/fixtures/alpha_external_run_014b/REPORT.md)
- [014c](/Users/usbdick/Documents/New%20project/synrail/fixtures/alpha_external_run_014c/REPORT.md)
- [014d](/Users/usbdick/Documents/New%20project/synrail/fixtures/alpha_external_run_014d/REPORT.md)
- [014e](/Users/usbdick/Documents/New%20project/synrail/fixtures/alpha_external_run_014e/REPORT.md)
- [015](/Users/usbdick/Documents/New%20project/synrail/fixtures/alpha_external_run_015/REPORT.md)
- [016](/Users/usbdick/Documents/New%20project/synrail/fixtures/alpha_external_run_016/REPORT.md)
- [017](/Users/usbdick/Documents/New%20project/synrail/fixtures/alpha_external_run_017/REPORT.md)
- [018](/Users/usbdick/Documents/New%20project/synrail/fixtures/alpha_external_run_018/REPORT.md)
- [019](/Users/usbdick/Documents/New%20project/synrail/fixtures/alpha_external_run_019/REPORT.md)
- [020](/Users/usbdick/Documents/New%20project/synrail/fixtures/alpha_external_run_020/REPORT.md)
- [019b](/Users/usbdick/Documents/New%20project/synrail/fixtures/alpha_external_run_019b/REPORT.md)
- [020b](/Users/usbdick/Documents/New%20project/synrail/fixtures/alpha_external_run_020b/REPORT.md)
- [021b](/Users/usbdick/Documents/New%20project/synrail/fixtures/alpha_external_run_021b/REPORT.md)
- [021c](/Users/usbdick/Documents/New%20project/synrail/fixtures/alpha_external_run_021c/REPORT.md)
- [021d](/Users/usbdick/Documents/New%20project/synrail/fixtures/alpha_external_run_021d/REPORT.md)
- [021e](/Users/usbdick/Documents/New%20project/synrail/fixtures/alpha_external_run_021e/REPORT.md)
- [022](/Users/usbdick/Documents/New%20project/synrail/fixtures/alpha_external_run_022/REPORT.md)
- [023](/Users/usbdick/Documents/New%20project/synrail/fixtures/alpha_external_run_023/REPORT.md)
- [024](/Users/usbdick/Documents/New%20project/synrail/fixtures/alpha_external_run_024/REPORT.md)
- [025](/Users/usbdick/Documents/New%20project/synrail/fixtures/alpha_external_run_025/REPORT.md)

There was also already a generic scoring template here:

- [ALPHA_SIGNAL_SCORECARD_001.md](/Users/usbdick/Documents/New%20project/synrail/docs/review/ALPHA_SIGNAL_SCORECARD_001.md)

There is now also a compact ledger here:

- [ALPHA_LEDGER_001.md](/Users/usbdick/Documents/New%20project/synrail/docs/review/ALPHA_LEDGER_001.md)

And a reusable report template here:

- [ALPHA_RUN_REPORT_TEMPLATE_002.md](/Users/usbdick/Documents/New%20project/synrail/docs/review/ALPHA_RUN_REPORT_TEMPLATE_002.md)

What was missing was a single synthesis document that says, in plain language, what these runs currently prove.

This file is that synthesis.

## Bottom Line

If the question is:

- **"Do the current alpha tests show that `Synrail` may be worth its cost?"**

the answer is:

- **yes, partially**

If the question is:

- **"Do they already prove that `Synrail` is clearly better than the simpler baseline on its wedge?"**

the answer is:

- **not yet**

The strongest positive signal is still handoff, but restore now has a real positive external recovery signal too.

The strongest negative signal is no longer the old false-success restore bug; the clearest remaining negative signal is now trivial-task operator tax, while restore still needs broader contour coverage and orientation still needs that smaller CLI-first loop to generalize beyond the Claude lane. The new wrinkle from `021b`, `021d`, `021e`, `022`, `023`, `024`, and `025` is that the Gemini trivial lane on this host is now split even more precisely: one older invocation shape is harness-broken (`setRawMode EIO`), but a headless-safe unattended Gemini path can complete the contour honestly and emit the trust-bearing `PROVEN` status under the new kernel gate. The newer `025` run is a real step forward: live Gemini now naturally reaches inferred direct-observation method and strong runtime verification in a single pass. The remaining gap is narrower than before, but it is still there: the prose proof surfaces are still being authored instead of disappearing behind a fully realized evidence-only contour, and trivial-task cost is only near-baseline rather than clearly better than baseline.

That is exactly enough clarity to justify the next round of focused fixes.
