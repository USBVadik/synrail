# SYNRAIL_ADAPTER_INTERFACES

## Purpose

Define the minimal adapter interface model for `Synrail`.

This document exists to move the adapter boundary from "visible in principle" toward "operationalized enough for extraction planning".

## Core rule

Adapters report environment facts.

The kernel decides:

- trust
- readiness
- promotion implications
- acceptance
- recovery implications

Adapters must not silently decide kernel truth.

## Minimal adapter set

### 1. Execution Surface Adapter

Purpose:

- identify the runtime surface for a run
- classify whether it is trusted clean, live observed, or dirty observed

Must be able to report:

- target path
- environment identity
- cleanliness classification
- baseline relation

### 2. Provider Invocation Adapter

Purpose:

- report how the downstream model path is invoked

Must be able to report:

- provider/model identity
- invocation path
- whether helper indirection is used or bypassed
- whether the path is reachable

### 3. Credential Surface Adapter

Purpose:

- report whether required credential surface is discoverable for the intended provider/model path

Must be able to report:

- env-based credential presence
- file-based credential presence
- credential absence
- ambiguity if discovery is incomplete
- explicit intended credential source once one has been identified

### 4. Helper Integrity Adapter

Purpose:

- report whether helper entrypoints are trusted, bypassed, contaminated, or unknown

Must be able to report:

- helper identity
- helper source path
- whether direct invocation bypass exists
- contamination/drift status

### 5. Artifact Collection Adapter

Purpose:

- report whether the run can emit the artifacts required by the lane

Must be able to report:

- final JSON viability
- modified-files viability
- diff/provenance viability
- cleanup-status viability

## Interface output shape

Each adapter should eventually expose a report shaped like:

```yaml
adapter_id: execution_surface_adapter
target: /tmp/usbagent_clean_clone
status: PASS
facts:
  classification: trusted_clean_path
  baseline_relation: trusted_baseline
notes:
  - explicit path identity confirmed
blocking_failure_classes: []
```

The exact serialization can change later.

The important requirement is:

- explicit status
- explicit facts
- explicit blockers

## Known current mappings

Current project reality already suggests mappings:

- `Codex -> Hetzner -> Gemini` transport path
  - execution-surface / provider-adjacent adapter concern
- trusted clean clone path on Node 2
  - execution-surface adapter concern
- direct Aider invocation
  - provider invocation adapter concern
- Bedrock credential checks
  - credential surface adapter concern
- contaminated `run-aider.sh` history
  - helper integrity adapter concern
- JSON / cleanup-status artifact expectations
  - artifact collection adapter concern

## Decision rule

The adapter boundary is operationalized enough for extraction planning when:

- the minimal adapter set is named
- each adapter has a clear responsibility
- each adapter reports facts instead of deciding acceptance

This is still not the same as a full implementation.

But it is enough to stop treating adapter concerns as implicit ambient knowledge.
