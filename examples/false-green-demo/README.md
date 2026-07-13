# False-Green Demo

Run it in under two minutes.

This demo shows the narrow Synrail wedge:

1. The operator commits a required unit-test profile in `synrail.toml`.
2. The agent claims the fix is done and records an allowed `grep` proof.
3. The proof is structurally valid, but the required unit test is still red.
4. `synrail verify` records the failure and `synrail check` blocks acceptance.
5. The behavior is repaired and the operator-owned test is rerun.
6. `synrail check` reaches `Status: Accepted` without an operator bypass.

## Fast path

1. plausible proof cannot hide a red required test
2. behavioral repair turns the operator-owned profile green
3. accepted closure appears only after fresh verification

## Run

```bash
./run_demo.sh
```

The script creates a disposable git repository with a buggy function, a real
`unittest`, and a tracked Verification Profile. It invokes the real installed
Synrail CLI to record proof, run the required test, check closure, repair the
behavior, and reverify it. The script asserts both the blocked and accepted
states; this is not a prewritten transcript printer.

## What you should see

- `Verification unit: FAIL (exit 1)` while the agent's convenient proof matches
- `Synrail: Status: Verification Failed` instead of false acceptance
- `Verification unit: GREEN` after the real code repair
- `Synrail: Status: Accepted` only after fresh behavioral verification

## Files

- `run_demo.sh` — executable two-minute proof loop in a disposable project
- `hero.tape` — reproducible VHS source for the public terminal recording
- `transcript.txt` — short sample terminal transcript
- `assets/synrail-false-green-hero.gif` — README-ready animated demo
- `assets/synrail-false-green-hero.mp4` — social/posting version of the same demo
- `assets/synrail-false-green-hero-poster.png` — static preview frame

Regenerate the public recording from this directory with:

```bash
vhs hero.tape
ffmpeg -y -sseof -0.25 \
  -i assets/synrail-false-green-hero.mp4 \
  -frames:v 1 assets/synrail-false-green-hero-poster.png
```

## Next step

If you want the bounded tester handoff after this demo, use the [first tester protocol](../../docs/review/FIRST_TESTER_PROTOCOL_001.md).

Feedback should go through the GitHub issue templates:

- `Alpha feedback`
- `False-green case`
- `Confusing output`

## Support boundary

This is a local alpha demo, not a broad production workflow claim.
