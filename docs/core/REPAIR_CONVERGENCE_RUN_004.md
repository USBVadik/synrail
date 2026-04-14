# REPAIR_CONVERGENCE_RUN_004

Run one fresh convergence stop against the current core using a packet that already crossed the max-attempt boundary.

## Purpose

This is a short re-run of the bounded stop path.
We want to confirm that the tightened core still does the right thing when `resume` receives a packet whose repair termination is already `MAX_REPAIR_ATTEMPTS`:
- no new blind repair attempt
- no phantom repair-history growth
- clear blocked result at `resume`

## Canonical artifacts

- `fixtures/repair_convergence_run_003/starting_state.json`
- `fixtures/repair_convergence_run_003/stage0_repair_packet.json`
- `fixtures/repair_convergence_run_004/report.json`
- `fixtures/repair_convergence_run_004/orchestration.json`
- `fixtures/repair_convergence_run_004/run.json`
- `fixtures/repair_convergence_run_004/repair_packet.json`

## Expected reading

The rerun should stop immediately with `MAX_REPAIR_ATTEMPTS` and preserve the bounded repair-history chain without inventing an extra attempt.
