# Synrail Documentation

Use this page to avoid treating the repository's research history as a setup
manual.

## Current User Path

Read these in order:

1. [`../README.md`](../README.md) - what Synrail is and whether it fits your workflow
2. [`core/FIRST_RUN_GUIDE.md`](core/FIRST_RUN_GUIDE.md) - install plus the smallest useful route
3. [`advanced/VERIFICATION_PROFILES.md`](advanced/VERIFICATION_PROFILES.md) - only when an agent must claim a test or runtime result
4. [`advanced/REPO_CLEAN_WORKFLOWS.md`](advanced/REPO_CLEAN_WORKFLOWS.md) - only for multi-repo QA, external artifacts, or Windows details

Most first runs need only the README and First Run Guide.

## Maintainer And Deep Reference

These files explain implementation boundaries; they are not required to install
or use the normal local lane:

- [`core/SYNRAIL_RUNTIME_TRUTH_SURFACE.md`](core/SYNRAIL_RUNTIME_TRUTH_SURFACE.md) - runtime truth model
- [`core/SYNRAIL_KERNEL_STATUS_CONTRACT.md`](core/SYNRAIL_KERNEL_STATUS_CONTRACT.md) - accepted and non-green status contracts
- [`core/SYNRAIL_EVIDENCE_PRECEDENCE.md`](core/SYNRAIL_EVIDENCE_PRECEDENCE.md) - competing evidence sources
- [`core/SYNRAIL_DOCTOR.md`](core/SYNRAIL_DOCTOR.md) - doctor/readiness implementation
- [`reference/`](reference/) - narrow technical reference material

## Historical Review And Research

[`review/README.md`](review/README.md) indexes audits, roadmaps, external
feedback, launch materials, and prior execution records. [`boundary/`](boundary/)
contains earlier product-boundary and extraction work. They are preserved as
evidence and maintainer history, not as the public onboarding path.
