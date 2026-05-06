# False-Green Demo

Run it in under two minutes.

This demo shows the narrow Synrail wedge:

1. Agent claims the task is done.
2. The proof is weak or mismatched.
3. `python3 alpha.py check` blocks acceptance.
4. Synrail names the bounded repair step.
5. The proof is repaired and real verification is run.
6. `python3 alpha.py check --clean-surface` reaches `Status: Accepted`.

## Fast path

1. weak proof attempt gets blocked
2. bounded repair names the next move
3. accepted closure appears only after real verification

## Run

```bash
./run_demo.sh
```

## What you should see

- `Synrail: Status: Proof Invalid` or another non-green blocker on the weak proof pass
- a concrete reason, not a vague failure
- a bounded next repair step
- `Status: Accepted` only after the proof and verification match

## Files

- `run_demo.sh` — printable two-minute walkthrough
- `transcript.txt` — short sample terminal transcript

## Next step

If you want the bounded tester handoff after this demo, use the [first tester protocol](../../docs/review/FIRST_TESTER_PROTOCOL_001.md).

Feedback should go through the GitHub issue templates:

- `Alpha feedback`
- `False-green case`
- `Confusing output`

## Support boundary

This is a local alpha demo, not a broad production workflow claim.
