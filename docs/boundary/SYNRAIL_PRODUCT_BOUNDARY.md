# SYNRAIL_PRODUCT_BOUNDARY

## Purpose

Define what `Synrail` is, what `Synrail` is not, and what must remain outside the product core when the project is eventually extracted into its own repository.

This document exists to prevent a premature extraction that would mix:

- product kernel
- environment adapters
- downstream bot specifics
- historical debugging residue

## Product definition

`Synrail` is a proof-first control kernel for coding agents operating in dirty real environments.

Its job is not to be the downstream bot.

Its job is to decide whether agent execution, promotion, correction, evaluation, and retry are trustworthy enough to accept.

## What belongs to the Synrail core

The following belong to the product core:

- proof discipline
- artifact truth discipline
- baseline identity discipline
- anti-false-success logic
- failure classification
- failure-memory conversion
- retry/recovery semantics
- `Safe Promotion`
- `Formal Validation`
- `Refactor Safety Controls`
- `Agent Correction Controls`
- `Self Evolution Controls`
- `Synrail Doctor`
- `Synrail Doctor Record Spec`
- doctor verdict logic
- exact-task acceptance semantics
- promotion candidate / artifact identity rules

## What belongs to the Synrail product shell later

These may belong to a future product shell, but are not required to define the core:

- operator-facing health display
- user-facing explanation surface
- benchmark / comparison display
- later UI
- future evaluation kernel
- future guided improvement layer

These are valid growth paths, but not extraction prerequisites for the kernel itself.

## What does not belong to the Synrail core

The following do **not** belong to the core:

- one downstream bot or product as the product
- Telegram bot behavior as a product
- `ccgram`
- one host topology's specifics
- one target-runtime topology's specifics
- one-off shell probes
- temporary transport workarounds
- temporary helper contamination states
- session-specific remote debugging commands
- environment-specific credentials themselves
- ad hoc operational notes that do not change the kernel

## Downstream agent capability layer

The downstream agent may have substantial capability logic that still does **not** belong to the `Synrail` core.

Examples:

- prompt enhancers
- backend/model routing for image generation
- photoreal prompt-class policies
- beauty/editorial/image-quality heuristics
- provider suitability maps for one downstream agent

These may become valuable downstream agent subsystems.

They may also become useful proving-ground scenarios for `Synrail`.

But they are not the proof-first control kernel itself.

`Synrail` may govern whether those systems are trusted enough to claim a fix.

It should not confuse those systems with its own product identity.

## Adapter boundary

`Synrail` should eventually treat runtime environments through adapters rather than through embedded environment truth.

Examples of adapter responsibilities:

- provider/model invocation adapter
- remote execution surface adapter
- artifact collection adapter
- credential-surface adapter
- helper/runtime integrity adapter

The adapter may report environment facts.

The core decides how those facts affect trust, readiness, promotion, and acceptance.

## Current known adapter-like surfaces

From the current project reality, these are adapter-like, not core truth:

- one `Codex -> remote host -> execution agent` transport path
- one remote execution path
- one trusted clean clone path
- Bedrock/Aider invocation path
- helper scripts like `run-aider.sh`
- remote shell/runtime discovery commands

They are useful and important.

But they should not define the product identity.

## What must be treated as a proving ground only

The following should be treated as proving grounds, not as the product:

- `NODE2_IMAGE_TRIGGER_FIX_001`
- one downstream product repo
- live dirty working tree states
- current host auth/credential gaps
- current helper contamination history
- downstream image-generation capability work such as:
  - prompt-enhancer tuning
  - backend suitability routing
  - photoreal realism packs
  - beauty-closeup generation heuristics

These are valuable because they force the kernel to become honest.

They are not the kernel itself.

## Architecture reference

The current coherent architecture map for the kernel now lives in:

- the fuller proving-ground architecture overview remains outside this first cut

This is the main technical overview that ties together the control, evaluation, runtime-truth, progression, transition, recovery, and closure subsystems.

## Extraction rule

When `Synrail` moves to its own repository, the repository should primarily contain:

- core control documents
- core control code
- doctor/evaluation/acceptance logic
- artifact formats
- machine-readable kernel status contract
- adapter interfaces
- bounded reference implementations for adapters

The repository should not primarily contain:

- one downstream bot implementation
- environment-specific shell archaeology
- hardcoded runtime assumptions about one host
- historical debugging narrative as product truth

## Readiness questions before extraction

Before extraction, we should be able to answer clearly:

1. What is the kernel?
2. What is an adapter?
3. What is only a proving ground?
4. What is future shell/UI, not core?
5. What exact artifacts define readiness and acceptance?

If these questions cannot be answered cleanly, extraction is still early.

## Current extraction assessment

Current state:

- kernel identity is becoming clear
- adapter boundary is visible but not yet operationalized fully
- proving-ground residue is still mixed into operational memory
- one minimal kernel extraction cut is now describable explicitly
- one concrete migration map for a later separate repo is now also describable explicitly
- extraction is plausible soon, but not yet fully clean

## Decision rule

Extract `Synrail` only when:

- kernel identity is explicit
- adapter boundary is explicit
- at least one repeatable evaluation lane exists
- doctor verdicts are concrete
- the product can be described without naming one downstream bot as the product itself

Do not extract merely because the artifacts look substantial.

Extract when the product boundary is clean enough that the new repository will represent the kernel rather than the history of one battlefield.
