# Alpha Run Report Template 002

Use this template for each new external alpha run.

The goal is not to sound polished.

The goal is to make each run decision-useful against the simpler baseline.

Keep existing run-specific artifacts next to the report:

- `agent.log`
- `.synrail/` directory when available
- any local verification outputs worth preserving

Use `n/a` when a field genuinely does not apply.

Use `estimate` language for baseline fields unless a real side-by-side baseline replay was actually run.

---

# Alpha External Run NNN

- Tester:
- Agent:
- Task:
- Project:
- Task class:
  - one of: `trivial`, `bugfix`, `additive_change`, `handoff`, `restore`, `proof_heavy`, `ui_runtime`, `orientation`, `mixed`
- Start time:
- End time:
- Elapsed minutes:
- Check iterations:
- Final outcome:
- Failure owner:
  - one of: `none`, `product`, `harness`, `agent`, `operator`, `mixed`
- Reuse tomorrow:
  - one of: `yes`, `no`, `unclear`
- Wedge fit:
  - one of: `low`, `medium`, `high`

## Baseline Delta

- Baseline minutes estimate:
- Synrail minutes actual:
- Delta time:
- Baseline retry count estimate:
- Synrail check count:
- Delta loops:
- Baseline restore path:
- Synrail restore path:
- Delta recovery:

## What Happened

- Got lost moments:
  - ...
  - ...

## Verdict

- Verdict:

## Notes

- Hidden oracle result:
- Most important product signal:
- Most important remaining doubt:

## Quick Guidance

- `Task class` should describe the actual contour, not the prompt style.
- `Failure owner` should name where the dominant problem came from.
  - Example: Claude permission lane issue = `harness`
  - Example: broken restore semantics = `product`
- Roadmap rule: only `product` / `none` runs, plus explicitly strong `mixed` verdicts, should directly drive kernel roadmap changes.
  - `harness`, `operator`, `agent`, and non-strong `mixed` runs are still useful, but they should update lane health or conditioning work instead of pretending to be clean kernel evidence.
- `Reuse tomorrow` should be brutally practical:
  - if you would actually choose `Synrail` again for this same task tomorrow, say `yes`
  - if not, say `no`
  - if the answer depends on one fix or one harness caveat, say `unclear`
- `Wedge fit` should answer:
  - is this a contour where `Synrail` should realistically beat the simpler baseline?
- `Delta recovery` can stay `n/a` outside restore/re-entry contours.
