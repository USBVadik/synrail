# Alpha Ledger 001

This ledger is the compact decision table for external alpha runs.

It complements, not replaces:

- the per-run `REPORT.md`
- the synthesis document in [ALPHA_EXTERNAL_EVIDENCE_2026-04-18.md](/Users/usbdick/Documents/New%20project/synrail/docs/review/ALPHA_EXTERNAL_EVIDENCE_2026-04-18.md)
- the generic review scorecard in [ALPHA_SIGNAL_SCORECARD_001.md](/Users/usbdick/Documents/New%20project/synrail/docs/review/ALPHA_SIGNAL_SCORECARD_001.md)

The purpose of this file is simple:

- show where `Synrail` already looks materially stronger than baseline
- show where baseline is still good enough
- show where `Synrail` is currently losing because of product, harness, or operator-tax issues

## How To Read It

- Baseline fields are still **estimates** unless a real side-by-side baseline replay was run.
- `Delta time` is `synrail_minutes_actual - baseline_minutes_estimate`.
  - negative means `Synrail` looked faster
  - positive means `Synrail` looked slower
- `Delta loops` is `synrail_check_count - baseline_retry_count_estimate`.
  - negative means `Synrail` looked lighter on loop count
  - positive means `Synrail` looked heavier
- `Delta recovery` is narrative because restore/re-entry value is not reducible to one number yet.

## Summary Table

| Run | Agent | Task class | Final outcome | Failure owner | Reuse tomorrow | Wedge fit | Baseline min est | Synrail min | Delta time | Baseline retries est | Synrail checks | Delta loops |
| --- | --- | --- | --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| [001](/Users/usbdick/Documents/New%20project/synrail/fixtures/alpha_external_run_001/REPORT.md) | Claude Code | trivial / additive_change | BLOCKED | harness | no | low | 0.3 | 0.4 | +0.1 | 0 | 0 | 0 |
| [002](/Users/usbdick/Documents/New%20project/synrail/fixtures/alpha_external_run_002/REPORT.md) | Gemini CLI | trivial / additive_change | NOT_ACCEPTED | product | no | low | 0.3 | 0.8 | +0.5 | 0 | 4 | +4 |
| [003](/Users/usbdick/Documents/New%20project/synrail/fixtures/alpha_external_run_003/REPORT.md) | Claude Code | trivial / additive_change | ACCEPTED | mixed | unclear | low | 0.3 | 0.8 | +0.5 | 0 | 2 | +2 |
| [004](/Users/usbdick/Documents/New%20project/synrail/fixtures/alpha_external_run_004/REPORT.md) | Claude Code | bugfix | INVALID | harness | no | medium | n/a | 2.3 | n/a | n/a | 0 | n/a |
| [005](/Users/usbdick/Documents/New%20project/synrail/fixtures/alpha_external_run_005/REPORT.md) | Gemini CLI | bugfix / proof_heavy | ACCEPTED | mixed | unclear | high | 1.0 | 1.5 | +0.5 | 1 | 3 | +2 |
| [006](/Users/usbdick/Documents/New%20project/synrail/fixtures/alpha_external_run_006/REPORT.md) | Claude Code | bugfix | ACCEPTED | harness | unclear | high | 1.5 | 2.1 | +0.6 | 1 | 1 | 0 |
| [007](/Users/usbdick/Documents/New%20project/synrail/fixtures/alpha_external_run_007/REPORT.md) | Codex manual | restore | RESTORE_FAILED | product | no | high | 0.3 | 0.7 | +0.4 | 1 | 1 | 0 |
| [008](/Users/usbdick/Documents/New%20project/synrail/fixtures/alpha_external_run_008/REPORT.md) | Gemini CLI | handoff | ACCEPTED | none | yes | high | 2.0 | 1.4 | -0.6 | 3 | 3 | 0 |
| [009](/Users/usbdick/Documents/New%20project/synrail/fixtures/alpha_external_run_009/REPORT.md) | Gemini CLI | trivial / additive_change | DOCTOR_BLOCKED | product | no | low | 0.3 | 1.0 | +0.7 | 0 | 4 | +4 |
| [010](/Users/usbdick/Documents/New%20project/synrail/fixtures/alpha_external_run_010/REPORT.md) | Gemini CLI | bugfix / proof_heavy | ACCEPTED | none | yes | high | 1.0 | 1.0 | 0.0 | 1 | 2 | +1 |
| [011](/Users/usbdick/Documents/New%20project/synrail/fixtures/alpha_external_run_011/REPORT.md) | Codex manual | restore | INVALID_BASELINE | operator | unclear | high | n/a | 0.2 | n/a | n/a | 0 | n/a |
| [011b](/Users/usbdick/Documents/New%20project/synrail/fixtures/alpha_external_run_011b/REPORT.md) | Codex manual | restore | RESTORE_REPORTED_BUT_STATE_NOT_RECOVERED | product | no | high | 0.3 | 0.0 | -0.3 | 0 | 0 | 0 |
| [012](/Users/usbdick/Documents/New%20project/synrail/fixtures/alpha_external_run_012/REPORT.md) | Claude Code + Gemini CLI | handoff | INVALID_HARNESS_APPROVAL_GATE | harness | no | high | n/a | 0.0 | n/a | n/a | 0 | n/a |
| [012b](/Users/usbdick/Documents/New%20project/synrail/fixtures/alpha_external_run_012b/REPORT.md) | Claude Code + Gemini CLI | handoff | INVALID_HARNESS_ROOT_BYPASS_BLOCKED | harness | no | high | n/a | 0.0 | n/a | n/a | 0 | n/a |
| [013](/Users/usbdick/Documents/New%20project/synrail/fixtures/alpha_external_run_013/REPORT.md) | Gemini CLI | bugfix | ACCEPTED | none | yes | high | 0.8 | 1.0 | +0.2 | 1 | 1 | 0 |
| [014](/Users/usbdick/Documents/New%20project/synrail/fixtures/alpha_external_run_014/REPORT.md) | Codex manual | restore | RESTORE_REPORTED_BUT_STATE_NOT_RECOVERED | product | no | high | 0.3 | 0.0 | -0.3 | 0 | 0 | 0 |
| [014b](/Users/usbdick/Documents/New%20project/synrail/fixtures/alpha_external_run_014b/REPORT.md) | Codex manual | restore | PARTIAL_DIAGNOSTIC_ONLY | operator | unclear | high | n/a | 0.0 | n/a | n/a | 0 | n/a |
| [014c](/Users/usbdick/Documents/New%20project/synrail/fixtures/alpha_external_run_014c/REPORT.md) | Codex manual | restore | RESTORE_REPORTED_BUT_WORKSPACE_NOT_RESTORED | product | no | high | 0.3 | 0.0 | -0.3 | 0 | 0 | 0 |
| [014d](/Users/usbdick/Documents/New%20project/synrail/fixtures/alpha_external_run_014d/REPORT.md) | Codex manual | restore | RESTORE_FAILED_HONESTLY_FOR_UNSUPPORTED_WORKSPACE | product | unclear | high | 0.3 | 0.0 | -0.3 | 0 | 0 | 0 |
| [014e](/Users/usbdick/Documents/New%20project/synrail/fixtures/alpha_external_run_014e/REPORT.md) | Codex manual | restore | RESTORED | none | yes | high | 0.3 | 0.0 | -0.3 | 0 | 0 | 0 |
| [015](/Users/usbdick/Documents/New%20project/synrail/fixtures/alpha_external_run_015/REPORT.md) | Gemini CLI | trivial / additive_change | ACCEPTED | product | no | low | 0.3 | 1.0 | +0.7 | 0 | 2 | +2 |
| [016](/Users/usbdick/Documents/New%20project/synrail/fixtures/alpha_external_run_016/REPORT.md) | Gemini CLI | bugfix / proof_heavy | ACCEPTED | mixed | yes | high | 1.0 | 1.2 | +0.2 | 1 | 2 | +1 |
| [017](/Users/usbdick/Documents/New%20project/synrail/fixtures/alpha_external_run_017/REPORT.md) | Gemini CLI | bugfix | ACCEPTED | none | yes | high | 0.8 | 1.0 | +0.2 | 1 | 1 | 0 |
| [018](/Users/usbdick/Documents/New%20project/synrail/fixtures/alpha_external_run_018/REPORT.md) | Gemini CLI + Gemini CLI | handoff | ACCEPTED | none | yes | high | 2.0 | 1.8 | -0.2 | 3 | 3 | 0 |
| [019](/Users/usbdick/Documents/New%20project/synrail/fixtures/alpha_external_run_019/REPORT.md) | Gemini CLI | orientation | ORIENTATION_SUMMARIZED_WITH_OVEREXPLORATION | mixed | unclear | medium | 0.4 | 0.9 | +0.5 | 0 | 0 | 0 |
| [020](/Users/usbdick/Documents/New%20project/synrail/fixtures/alpha_external_run_020/REPORT.md) | Claude Code | orientation | ORIENTATION_SUMMARIZED | none | yes | medium | 0.4 | 0.3 | -0.1 | 0 | 0 | 0 |
| [019b](/Users/usbdick/Documents/New%20project/synrail/fixtures/alpha_external_run_019b/REPORT.md) | Gemini CLI | orientation | ORIENTATION_SUMMARIZED_WITH_OVEREXPLORATION | mixed | unclear | medium | 0.4 | 0.8 | +0.4 | 0 | 0 | 0 |
| [020b](/Users/usbdick/Documents/New%20project/synrail/fixtures/alpha_external_run_020b/REPORT.md) | Claude Code | orientation | ORIENTATION_SUMMARIZED_WITH_SYNRAIL_FIRST | none | yes | medium | 0.4 | 0.3 | -0.1 | 0 | 0 | 0 |
| [019c](/Users/usbdick/Documents/New%20project/synrail/fixtures/alpha_external_run_019c/REPORT.md) | Gemini CLI | orientation | ORIENTATION_SUMMARIZED_WITH_REDUCED_EXPLORATION | mixed | unclear | medium | 0.4 | 0.5 | +0.1 | 0 | 0 | 0 |

## Per-Run Records

### Run 001

- Report: [fixtures/alpha_external_run_001/REPORT.md](/Users/usbdick/Documents/New%20project/synrail/fixtures/alpha_external_run_001/REPORT.md)
- Task class: `trivial / additive_change`
- Failure owner: `harness`
- Reuse tomorrow: `no`
- Wedge fit: `low`
- Baseline minutes estimate: `0.3`
- Synrail minutes actual: `0.4`
- Delta time: `+0.1`
- Baseline retry count estimate: `0`
- Synrail check count: `0`
- Delta loops: `0`
- Baseline restore path: `n/a`
- Synrail restore path: `n/a`
- Delta recovery: `n/a`
- Why it matters:
  - this run should not count as product weakness or strength
  - it mainly records that Claude's non-interactive harness can dominate the lane before `Synrail` is even exercised

### Run 002

- Report: [fixtures/alpha_external_run_002/REPORT.md](/Users/usbdick/Documents/New%20project/synrail/fixtures/alpha_external_run_002/REPORT.md)
- Task class: `trivial / additive_change`
- Failure owner: `product`
- Reuse tomorrow: `no`
- Wedge fit: `low`
- Baseline minutes estimate: `0.3`
- Synrail minutes actual: `0.8`
- Delta time: `+0.5`
- Baseline retry count estimate: `0`
- Synrail check count: `4`
- Delta loops: `+4`
- Baseline restore path: `n/a`
- Synrail restore path: `n/a`
- Delta recovery: `n/a`
- Why it matters:
  - strongest current evidence that trivial cheap tasks still pay too much visible control tax
  - baseline is probably good enough here

### Run 003

- Report: [fixtures/alpha_external_run_003/REPORT.md](/Users/usbdick/Documents/New%20project/synrail/fixtures/alpha_external_run_003/REPORT.md)
- Task class: `trivial / additive_change`
- Failure owner: `mixed`
- Reuse tomorrow: `unclear`
- Wedge fit: `low`
- Baseline minutes estimate: `0.3`
- Synrail minutes actual: `0.8`
- Delta time: `+0.5`
- Baseline retry count estimate: `0`
- Synrail check count: `2`
- Delta loops: `+2`
- Baseline restore path: `n/a`
- Synrail restore path: `n/a`
- Delta recovery: `n/a`
- Why it matters:
  - happy path works
  - but only after harness help and with visible `check --clean-surface` ceremony

### Run 004

- Report: [fixtures/alpha_external_run_004/REPORT.md](/Users/usbdick/Documents/New%20project/synrail/fixtures/alpha_external_run_004/REPORT.md)
- Task class: `bugfix`
- Failure owner: `harness`
- Reuse tomorrow: `no`
- Wedge fit: `medium`
- Baseline minutes estimate: `n/a`
- Synrail minutes actual: `2.3`
- Delta time: `n/a`
- Baseline retry count estimate: `n/a`
- Synrail check count: `0`
- Delta loops: `n/a`
- Baseline restore path: `n/a`
- Synrail restore path: `n/a`
- Delta recovery: `n/a`
- Why it matters:
  - invalid run
  - should not be used as evidence for or against product value

### Run 005

- Report: [fixtures/alpha_external_run_005/REPORT.md](/Users/usbdick/Documents/New%20project/synrail/fixtures/alpha_external_run_005/REPORT.md)
- Task class: `bugfix / proof_heavy`
- Failure owner: `mixed`
- Reuse tomorrow: `unclear`
- Wedge fit: `high`
- Baseline minutes estimate: `1.0`
- Synrail minutes actual: `1.5`
- Delta time: `+0.5`
- Baseline retry count estimate: `1`
- Synrail check count: `3`
- Delta loops: `+2`
- Baseline restore path: `n/a`
- Synrail restore path: `n/a`
- Delta recovery: `n/a`
- Why it matters:
  - strong mixed signal
  - hidden oracle passed, so the fix was real
  - but proof still allowed narrative-heavy readback and parent git clutter was still visible

### Run 006

- Report: [fixtures/alpha_external_run_006/REPORT.md](/Users/usbdick/Documents/New%20project/synrail/fixtures/alpha_external_run_006/REPORT.md)
- Task class: `bugfix`
- Failure owner: `harness`
- Reuse tomorrow: `unclear`
- Wedge fit: `high`
- Baseline minutes estimate: `1.5`
- Synrail minutes actual: `2.1`
- Delta time: `+0.6`
- Baseline retry count estimate: `1`
- Synrail check count: `1`
- Delta loops: `0`
- Baseline restore path: `n/a`
- Synrail restore path: `n/a`
- Delta recovery: `n/a`
- Why it matters:
  - strongest current evidence that a bounded bug-fix can go through honestly without reproducing a false green
  - but observability on headless Claude remains weak

### Run 007

- Report: [fixtures/alpha_external_run_007/REPORT.md](/Users/usbdick/Documents/New%20project/synrail/fixtures/alpha_external_run_007/REPORT.md)
- Task class: `restore`
- Failure owner: `product`
- Reuse tomorrow: `no`
- Wedge fit: `high`
- Baseline minutes estimate: `0.3`
- Synrail minutes actual: `0.7`
- Delta time: `+0.4`
- Baseline retry count estimate: `1`
- Synrail check count: `1`
- Delta loops: `0`
- Baseline restore path: `manual rollback of the changed file or direct revert to the known-good surface`
- Synrail restore path: `save -> confirm-restore -> restore`
- Delta recovery: `baseline likely succeeds quickly; Synrail failed to recover at all`
- Why it matters:
  - strongest negative signal in the current alpha set
  - restore is part of the intended wedge, so this is a direct strike against baseline advantage

### Run 008

- Report: [fixtures/alpha_external_run_008/REPORT.md](/Users/usbdick/Documents/New%20project/synrail/fixtures/alpha_external_run_008/REPORT.md)
- Task class: `handoff`
- Failure owner: `none`
- Reuse tomorrow: `yes`
- Wedge fit: `high`
- Baseline minutes estimate: `2.0`
- Synrail minutes actual: `1.4`
- Delta time: `-0.6`
- Baseline retry count estimate: `3`
- Synrail check count: `3`
- Delta loops: `0`
- Baseline restore path: `n/a`
- Synrail restore path: `n/a`
- Delta recovery: `n/a`
- Why it matters:
  - strongest current positive signal
  - second-operator continuation looks materially real
  - this is the clearest contour where `Synrail` already looks stronger than the simpler baseline

### Run 009

- Report: [fixtures/alpha_external_run_009/REPORT.md](/Users/usbdick/Documents/New%20project/synrail/fixtures/alpha_external_run_009/REPORT.md)
- Task class: `trivial / additive_change`
- Failure owner: `product`
- Reuse tomorrow: `no`
- Wedge fit: `low`
- Baseline minutes estimate: `0.3`
- Synrail minutes actual: `1.0`
- Delta time: `+0.7`
- Baseline retry count estimate: `0`
- Synrail check count: `4`
- Delta loops: `+4`
- Baseline restore path: `n/a`
- Synrail restore path: `n/a`
- Delta recovery: `n/a`
- Why it matters:
  - strongest fresh confirmation that trivial tasks are still paying too much visible ceremony tax
  - the current compressed-loop / clean-surface tranche did not yet remove live Gemini confusion around `repair-step` and `--clean-surface`
  - `Synrail` stayed honest and blocked weak proof, but the cost on this contour is still materially worse than baseline

### Run 010

- Report: [fixtures/alpha_external_run_010/REPORT.md](/Users/usbdick/Documents/New%20project/synrail/fixtures/alpha_external_run_010/REPORT.md)
- Task class: `bugfix / proof_heavy`
- Failure owner: `none`
- Reuse tomorrow: `yes`
- Wedge fit: `high`
- Baseline minutes estimate: `1.0`
- Synrail minutes actual: `1.0`
- Delta time: `0.0`
- Baseline retry count estimate: `1`
- Synrail check count: `2`
- Delta loops: `+1`
- Baseline restore path: `n/a`
- Synrail restore path: `n/a`
- Delta recovery: `n/a`
- Why it matters:
  - strongest fresh signal that proof hardening is moving in the right direction
  - Gemini's vague first proof did not simply glide through; the run ended accepted only after the readback became concrete and line-level
  - this does not yet prove full proof independence, but it does show less narrative slack than earlier runs

### Run 011

- Report: [fixtures/alpha_external_run_011/REPORT.md](/Users/usbdick/Documents/New%20project/synrail/fixtures/alpha_external_run_011/REPORT.md)
- Task class: `restore`
- Failure owner: `operator`
- Reuse tomorrow: `unclear`
- Wedge fit: `high`
- Baseline minutes estimate: `n/a`
- Synrail minutes actual: `0.2`
- Delta time: `n/a`
- Baseline retry count estimate: `n/a`
- Synrail check count: `0`
- Delta loops: `n/a`
- Baseline restore path: `n/a`
- Synrail restore path: `n/a`
- Delta recovery: `n/a`
- Why it matters:
  - this run is explicitly invalid and should not be used as restore evidence
  - the probe started from a bad baseline template, so the only honest conclusion is that restore still needs a clean rerun before we compare against run 007

### Run 011b

- Report: [fixtures/alpha_external_run_011b/REPORT.md](/Users/usbdick/Documents/New%20project/synrail/fixtures/alpha_external_run_011b/REPORT.md)
- Task class: `restore`
- Failure owner: `product`
- Reuse tomorrow: `no`
- Wedge fit: `high`
- Baseline minutes estimate: `0.3`
- Synrail minutes actual: `0.0`
- Delta time: `-0.3`
- Baseline retry count estimate: `0`
- Synrail check count: `0`
- Delta loops: `0`
- Baseline restore path: `manual revert of the changed file or copy back from the known-good baseline`
- Synrail restore path: `save (fallback ready) -> confirm-restore -> restore`
- Delta recovery: `save is now materially better than run 007 because it arms a pre-run fallback, but restore still loses to baseline because the broken file remains broken after Synrail says RESTORED`
- Why it matters:
  - this is the first valid restore rerun after the pre-run snapshot tranche
  - `save` is no longer the main failure; it now arms a pre-run fallback successfully
  - the remaining restore bug is more precise and more serious: `confirm-restore` says no restore point exists, then `restore` claims success anyway, and the broken state remains broken

### Run 012

- Report: [fixtures/alpha_external_run_012/REPORT.md](/Users/usbdick/Documents/New%20project/synrail/fixtures/alpha_external_run_012/REPORT.md)
- Task class: `handoff`
- Failure owner: `harness`
- Reuse tomorrow: `no`
- Wedge fit: `high`
- Baseline minutes estimate: `n/a`
- Synrail minutes actual: `0.0`
- Delta time: `n/a`
- Baseline retry count estimate: `n/a`
- Synrail check count: `0`
- Delta loops: `n/a`
- Baseline restore path: `n/a`
- Synrail restore path: `n/a`
- Delta recovery: `n/a`
- Why it matters:
  - this run should not be counted as handoff product evidence
  - the root/headless Claude lane blocked shell access before a governed intermediate state even existed

### Run 012b

- Report: [fixtures/alpha_external_run_012b/REPORT.md](/Users/usbdick/Documents/New%20project/synrail/fixtures/alpha_external_run_012b/REPORT.md)
- Task class: `handoff`
- Failure owner: `harness`
- Reuse tomorrow: `no`
- Wedge fit: `high`
- Baseline minutes estimate: `n/a`
- Synrail minutes actual: `0.0`
- Delta time: `n/a`
- Baseline retry count estimate: `n/a`
- Synrail check count: `0`
- Delta loops: `n/a`
- Baseline restore path: `n/a`
- Synrail restore path: `n/a`
- Delta recovery: `n/a`
- Why it matters:
  - this rerun shows the remaining Claude lane problem more precisely
  - under root, the bypass-permissions escape hatch is itself blocked, so the current Claude handoff lane is still harness-limited rather than product-limited

### Run 013

- Report: [fixtures/alpha_external_run_013/REPORT.md](/Users/usbdick/Documents/New%20project/synrail/fixtures/alpha_external_run_013/REPORT.md)
- Task class: `bugfix`
- Failure owner: `none`
- Reuse tomorrow: `yes`
- Wedge fit: `high`
- Baseline minutes estimate: `0.8`
- Synrail minutes actual: `1.0`
- Delta time: `+0.2`
- Baseline retry count estimate: `1`
- Synrail check count: `1`
- Delta loops: `0`
- Baseline restore path: `n/a`
- Synrail restore path: `n/a`
- Delta recovery: `n/a`
- Why it matters:
  - this is another fresh accepted bugfix signal after the proof-hardening tranche
  - it strengthens the claim that bounded bugfix closure is credible even when the task is not the same retry-backoff change as run 010

### Run 014

- Report: [fixtures/alpha_external_run_014/REPORT.md](/Users/usbdick/Documents/New%20project/synrail/fixtures/alpha_external_run_014/REPORT.md)
- Task class: `restore`
- Failure owner: `product`
- Reuse tomorrow: `no`
- Wedge fit: `high`
- Baseline minutes estimate: `0.3`
- Synrail minutes actual: `0.0`
- Delta time: `-0.3`
- Baseline retry count estimate: `0`
- Synrail check count: `0`
- Delta loops: `0`
- Baseline restore path: `manual revert of the changed file or copy back from the known-good baseline`
- Synrail restore path: `save (pre-run snapshot armed) -> confirm-restore -> restore`
- Delta recovery: `baseline still wins because Synrail can arm a snapshot but still cannot actually recover the broken file after restore reports success`
- Why it matters:
  - this run confirms that the restore problem is still alive even after the pre-run snapshot tranche
  - it sharpens the product bug further: `save` is no longer the headline failure, but `restore` still does not restore the broken working state
  - restore therefore remains the strongest negative signal in the alpha ledger

### Run 014b

- Report: [fixtures/alpha_external_run_014b/REPORT.md](/Users/usbdick/Documents/New%20project/synrail/fixtures/alpha_external_run_014b/REPORT.md)
- Task class: `restore`
- Failure owner: `operator`
- Reuse tomorrow: `unclear`
- Wedge fit: `high`
- Baseline minutes estimate: `n/a`
- Synrail minutes actual: `0.0`
- Delta time: `n/a`
- Baseline retry count estimate: `n/a`
- Synrail check count: `0`
- Delta loops: `n/a`
- Baseline restore path: `n/a`
- Synrail restore path: `save -> confirm-restore -> restore`
- Delta recovery: `n/a`
- Why it matters:
  - this rerun should not be treated as the final restore verdict because the baseline test command was wrong
  - it is still useful diagnostically because it showed that `confirm-restore` now passes on the deployed build

### Run 014c

- Report: [fixtures/alpha_external_run_014c/REPORT.md](/Users/usbdick/Documents/New%20project/synrail/fixtures/alpha_external_run_014c/REPORT.md)
- Task class: `restore`
- Failure owner: `product`
- Reuse tomorrow: `no`
- Wedge fit: `high`
- Baseline minutes estimate: `0.3`
- Synrail minutes actual: `0.0`
- Delta time: `-0.3`
- Baseline retry count estimate: `0`
- Synrail check count: `0`
- Delta loops: `0`
- Baseline restore path: `manual revert of the changed file or copy back from the known-good baseline`
- Synrail restore path: `save (pre-run snapshot armed) -> confirm-restore -> restore`
- Delta recovery: `baseline still wins because Synrail confirms the restore point correctly but still leaves the broken file in place after reporting RESTORED`
- Why it matters:
  - this is the authoritative deployed-build restore verdict after the parser/default-path fix
  - it shows that the problem is no longer checkpoint discovery
  - the remaining restore bug is now explicit in the trace: `checkpoint_restore.json` records `workspace_restored: false`

### Run 014d

- Report: [fixtures/alpha_external_run_014d/REPORT.md](/Users/usbdick/Documents/New%20project/synrail/fixtures/alpha_external_run_014d/REPORT.md)
- Task class: `restore`
- Failure owner: `product`
- Reuse tomorrow: `unclear`
- Wedge fit: `high`
- Baseline minutes estimate: `0.3`
- Synrail minutes actual: `0.0`
- Delta time: `-0.3`
- Baseline retry count estimate: `0`
- Synrail check count: `0`
- Delta loops: `0`
- Baseline restore path: `manual revert of the changed file or copy back from the known-good baseline`
- Synrail restore path: `save -> confirm-restore -> restore -> honest restore-failed rollback`
- Delta recovery: `Synrail is now more truthful than 014c because it no longer claims false success, but baseline still wins on actual recovery for no-commit workspaces`
- Why it matters:
  - this run validates the latest honesty fix on the deployed build
  - the workspace is in git but has no commits, so restore correctly records `workspace_snapshot.type = none`
  - the product no longer lies about restore success, but it still cannot recover the workspace for this contour

### Run 014e

- Report: [fixtures/alpha_external_run_014e/REPORT.md](/Users/usbdick/Documents/New%20project/synrail/fixtures/alpha_external_run_014e/REPORT.md)
- Task class: `restore`
- Failure owner: `none`
- Reuse tomorrow: `yes`
- Wedge fit: `high`
- Baseline minutes estimate: `0.3`
- Synrail minutes actual: `0.0`
- Delta time: `-0.3`
- Baseline retry count estimate: `0`
- Synrail check count: `0`
- Delta loops: `0`
- Baseline restore path: `manual revert of the changed file or copy back from the known-good baseline`
- Synrail restore path: `save (file-copy pre-run snapshot) -> confirm-restore -> restore`
- Delta recovery: `Synrail now matches or beats baseline on this contour because the broken file is restored automatically and tests return to green`
- Why it matters:
  - this is the strongest restore-positive signal in the ledger so far
  - it validates the `file_copy` fallback on exactly the no-commit git workspace that previously failed in `014d`
  - restore is no longer just more honest here; it actually works

### Run 015

- Report: [fixtures/alpha_external_run_015/REPORT.md](/Users/usbdick/Documents/New%20project/synrail/fixtures/alpha_external_run_015/REPORT.md)
- Task class: `trivial / additive_change`
- Failure owner: `product`
- Reuse tomorrow: `no`
- Wedge fit: `low`
- Baseline minutes estimate: `0.3`
- Synrail minutes actual: `1.0`
- Delta time: `+0.7`
- Baseline retry count estimate: `0`
- Synrail check count: `2`
- Delta loops: `+2`
- Baseline restore path: `n/a`
- Synrail restore path: `n/a`
- Delta recovery: `n/a`
- Why it matters:
  - this is a useful retest after the command-surface / clean-surface tranche
  - it shows real progress over run 009: accepted closure, compressed `--help`, and no visible `--clean-surface` dance
  - but trivial-task overhead is still materially worse than baseline, so the trivial lane is improved but not won

### Run 016

- Report: [fixtures/alpha_external_run_016/REPORT.md](/Users/usbdick/Documents/New%20project/synrail/fixtures/alpha_external_run_016/REPORT.md)
- Task class: `bugfix / proof_heavy`
- Failure owner: `mixed`
- Reuse tomorrow: `yes`
- Wedge fit: `high`
- Baseline minutes estimate: `1.0`
- Synrail minutes actual: `1.2`
- Delta time: `+0.2`
- Baseline retry count estimate: `1`
- Synrail check count: `2`
- Delta loops: `+1`
- Baseline restore path: `n/a`
- Synrail restore path: `n/a`
- Delta recovery: `n/a`
- Why it matters:
  - this is another positive signal for proof hardening, because the final accepted readback was concrete and observational rather than a loose action summary
  - it stops short of perfectly isolating the action-verb rejection guard, so it should count as partial validation rather than a clean proof of that one heuristic
  - it also surfaced a smaller reporting seam: accepted closure and `report.json` messaging still looked slightly inconsistent

### Run 017

- Report: [fixtures/alpha_external_run_017/REPORT.md](/Users/usbdick/Documents/New%20project/synrail/fixtures/alpha_external_run_017/REPORT.md)
- Task class: `bugfix`
- Failure owner: `none`
- Reuse tomorrow: `yes`
- Wedge fit: `high`
- Baseline minutes estimate: `0.8`
- Synrail minutes actual: `1.0`
- Delta time: `+0.2`
- Baseline retry count estimate: `1`
- Synrail check count: `1`
- Delta loops: `0`
- Baseline restore path: `n/a`
- Synrail restore path: `n/a`
- Delta recovery: `n/a`
- Why it matters:
  - this is a fresh independent bounded bugfix signal on a contour that is not just a replay of run 010 or 013
  - one-check accepted closure keeps strengthening the claim that bounded bugfix work is becoming repeatable on the intended wedge

### Run 018

- Report: [fixtures/alpha_external_run_018/REPORT.md](/Users/usbdick/Documents/New%20project/synrail/fixtures/alpha_external_run_018/REPORT.md)
- Task class: `handoff`
- Failure owner: `none`
- Reuse tomorrow: `yes`
- Wedge fit: `high`
- Baseline minutes estimate: `2.0`
- Synrail minutes actual: `1.8`
- Delta time: `-0.2`
- Baseline retry count estimate: `3`
- Synrail check count: `3`
- Delta loops: `0`
- Baseline restore path: `n/a`
- Synrail restore path: `n/a`
- Delta recovery: `n/a`
- Why it matters:
  - this is now a second valid handoff success, which is exactly the kind of repetition the wedge needed
  - first operator left a real semantically insufficient state; second operator inherited that state, repaired the proof, and reached accepted closure
  - handoff / continuation honesty remains the clearest place where `Synrail` looks materially stronger than the simpler baseline

### Run 019

- Report: [fixtures/alpha_external_run_019/REPORT.md](/Users/usbdick/Documents/New%20project/synrail/fixtures/alpha_external_run_019/REPORT.md)
- Task class: `orientation`
- Failure owner: `mixed`
- Reuse tomorrow: `unclear`
- Wedge fit: `medium`
- Baseline minutes estimate: `0.4`
- Synrail minutes actual: `0.9`
- Delta time: `+0.5`
- Baseline retry count estimate: `0`
- Synrail check count: `0`
- Delta loops: `0`
- Baseline restore path: `n/a`
- Synrail restore path: `n/a`
- Delta recovery: `n/a`
- Why it matters:
  - Gemini can now recover governed project context without drifting into sibling probe folders
  - but the orientation lane still over-explores and does not visibly standardize on a literal `synrail` CLI-first entry

### Run 020

- Report: [fixtures/alpha_external_run_020/REPORT.md](/Users/usbdick/Documents/New%20project/synrail/fixtures/alpha_external_run_020/REPORT.md)
- Task class: `orientation`
- Failure owner: `none`
- Reuse tomorrow: `yes`
- Wedge fit: `medium`
- Baseline minutes estimate: `0.4`
- Synrail minutes actual: `0.3`
- Delta time: `-0.1`
- Baseline retry count estimate: `0`
- Synrail check count: `0`
- Delta loops: `0`
- Baseline restore path: `n/a`
- Synrail restore path: `n/a`
- Delta recovery: `n/a`
- Why it matters:
  - Claude answered accurately and quickly from governed artifacts with no write attempts and no parent-directory drift
  - but even this stronger run still used direct `.synrail` reads rather than a literal `synrail status` entrypoint

### Run 019b

- Report: [fixtures/alpha_external_run_019b/REPORT.md](/Users/usbdick/Documents/New%20project/synrail/fixtures/alpha_external_run_019b/REPORT.md)
- Task class: `orientation`
- Failure owner: `mixed`
- Reuse tomorrow: `unclear`
- Wedge fit: `medium`
- Baseline minutes estimate: `0.4`
- Synrail minutes actual: `0.8`
- Delta time: `+0.4`
- Baseline retry count estimate: `0`
- Synrail check count: `0`
- Delta loops: `0`
- Baseline restore path: `n/a`
- Synrail restore path: `n/a`
- Delta recovery: `n/a`
- Why it matters:
  - this is the direct retest after the orientation-guidance wording fix
  - Gemini now explicitly acknowledges Synrail at the start, but the actual lane is still too wide and exploratory
  - this means the wording change alone was not enough to produce a reliable minimal orientation contour on Gemini

### Run 020b

- Report: [fixtures/alpha_external_run_020b/REPORT.md](/Users/usbdick/Documents/New%20project/synrail/fixtures/alpha_external_run_020b/REPORT.md)
- Task class: `orientation`
- Failure owner: `none`
- Reuse tomorrow: `yes`
- Wedge fit: `medium`
- Baseline minutes estimate: `0.4`
- Synrail minutes actual: `0.3`
- Delta time: `-0.1`
- Baseline retry count estimate: `0`
- Synrail check count: `0`
- Delta loops: `0`
- Baseline restore path: `n/a`
- Synrail restore path: `n/a`
- Delta recovery: `n/a`
- Why it matters:
  - this is the clearest validation of the guidance fix so far
  - Claude literally ran `synrail` first, then answered from governed artifacts in a short read-only flow
  - orientation is now visibly stronger on the Claude lane than it was in run `020`

### Run 019c

- Report: [fixtures/alpha_external_run_019c/REPORT.md](/Users/usbdick/Documents/New%20project/synrail/fixtures/alpha_external_run_019c/REPORT.md)
- Task class: `orientation`
- Failure owner: `mixed`
- Reuse tomorrow: `unclear`
- Wedge fit: `medium`
- Baseline minutes estimate: `0.4`
- Synrail minutes actual: `0.5`
- Delta time: `+0.1`
- Baseline retry count estimate: `0`
- Synrail check count: `0`
- Delta loops: `0`
- Baseline restore path: `n/a`
- Synrail restore path: `n/a`
- Delta recovery: `n/a`
- Why it matters:
  - this is the Gemini-only retest after the stronger lane-specific orientation wording
  - compared with `019b`, the run is materially narrower: no database/schema probing, no sibling-probe archaeology, and the answer stays centered on governed state
  - but the lane still is not as small as Claude `020b`, and the server artifacts did not persist a normal `end` / `rc` completion trace

## Current Read

If we force the current ledger into one brutally practical sentence:

- `Synrail` already looks stronger than baseline on `handoff / continuation honesty`
- looks credible on bounded accepted closure
- looks materially stronger than before on proof hardening for bounded bug-fix runs
- still looks too heavy on trivial tasks, even though the newer compressed-loop tranche improved the path from run 009 to run 015
- and now has a materially stronger restore story: `014d` fixed the false-success lie, and `014e` validates real recovery on the no-commit git contour via `file_copy`
- orientation on governed roots is better than before; Claude now shows a literal `synrail`-first entry, while Gemini has narrowed the loop materially in `019c` but still does not converge on that same small shape
- the Claude-first handoff lane is still harness-limited under the current root server setup, so new handoff strength is still coming mostly from Gemini-side evidence

## Next Runs

Append new runs using:

- [ALPHA_RUN_REPORT_TEMPLATE_002.md](/Users/usbdick/Documents/New%20project/synrail/docs/review/ALPHA_RUN_REPORT_TEMPLATE_002.md)

For each new run:

1. create the run-specific `fixtures/.../REPORT.md`
2. add one new row to the summary table above
3. add one new per-run record block below
4. update the top-level synthesis only when the overall verdict actually changes
