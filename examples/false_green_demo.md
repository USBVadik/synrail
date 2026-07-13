# False-Green Demo

This is the shortest public entry to the Synrail wedge.

For the runnable two-minute version, start here:

- [examples/false-green-demo/README.md](false-green-demo/README.md)

## Transcript

```text
Agent: fixed add(); tests pass
Agent proof: grep found the new fast-path line
Verification unit: FAIL (exit 1)
Synrail: Status: Verification Failed
Agent: repaired the behavior, not the story
Verification unit: GREEN
Synrail: Status: Accepted
```

## What this shows

- structurally valid proof can coexist with behavior that is still wrong
- an operator-owned Verification Profile rejects that false-green state
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
