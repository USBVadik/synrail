# False-Green Demo

This is the shortest public entry to the Synrail wedge.

For the runnable two-minute version, start here:

- [examples/false-green-demo/README.md](false-green-demo/README.md)

## Transcript

```text
Agent: done, tests passed
Synrail: Status: Proof Invalid
Reason: final_result.json is narrative, not machine-readable proof
Next: replace it with structured evidence and rerun synrail check
Agent: repaired final_result.json and ran the real verification
Synrail: Status: Accepted
```

## What this shows

- the agent can sound finished before the proof is trustworthy
- Synrail rejects that false-green state explicitly
- the repair target stays bounded
- only `Status: Accepted` closes the loop

## Next step

If you want the bounded tester handoff after this summary, use the [first tester protocol](../docs/review/FIRST_TESTER_PROTOCOL_001.md).

Feedback should go through the GitHub issue templates:

- `Alpha feedback`
- `False-green case`
- `Confusing output`

## Support boundary

This is a local alpha demo, not a broad production workflow claim.
