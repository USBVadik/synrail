# CONTINUATION_AUTONOMY_001

## Goal

Strengthen packet-first continuation so a second operator can recover the current contour without author memory.

This cycle does not add new continuation families or richer history layers.

It hardens three already-existing surfaces:

- repair packet
- session export
- session replay

## What changed

### 1. Repair packet now carries explicit source-of-truth precedence

`repair_packet.json` now includes one runtime-owned `source_of_truth` contract:

- authoritative entry artifacts: `state_file`, `repair_packet`
- explicit precedence: `state_file -> repair_packet -> repair_receipt -> repair_history_chain`
- artifact roles
- freshness rule
- contradiction rule
- packet replay readiness

This makes precedence inspectable in the runtime artifact itself instead of only in kernel docs.

### 2. Continuation core now exposes packet-first replay readiness

`continuation_core` now includes:

- `authoritative_entry_artifacts`
- `source_of_truth_precedence`
- `packet_replay_ready`

This is the minimum extra truth a second operator needs to understand why the packet is sufficient for the current retry path.

### 3. Session export now carries continuation truth

`session-export` is now a thin CLI surface over the existing observability layer.

The exported record now carries:

- entry artifacts
- source-of-truth precedence
- whether packet replay is ready
- whether a latest repair receipt is available

### 4. Session replay now carries continuation summary

`telemetry export` now preserves the same packet-first continuation summary in `session_replay.json`.

That means replay is no longer only:

- command sequence
- latest blocker

It also preserves:

- what artifacts are authoritative
- what order wins on contradiction
- whether packet replay was ready

## Canonical proof

Fixture:

- [continuation_autonomy_run_001](/Users/usbdick/Documents/New%20project/synrail/fixtures/continuation_autonomy_run_001)

Key artifacts:

- [repair_packet.json](/Users/usbdick/Documents/New%20project/synrail/fixtures/continuation_autonomy_run_001/repair_packet.json)
- [session_export.json](/Users/usbdick/Documents/New%20project/synrail/fixtures/continuation_autonomy_run_001/session_export.json)
- [session_replay.json](/Users/usbdick/Documents/New%20project/synrail/fixtures/continuation_autonomy_run_001/session_replay.json)
- [second_operator.json](/Users/usbdick/Documents/New%20project/synrail/fixtures/continuation_autonomy_run_001/second_operator.json)

Key results:

- packet now declares explicit precedence and replay readiness
- session export preserves packet-first continuation truth
- session replay preserves the same continuation summary
- second operator still returns `FOLLOWABLE_BY_SECOND_OPERATOR`

## Why this matters

This cycle reduces author dependence without growing continuation semantics.

Before:

- precedence existed mostly as doc truth and indirect artifact behavior
- replay/export did not surface enough packet-first authority explicitly

After:

- precedence is machine-readable in the packet
- export/replay preserve that truth
- second-operator followability now checks precedence and replay readiness explicitly
