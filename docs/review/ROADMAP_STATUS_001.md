# Roadmap Status 001

This document is intentionally split into:

- built now
- partially built
- planned next
- deliberately frozen

## Built now

### Product-shell tranche

Completed:

- thin default output layer
- bounded `repair-step` bridge
- controlled-start bootstrap and starter proof flow
- `save / retry / restore / confirm-restore` human-facing shell
- alpha install path
- reduced visible artifact choreography
- one bounded happy path

### Truth hardening tranche

Completed:

1. semantic proof hardening
2. acceptance criteria independence
3. doctor measured coverage
4. continuation arbiter
5. regression harness
6. observability only where it supports those weak spots
7. explicit evidence-ownership split for roadmap eligibility
8. task-class-scoped hostile observation heuristics on measured proof-sensitive lanes

### External-alpha readiness slice

Completed:

- current tester-pack doc aligned to current shell
- current runnable tester-pack smoke
- current canonical tester-pack fixture
- current claim-validation pack for second-operator followability and evidence-ownership discipline
- fresh-path identity plumbing through `init -> check`
- removal of acceptance self-staleness on harmless artifact-path drift

### Current local-roadmap delta

Completed as shipped tranches on the current branch:

1. behavioral cheapening by default
   - only `final_result.json` is materialized by default on `start`
   - fallback proof surfaces stay unmaterialized until explicitly needed
   - first-loop shell guidance now keeps `final_result` as the only default proof target
   - agent-facing repo guidance now also tells operators to verify locally, strengthen `final_result.json` first, leave `readback.txt` and `scenario_proof.txt` untouched unless later named, and keep `cleanup_status` absent unless Synrail explicitly asks for cleanup attestation
   - first-run docs and the reference README now keep `final_result.json` as the only default proof target and only surface `readback-template` or `scenario-proof-template` after `check` explicitly targets a fallback prose surface
   - explicitly targeted `readback.txt` and `scenario_proof.txt` repair checklists now ask for the minimal concrete observation or verification needed for the named blocker instead of inviting extra explanatory prose
   - explicitly targeted `readback-template` and `scenario-proof-template` starter text now also asks for minimal concrete blocker-specific evidence instead of generic descriptive prose
   - runtime bundle why-text for readback and scenario proof now describes those fallback surfaces as blocker-specific fallback evidence instead of explanatory prose when runtime corroboration is still too weak to waive them
   - bootstrap starter guidance now tells operators that fallback prose surfaces stay untouched unless Synrail explicitly targets one as blocker-specific fallback evidence
   - partial-proof continuation now keeps `repair-step` on `final_result.json` first whenever final-result truth is still stale, before Synrail materializes or targets fallback proof surfaces
2. repeatable everyday economics benchmark
   - one repeatable everyday benchmark pack now exists
   - it currently shows two repeatable low-drag winners, four baseline-good-enough paths, and zero unclear paths
   - the current focus family is `small_template_text_fix`, which now has two justified low-drag paths and reads as a low-variance repeatable family even though the broader repeatable-everyday verdict is still baseline-favorable overall
   - that focused family still reads as both `FOCUSED_CLASS_CHEAP_ENOUGH` and `FOCUSED_CLASS_BEHAVIOR_CHEAP_BY_DEFAULT` on the current canonical pack
   - the class verdict is still baseline-favorable overall
   - the harness and pack now also split the everyday economics lane into machine-readable `fixed_control_mass` vs `behavioral_control_tax`, while keeping `total_control_burden`, `checks_per_accepted_closure`, `operator_visible_actions`, and `got_lost_moments` visible as supporting deltas
   - a same-family behavior-independence pressure slice now shows the focused class can remain `SYNRAIL_BETTER` and `FOCUSED_CLASS_KERNEL_CHEAP_ENOUGH` while behavior cheapness drops to `FOCUSED_CLASS_BEHAVIOR_NOT_YET_CHEAP_BY_DEFAULT` when an extra skippable surface reappears
   - this means the focused win is now more honest: the canonical wedge is behavior-cheap by default, but that behavior cheapness is not yet fully independent under same-family pressure
3. proof independence stress
   - labeled-but-thin scenario prose no longer carries verification corroboration on strict proof-sensitive lanes
   - thin command confirmations like `Output: ok`, `grep confirms ...`, or exit-code-only observations are now blocked on those lanes
4. restore maturity across families
   - the local restore matrix now covers clean git, dirty tracked, dirty untracked, mixed file state, non-git file-copy, no-commit git via file-copy fallback, and unsupported honest fail
5. shell compression to actually thin
   - fallback chatter in the first operator loop is now compressed into one note instead of multiple optional branches
   - the default start/check shell now points to final_result.json plus helper commands instead of inlining the full proof tutorial
   - the default non-green path now lets `synrail check` carry the first bounded fix, with `repair-step` left as an optional standalone prompt surface
6. evidence hygiene as process rule
   - roadmap moves are now gated on classified evidence sets, not justified from a single noisy report
7. strengthen the strongest wedge on ugly contours
   - second-operator and continuation honesty now have uglier validation contours with bounded retry pressure
8. cleanup truth now follows the cheap happy path
   - bundle cleanup fallback now recognizes the runtime doctor `gate_results` shape instead of requiring a unit-only gate key
   - normal `synrail check` can satisfy `cleanup_status` from doctor-ready workspace truth without manual `final_result.json` repair
   - smoke coverage now proves the real `start -> final_result without cleanup_status -> check` path
9. change-impact invalidation now narrows the default non-green path
   - default thin output now reuses refresh `dominant_invalidation` and `invalidations` when they match the active run
   - the default `synrail check` summary now points only at stale obligations instead of broadly re-describing the whole non-green contour
   - dev thin output now shows refresh invalidation lines so retry/check guidance stays runtime-visible without adding a new operator surface

## Partially built

These exist, but are still intentionally narrow.

### Alpha shell

Partially built because:

- it is one contour, not a broad shell
- install path is still toolchain-sensitive
- some compatibility vocabulary still exists underneath

### Observability

Partially built because:

- local export exists
- no hosted dashboard exists
- event history is still intentionally compact

### Baseline and substitute pressure

Partially built because:

- some substitute and economics pressure slices exist
- the active baseline economics harness now also tracks fixed control mass through mental steps, trust-bearing artifacts, and required visible surfaces
- one repeatable everyday benchmark pack now exists for the cheapened local contour
- that pack currently reads as baseline-favorable overall, with one repeatable low-drag winner but no broad everyday win yet
- this is still not a broad external benchmark program

### Restore maturity

Partially built because:

- the local restore matrix now has explicit regression coverage for clean git, dirty tracked, dirty untracked, mixed file state, non-git file-copy, no-commit git via file-copy fallback, and unsupported honest fail
- the no-commit git contour is now locally covered as a distinct file-copy restore contour instead of living only in external evidence
- this is still a narrow matrix, not a broad claim that restore is mature on arbitrary workspaces

## Planned next

These are the most likely next moves after the current local-roadmap closure.

1. refresh critic-facing review docs on the current shipped branch truth
2. hand the current branch to critics before broadening any product story
3. collect one fresh live external signal on the cheapened and evidence-gated branch
4. decide only after that whether the current wedge deserves broader packaging or more hardening

## Deliberately frozen for now

Not the next move:

- new continuation families
- richer repair history
- richer operator evidence for completeness only
- hybrid promotion
- broad product shell growth
- hosted telemetry platform
- broad packaging work
- new conceptual layers without runtime consequence

## Open risks

These are the major honest risks still worth external pressure.

1. semantic proof may still be too thin in domain-specific cases, and the newer scoped heuristics still need fresh unseen validation
2. measured doctor coverage is real but still corpus-bounded
3. the continuation arbiter covers important surfaces, but still not every imaginable ambiguity
4. the cheapened everyday contour still wins only one repeatable benchmark path and remains baseline-favorable overall as a class
5. restore and continuation ergonomics may still look heavier than a critic is willing to tolerate
6. the current evidence base is stronger and better gated than before, but it is still partly self-curated and still needs fresh outside pressure

## What a successful external critique should tell us

A good critique should tell us:

- where the kernel is genuinely stronger than baseline
- where the product still pays too much operator tax
- which hardening claims feel real
- which ones still feel local/canonical
- whether the current alpha lane is worth expanding at all
