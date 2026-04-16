# Critic Guide 001

If you want to review `Synrail` honestly, do not start by asking whether the architecture looks elegant.

Start by trying to break its truth claims.

## Main critique targets

1. false accept
2. false reject
3. false-ready doctor
4. weak continuation handoff
5. restore/repair ceremony
6. shell usefulness versus simpler substitute workflows

## Suggested attack order

### 1. Attack the first-run alpha contour

Read:

- `docs/core/ALPHA_TEST_PACK_001.md`
- `fixtures/alpha_test_pack_run_004/`
- `tests/test_alpha_test_pack_smoke.py`

Ask:

- does this feel like a product or a supervised artifact ritual?
- is the next step actually obvious?
- is the exported telemetry actually useful?

### 2. Attack false accept / false reject boundaries

Read:

- `tests/test_truth_regressions.py`
- `fixtures/semantic_proof_hardening_run_001/`
- `fixtures/acceptance_independence_run_001/`

Ask:

- where could a weak proof still pass?
- where could a legitimate contour still be blocked?

### 3. Attack doctor honesty

Read:

- `tools/reference/synrail_doctor_v1.py`
- `tools/reference/synrail_doctor_coverage_v0.py`
- `fixtures/doctor_measured_coverage_run_001/`

Ask:

- is measured coverage really enough to justify the readiness claim?
- what important fail modes are still missing?

### 4. Attack continuation trust

Read:

- `tools/reference/synrail_repair_packet_v0.py`
- `tools/reference/synrail_continuation_arbiter_v0.py`
- `fixtures/continuation_arbiter_conflict_run_001/`

Ask:

- can a second operator really follow this without author memory?
- when conflict exists, does the system resolve it convincingly?

## Questions we want answered bluntly

1. What claim here do you trust the least?
2. Which runtime artifact still looks self-issued?
3. Which alpha command would you remove or rename?
4. Where would you expect the first embarrassing false-positive or false-negative in real usage?
5. If you had to cut scope by half, what would survive?

## We prefer these kinds of criticism

Good criticism:

- “this acceptance fingerprint still encodes unstable runtime detail”
- “this shell step is only translating internal state, not helping the operator”
- “this continuation trace still doesn’t explain why source A beat source B”
- “your doctor corpus misses this failure family, so the readiness claim is too strong”

Less useful criticism:

- “it should have a nicer dashboard”
- “it needs more AI features”
- “this could be a platform”

Those may become relevant later.

They are not the current review target.
