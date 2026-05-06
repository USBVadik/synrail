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

### 1. Attack the public proof surfaces first

Read:

- `README.md`
- `examples/false-green-demo/README.md`
- `examples/false-green-benchmark/README.md`
- `docs/review/PUBLIC_LAUNCH_PACKET_001.md`

Ask:

- does the first screen make the false-green wedge obvious fast enough?
- does the runnable demo show a real blocked-to-accepted contour, or only a polished narrative?
- does the benchmark starter stay honest about being curated local evidence instead of implying empirical proof?
- does the launch copy overclaim beyond the current narrow local alpha lane?

### 2. Attack the first-run alpha contour

Read:

- `docs/core/ALPHA_TEST_PACK_001.md`
- `fixtures/alpha_test_pack_run_004/`
- `tests/test_alpha_test_pack_smoke.py`

Ask:

- does this feel like a product or a supervised artifact ritual?
- which visible step in the everyday lane feels least worth its weight?
- where does the shell still sound more certain than the current proof has earned?
- is the exported telemetry actually useful?

### 3. Attack false accept / false reject boundaries

Read:

- `tests/test_truth_regressions.py`
- `fixtures/semantic_proof_hardening_run_001/`
- `fixtures/acceptance_independence_run_001/`
- `tools/reference/synrail_bundle_v0.py`
- `tools/reference/synrail_closure_v0.py`

Ask:

- where could a weak proof still pass?
- where could a legitimate contour still be blocked?
- where can numeric line/location claims still sound evidentiary without literal evidence?
- where do allowlisted verification recheck and `shadow_observation_guard_results` still leave too much trust self-issued?

### 4. Attack doctor honesty

Read:

- `tools/reference/synrail_doctor_v1.py`
- `tools/reference/synrail_doctor_coverage_v0.py`
- `fixtures/doctor_measured_coverage_run_001/`

Ask:

- is measured coverage really enough to justify the readiness claim?
- what important fail modes are still missing?

### 5. Attack continuation trust

Read:

- `tools/reference/synrail_repair_packet_v0.py`
- `tools/reference/synrail_continuation_arbiter_v0.py`
- `fixtures/continuation_arbiter_conflict_run_001/`
- `tests/test_claim_validation_pack.py`

Ask:

- can a second operator really follow this without author memory?
- when conflict exists, does the system resolve it convincingly?
- does restore or handoff create concrete value over a simpler substitute?

## Questions we want answered bluntly

1. Which step in the everyday lane feels least worth its weight?
2. Which runtime artifact or proof claim still looks self-issued?
3. Where would a second operator still need author memory during restore or handoff?
4. What concrete value, if any, does `Synrail` add over a simpler substitute in restore or re-entry?
5. If that value is not yet strong enough, what would you cut first?

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
