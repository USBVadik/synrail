# OBSERVABILITY_BUG_PACKET_001

## Goal

Add one compact bug-packet surface for runtime debugging and issue filing before external alpha.

This cycle does not add a dashboard or hosted telemetry backend.

It adds one bounded export over already-existing runtime artifacts.

## What changed

### 1. New compact bug packet

`synrail bug-packet` now emits one machine-readable record that compresses:

- current state and blocking reason
- acceptance summary
- doctor summary
- continuation summary
- thin-output summary
- observability summary
- artifact inventory

### 2. One issue-ready markdown export

The same command can also emit one issue-ready markdown body.

This means we no longer need to manually assemble:

- latest blocker
- doctor verdict
- continuation step
- packet-first precedence
- artifact availability

for every alpha failure report.

### 3. No new semantics branch

This is strictly an observability/export layer.

It reuses:

- state
- report
- doctor
- repair packet
- observability/session-export
- thin output

## Canonical proof

Fixture:

- [observability_bug_packet_run_002](../../fixtures/observability_bug_packet_run_002)

Key artifacts:

- [bug_packet.json](../../fixtures/observability_bug_packet_run_002/bug_packet.json)
- [github_issue.md](../../fixtures/observability_bug_packet_run_002/github_issue.md)
- [observability.json](../../fixtures/observability_bug_packet_run_002/observability.json)
- [repair_packet.json](../../fixtures/observability_bug_packet_run_002/repair_packet.json)

Key results:

- doctor summary carries final verdict and coverage gate truth
- continuation summary carries packet-first precedence and replay readiness
- observability summary carries repair-attempt and rejection counts
- issue markdown is ready without copying raw artifact contents by hand

## Why this matters

This cycle strengthens two things at once:

- faster debugging for us
- stronger trust signal for external testers and critics

The product now has one compact failure export that explains:

- what failed
- what trusted layers said
- what continuation step was active
- what artifacts are present

without asking the operator to reconstruct the story manually.
