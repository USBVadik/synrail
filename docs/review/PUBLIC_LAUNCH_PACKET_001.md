# Public Launch Packet 001

## Twitter/X thread

AI coding agents have a false-green problem.

They say:
"Done. Tests pass."

But often:
- tests did not run
- wrong files changed
- proof is narrative
- handoff state is unclear

I built Synrail as a local acceptance gate between claimed_done and accepted_done.
CI can tell me whether configured jobs passed. Synrail checks whether this agent
run's task-scoped proof actually earned "done".
Demo below.

## LinkedIn post

The hardest part of using coding agents is not generation.
It is knowing when their work is safe to accept.

Synrail is a local acceptance gate that turns agent claims into verifiable closure:
claim -> evidence -> verification -> accept/block/repair.

It complements CI and code review; it does not replace either one.
It is a narrow local alpha lane, not a broad workflow platform.
The wedge is simple: catch false-green closure before it gets accepted as truth.

## GitHub / HN launch blurb

Show HN: Synrail — catches false-green claims from AI coding agents

Synrail is a local acceptance gate for coding-agent work.
It blocks false-green "done" until task-scoped proof is rechecked.

If the proof is weak, mismatched, or unverified, Synrail blocks acceptance and points to one bounded repair step.

Start here:
- README
- false-green demo
- first-run quickstart

## First tester protocol

Use `FIRST_TESTER_PROTOCOL_001.md` as the shareable one-page handoff.

Ask 3-5 people who already use Claude Code, Codex, Cursor, or Aider on real tasks.

Give them this path:

1. Install Synrail.
2. Read the repo README first screen.
3. Run the false-green demo.
4. Try one real small local task.
5. Report the result through the GitHub issue templates.

Route feedback through the GitHub issue templates:
- Alpha feedback
- False-green case
- Confusing output

This handoff is for narrow local alpha signal, not broad product readiness proof.
