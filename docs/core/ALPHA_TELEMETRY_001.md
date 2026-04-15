# Alpha Telemetry 001

This slice adds one opt-in telemetry path for the current alpha lane.

It is intentionally narrow:

- no hosted backend
- no file contents
- no secret values
- no broad tracing shell

The current telemetry path records only what we need for alpha failures:

- command sequence
- state at error
- component error class
- repair attempt count
- Synrail version and OS
- one GitHub-Issues-ready markdown body

## Commands

Enable telemetry on one artifact root:

```bash
ARTIFACT_ROOT="$(pwd)/.synrail"
synrail start --artifact-root "$ARTIFACT_ROOT" --project-root "$(pwd)" --task-identity "Reject a plain-text final result and keep the repair bounded." --telemetry-opt-in --tester-id alpha_tester_001
```

Or enable it explicitly after `start`:

```bash
synrail telemetry enable --artifact-root "$ARTIFACT_ROOT" --tester-id alpha_tester_001
```

Export one replay plus one issue body:

```bash
synrail telemetry export --artifact-root "$ARTIFACT_ROOT"
```

Use this after a confusing non-green run or when you want to send feedback.
It is not required for the normal repair loop.

This writes:

- `telemetry/command_sequence.jsonl`
- `telemetry/session_replay.json`
- `telemetry/github_issue.md`

## Canonical Run

Canonical telemetry-enabled alpha run:

- [session replay](../../fixtures/alpha_test_pack_run_004/lane/telemetry/session_replay.json)
- [issue body](../../fixtures/alpha_test_pack_run_004/lane/telemetry/github_issue.md)
- [thin output](../../fixtures/alpha_test_pack_run_004/lane/thin_output.json)
- [prompt](../../fixtures/alpha_test_pack_run_004/lane/prompt.json)

What this run proves:

- `Synrail` can collect one bounded alpha replay without leaking artifact contents
- the replay keeps the non-green outcome readable as `PROOF_INVALID`, not raw `OK`
- the exported issue body is already small enough to paste into one GitHub issue without extra cleanup

## Boundaries

This is still provisional alpha telemetry:

- no automatic upload
- no hosted dashboard
- no user-content capture
- no attempt to replace the underlying state, report, prompt, or observability artifacts

The telemetry slice exists only to speed up external alpha feedback.

If telemetry export is still not enough, `synrail bug-packet` is the optional heavier fallback for issue filing.
