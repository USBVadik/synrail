# External Alpha Send 001

Use this document when you are ready to send `Synrail` to outside critics or early alpha testers.

This is not a pitch for a platform.

It is a send-ready handoff for a narrow proof-first control product.

## Who to Send It To

Best targets:

- experienced engineers who have already used coding agents in real repos
- people who have felt false-green pain, unclear non-green loops, or bad handoff/re-entry pain
- people willing to be blunt

Weaker targets:

- people who mainly want polished demos
- people evaluating this as a broad workflow platform
- people who will only react to UI polish

## What to Send

Minimum package:

1. the exact repository snapshot at the explicitly selected target commit
2. [EXTERNAL_CRITIQUE_PACK_001.md](./EXTERNAL_CRITIQUE_PACK_001.md)
3. [CRITIC_REVIEW_BRIEF_2026-04-19.md](./CRITIC_REVIEW_BRIEF_2026-04-19.md)
4. [EXTERNAL_FULL_REVIEW_2026-04-21.md](./EXTERNAL_FULL_REVIEW_2026-04-21.md)
5. [ALPHA_TEST_PACK_001.md](../core/ALPHA_TEST_PACK_001.md)
6. [PRODUCT_MEMO_001.md](./PRODUCT_MEMO_001.md)
7. [KNOWN_WEAKNESSES_001.md](./KNOWN_WEAKNESSES_001.md)
8. focused economics test:
   - `tests/test_everyday_benchmark_pack.py`
9. curated external fixture:
   - `fixtures/alpha_test_pack_run_004/`
10. focused economics fixtures:
   - `fixtures/repeatable_everyday_benchmark_pack_001.json`
   - `fixtures/cost_of_control_everyday_001.json`

Cut the external handoff from that exact snapshot. Do not assemble the send from a drifting local working tree.

If the reviewer wants deeper technical context, also include:

1. [TECHNICAL_MAP_001.md](./TECHNICAL_MAP_001.md)
2. [CODE_MAP_001.md](./CODE_MAP_001.md)
3. [CRITIC_GUIDE_001.md](./CRITIC_GUIDE_001.md)
4. [REVIEW_HANDOFF_CHECKLIST_001.md](./REVIEW_HANDOFF_CHECKLIST_001.md)
5. `tests/test_claim_validation_pack.py`

## Fastest Send Path

If the reviewer will only spend 10-20 minutes, send:

1. [ALPHA_TEST_PACK_001.md](../core/ALPHA_TEST_PACK_001.md)
2. [EXTERNAL_CRITIQUE_PACK_001.md](./EXTERNAL_CRITIQUE_PACK_001.md)
3. [KNOWN_WEAKNESSES_001.md](./KNOWN_WEAKNESSES_001.md)

## Short DM Version

```text
I’m testing a narrow product called Synrail. It’s not a platform or orchestration shell. The wedge is simpler: block false success from coding agents, keep one verified fallback, and make non-green repair/restore paths explicit.

I want blunt critique, not encouragement.

If you’re open, I’ll send one small alpha pack that takes about 10 minutes to attack. The main questions are whether the everyday lane feels too heavy, whether the proof still feels self-issued, and whether restore or handoff value is real enough to justify the control mass.
```

## Full Email / Long Message Version

```text
I’m working on a narrow proof-first control product called Synrail.

The core claim is: claimed done is not accepted done.

It’s meant for cases where a coding agent can produce a plausible success narrative, but the operator still needs a stricter acceptance gate, a bounded next repair step when things go non-green, and a faster/more honest restore path when a verified working state matters.

This is not a platform pitch. It is one narrow alpha lane over a proof-governed kernel.

What I want from you is blunt criticism on:
- where the everyday lane still feels heavier than the loss it prevents
- which proof artifact or shell claim still feels self-issued
- whether restore, re-entry, or handoff value is concrete enough to justify the control mass
- what you would cut first if that value is still too weak

Best starting points:
- docs/core/ALPHA_TEST_PACK_001.md
- docs/review/EXTERNAL_CRITIQUE_PACK_001.md
- docs/review/KNOWN_WEAKNESSES_001.md

If you have more time:
- docs/review/TECHNICAL_MAP_001.md
- docs/review/CODE_MAP_001.md
- tests/test_truth_regressions.py

The ask is not “tell me if this is cool.”
The ask is “tell me where this still feels too heavy, too self-issued, or too weak to justify the product.”
```

## What to Ask Them To Do

Ask the reviewer to choose one of these modes:

### Mode A — 10-minute attack

1. read [ALPHA_TEST_PACK_001.md](../core/ALPHA_TEST_PACK_001.md)
2. run the quickstart
3. tell us:
   - which visible step felt heaviest relative to its value
   - which artifact or proof step still felt self-issued
   - whether restore or re-entry value felt concrete or vague

### Mode B — 45-minute teardown

1. read [EXTERNAL_CRITIQUE_PACK_001.md](./EXTERNAL_CRITIQUE_PACK_001.md)
2. read [TECHNICAL_MAP_001.md](./TECHNICAL_MAP_001.md)
3. read [KNOWN_WEAKNESSES_001.md](./KNOWN_WEAKNESSES_001.md)
4. inspect the code and fixtures they care about
5. tell us where the everyday lane still feels heavy, which proof still feels self-issued, and whether restore or handoff earns its weight

## Exact Questions To Ask

Use these questions verbatim if helpful:

1. Which step in the everyday lane feels least worth its weight?
2. Which artifact or proof surface still feels self-issued or too author-shaped to trust?
3. Where does the shell still sound more certain than the current proof has actually earned?
4. What concrete loss do you still avoid only weakly or vaguely in the everyday lane?
5. In restore, re-entry, or handoff, what concrete value does `Synrail` create over a simpler substitute?
6. If that value is still too weak, what would you cut first?

## What Good Feedback Looks Like

Good:

- “this step feels like artifact ritual, not leverage”
- “this claim is too strong for the current doctor/proof boundary”
- “this restore path is the first place I felt real value”
- “this still looks self-validating here”
- “I would delete this command from the first-run pack”

Less useful:

- “it needs a dashboard”
- “it needs more AI”
- “make it a platform”

Those are not the current review target.

## What to Request Back

Ask them to send back:

1. the scenario they ran
2. the command or step that felt heaviest relative to its value
3. the artifact or proof step that still felt self-issued or hard to trust
4. one sentence on whether restore, re-entry, or handoff value felt concrete or vague
5. telemetry export, if they used it

## Current Honest Positioning

Keep this wording tight:

- narrow proof-first control product
- one alpha lane
- not a platform
- not a broad workflow shell
- strongest where false green is expensive and verified fallback matters

## Before You Hit Send

Check:

1. [REVIEW_HANDOFF_CHECKLIST_001.md](./REVIEW_HANDOFF_CHECKLIST_001.md)
2. [ALPHA_TEST_PACK_001.md](../core/ALPHA_TEST_PACK_001.md)
