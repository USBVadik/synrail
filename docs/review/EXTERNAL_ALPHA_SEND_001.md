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

1. repository snapshot at the target commit
2. [EXTERNAL_CRITIQUE_PACK_001.md](./EXTERNAL_CRITIQUE_PACK_001.md)
3. [ALPHA_TEST_PACK_001.md](../core/ALPHA_TEST_PACK_001.md)
4. [PRODUCT_MEMO_001.md](./PRODUCT_MEMO_001.md)
5. [KNOWN_WEAKNESSES_001.md](./KNOWN_WEAKNESSES_001.md)
6. curated external fixture:
   - `fixtures/alpha_test_pack_run_004/`

If the reviewer wants deeper technical context, also include:

1. [TECHNICAL_MAP_001.md](./TECHNICAL_MAP_001.md)
2. [CODE_MAP_001.md](./CODE_MAP_001.md)
3. [CRITIC_GUIDE_001.md](./CRITIC_GUIDE_001.md)
4. [REVIEW_HANDOFF_CHECKLIST_001.md](./REVIEW_HANDOFF_CHECKLIST_001.md)

## Fastest Send Path

If the reviewer will only spend 10-20 minutes, send:

1. [ALPHA_TEST_PACK_001.md](../core/ALPHA_TEST_PACK_001.md)
2. [EXTERNAL_CRITIQUE_PACK_001.md](./EXTERNAL_CRITIQUE_PACK_001.md)
3. [KNOWN_WEAKNESSES_001.md](./KNOWN_WEAKNESSES_001.md)

## Short DM Version

```text
I’m testing a narrow product called Synrail. It’s not a platform or orchestration shell. The wedge is simpler: block false success from coding agents, keep one verified fallback, and make non-green repair/restore paths explicit.

I want blunt critique, not encouragement.

If you’re open, I’ll send one small alpha pack that takes about 10 minutes to attack. The main question is whether this actually creates workflow leverage, or just justified ceremony.
```

## Full Email / Long Message Version

```text
I’m working on a narrow proof-first control product called Synrail.

The core claim is: claimed done is not accepted done.

It’s meant for cases where a coding agent can produce a plausible success narrative, but the operator still needs a stricter acceptance gate, a bounded next repair step when things go non-green, and a faster/more honest restore path when a verified working state matters.

This is not a platform pitch. It is one narrow alpha lane over a proof-governed kernel.

What I want from you is blunt criticism on:
- whether the truth surfaces are actually strict enough
- whether the shell still feels like ceremony
- whether the wedge is strong enough to justify the product at all
- where you expect false accept / false reject / awkward recovery to still leak through

Best starting points:
- docs/core/ALPHA_TEST_PACK_001.md
- docs/review/EXTERNAL_CRITIQUE_PACK_001.md
- docs/review/KNOWN_WEAKNESSES_001.md

If you have more time:
- docs/review/TECHNICAL_MAP_001.md
- docs/review/CODE_MAP_001.md
- tests/test_truth_regressions.py

The ask is not “tell me if this is cool.”
The ask is “tell me where this is still fake, too ceremonial, or too narrow to matter.”
```

## What to Ask Them To Do

Ask the reviewer to choose one of these modes:

### Mode A — 10-minute attack

1. read [ALPHA_TEST_PACK_001.md](../core/ALPHA_TEST_PACK_001.md)
2. run the quickstart
3. tell us:
   - what felt useful
   - what felt ceremonial
   - whether the saved loss was real or vague

### Mode B — 45-minute teardown

1. read [EXTERNAL_CRITIQUE_PACK_001.md](./EXTERNAL_CRITIQUE_PACK_001.md)
2. read [TECHNICAL_MAP_001.md](./TECHNICAL_MAP_001.md)
3. read [KNOWN_WEAKNESSES_001.md](./KNOWN_WEAKNESSES_001.md)
4. inspect the code and fixtures they care about
5. tell us where the kernel still looks strict by form but weak by substance

## Exact Questions To Ask

Use these questions verbatim if helpful:

1. What part of this product do you trust the least?
2. Which command in the first-run contour feels least justified?
3. Where does the shell still sound more certain than the product has actually earned?
4. What exactly do you lose without `Synrail` in the false-success scenario?
5. What exactly do you gain with `Synrail` in the restore/re-entry scenario?
6. If you had to cut this product in half, what would survive?

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
2. the command where they got stuck or rolled their eyes
3. one sentence on what `Synrail` actually saved them from
4. one sentence on what still felt like process overhead
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
