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
synrail init --artifact-root "$ARTIFACT_ROOT" --telemetry-opt-in --tester-id alpha_tester_001
```

Or enable it explicitly after `init`:

```bash
synrail telemetry enable --artifact-root "$ARTIFACT_ROOT" --tester-id alpha_tester_001
```

Export one replay plus one issue body:

```bash
synrail telemetry export --artifact-root "$ARTIFACT_ROOT"
```

This writes:

- `telemetry/command_sequence.jsonl`
- `telemetry/session_replay.json`
- `telemetry/github_issue.md`

## Canonical Run

Canonical telemetry-enabled alpha run:

- [session replay](/Users/usbdick/Documents/New%20project/synrail/fixtures/alpha_telemetry_run_001/telemetry/session_replay.json)
- [issue body](/Users/usbdick/Documents/New%20project/synrail/fixtures/alpha_telemetry_run_001/telemetry/github_issue.md)
- [thin output](/Users/usbdick/Documents/New%20project/synrail/fixtures/alpha_telemetry_run_001/thin_output.json)
- [prompt](/Users/usbdick/Documents/New%20project/synrail/fixtures/alpha_telemetry_run_001/prompt.json)

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
