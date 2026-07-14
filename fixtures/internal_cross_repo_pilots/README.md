# Internal Cross-Repository Pilot Evidence

These are three seeded, maintainer-operated dogfood runs captured on
2026-07-14. They test whether Synrail blocks a plausible file-level proof while
an operator-owned behavioral verification profile is red, then accepts the
same bounded task only after the behavior is repaired.

They are deliberately classified as:

```text
evidence_class = INTERNAL_CROSS_REPO_DOGFOOD
claim_scope = NOT_EXTERNAL_EMPIRICAL_EVIDENCE
```

They do not measure naturally occurring agent failure rates, external-user
adoption, or production effectiveness. The defects were intentionally seeded
in disposable clones, and the maintainer operated Synrail and the repairs.

## Captured Runs

| Repository | Ecosystem | Upstream base | Setup | First blocker | Total operator time | Outcome |
| --- | --- | --- | ---: | ---: | ---: | --- |
| `pypa/sampleproject` | Python | `621e4974ca25ce531773def586ba3ed8e736b3fc` | 2.664s | 3.083s | 8.787s | seeded false-green blocked; repaired run accepted |
| `feross/is-buffer` | Node | `ec4bf3415108e8971375e6717ad63dde752faebf` | 43.669s | 3.516s | 50.607s | seeded false-green blocked; repaired run accepted |
| `USBVadik/aws-proof-gated-prompts` | documentation policy | `1329443b37584bcd8ca03589b2660687539b91e2` | 0.301s | 2.529s | 9.367s | seeded false-green blocked; repaired run accepted |

Across this small seeded set, median time to the first blocker was 3.083s and
median total operator time was 9.367s. The Node total is dominated by a 43.669s
one-time dependency setup, so it must not be compared directly with the two
already-runnable contours.

Two repositories had no bounded automatic suggestion and required the
maintainer to choose or add a project-specific test. The Node candidate was
found automatically but narrowed from `npm test` to the existing local
`npm run test-node` lane after operator review. This is evidence that profile
review remains part of setup, not evidence of zero-touch adoption.

The Python pilot installed its disposable target package into the interpreter
running Synrail. It therefore validates virtualenv execution semantics, but it
does not demonstrate automatic discovery of a separate target-project `.venv`.

## What The Pilot Found Before Final Capture

The first attempts exposed two Synrail integration bugs that were fixed before
these clean records were generated:

- non-accepted `synrail check` output still exited with process code `0`;
- `@synrail-python` executed the interpreter realpath and lost virtualenv
  package visibility.

The final records therefore exercise the repaired behavior: non-accepted
checks exit `2`, accepted checks exit `0`, and Python profiles retain the
locked virtualenv invocation while also binding the real executable hash.

## Integrity

Each pilot record is schema-valid and binds the accepted state, project
profile, final result, final report, verification receipts, and the preserved
same-run blocked report by SHA-256. The paired `*-blocked-report.json` files
contain the minimal orchestration verdict needed to verify that binding; they
do not contain verifier stdout/stderr, source content, or absolute local paths.

The automated regression in `tests/test_cross_repo_pilot.py` verifies the
schema, evidence boundary, same-run relation, blocked reason, and report hash.
Use `examples/cross-repo-pilot/` to capture another internal run. Real outside
user evidence belongs in the external alpha process instead.
