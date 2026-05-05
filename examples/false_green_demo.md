# False-Green Demo

This is the smallest public demo of the Synrail wedge.

## Transcript

```text
Agent: tests passed
Synrail: Status: Proof Invalid
Reason: verification command not executed / freshness mismatch
Next: repair final_result.json
Agent: repaired final_result.json
Synrail: Status: Accepted
```

## What this shows

- the agent can sound finished before the proof is trustworthy
- Synrail rejects that false-green state explicitly
- the repair target stays bounded
- only `Status: Accepted` closes the loop

## Support boundary

This is a local alpha demo, not a broad production workflow claim.
