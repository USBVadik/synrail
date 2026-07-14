# Internal Cross-Repo Pilot Kit

Use this kit to measure Synrail on repositories other than Synrail itself.
It records internal dogfood evidence; it does **not** turn a maintainer-run
exercise into external empirical validation.

## What To Measure

- profile/setup time before `synrail start`
- time to the first useful blocker
- time spent in operator-approved verification
- time to accepted closure, when acceptance is reached
- whether a plausible false-green claim was actually prevented
- manual interventions and confusion moments

## Run One Pilot

1. Use a disposable clone or a branch you can safely modify.
2. Run `synrail suggest-verification`, review the candidate, and commit the
   operator-owned `synrail.toml`.
3. Confirm `synrail preflight` reports `Behavioral verification: READY`.
4. Start one bounded run, make the task change, and record truthful proof.
5. Run `synrail verify`, then `synrail check`. If it prevents a plausible
   false-green claim, preserve that report before repairing:

   ```bash
   cp .synrail/report.json /tmp/pilot-01-blocked-report.json
   ```

6. Perform the bounded repair, rerun verification/check, and preserve the
   final Synrail artifacts until the record is captured.

Capture the result outside the target repository:

```bash
python3 tools/pilots/capture_cross_repo_run.py \
  --project-root /tmp/project \
  --artifact-root /tmp/project/.synrail \
  --output /tmp/pilot-01.json \
  --repository-label sample-project \
  --ecosystem python \
  --task-class bounded-fix \
  --task-summary "Fix the bounded behavior covered by the existing test." \
  --setup-seconds 45.2 \
  --time-to-first-blocker-seconds 61.8 \
  --total-operator-seconds 132.4 \
  --false-green-prevented yes \
  --blocked-report /tmp/pilot-01-blocked-report.json \
  --intervention "Reviewed and committed the suggested verification profile."
```

The capture tool reads only direct regular JSON artifacts. It fails closed on
missing run identity, root mismatch, malformed receipts, symlinks, or an
existing output path. A `yes` false-green outcome requires a preserved blocked
report from the same run. The record stores artifact hashes, not raw verifier
output or absolute local paths.

## Evidence Boundary

Every record is fixed to:

```text
evidence_class = INTERNAL_CROSS_REPO_DOGFOOD
claim_scope = NOT_EXTERNAL_EMPIRICAL_EVIDENCE
```

Do not copy these records into `fixtures/external_alpha_runs` and do not report
their outcomes as outside-user false-green rates. Real external runs still use
the [external alpha run template](../../docs/review/EXTERNAL_ALPHA_RUN_TEMPLATE_001.md).

Three seeded maintainer-run examples, their paired blocked reports, measured
setup/repair timings, and the exact claim boundary are preserved in
[`fixtures/internal_cross_repo_pilots`](../../fixtures/internal_cross_repo_pilots/README.md).
