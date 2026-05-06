# Deploy Guard Examples

These examples show the current **guard-first side-effect pattern** in copyable form.

They are intentionally narrow.

They do **not** promote the current alpha lane into full remote execution support.

Use them when:

- one local `Synrail` run already reached accepted closure
- a later shell step wants to perform a bounded side effect
- you want the side effect to stop on stale closure, stale run id, or stale target identity

Included examples:

- `deploy_with_synrail_guard.sh`
  - explicit guard before file sync and again before restart
- `deploy_with_synrail_wrapper.sh`
  - uses the wrapper helper for each side effect
- `pm2_pre_restart_with_synrail.sh`
  - smallest host-local restart gate
- `systemd_restart_with_synrail.sh`
  - smallest host-local guarded `systemctl restart` example
- `systemd_service_override.conf`
  - example `systemd` drop-in showing `ExecStartPre` with the Synrail deploy guard

## Next step

If you want the bounded tester handoff after reviewing these deploy-guard examples, use the [first tester protocol](../../docs/review/FIRST_TESTER_PROTOCOL_001.md).

Feedback should go through the GitHub issue templates:

- `Alpha feedback`
- `Confusing output`
- `Bug report`

Related docs:

- [`docs/core/DEPLOY_GUARD_INTEGRATION_001.md`](../../docs/core/DEPLOY_GUARD_INTEGRATION_001.md)
- [`tools/reference/synrail_deploy_guard.sh`](../../tools/reference/synrail_deploy_guard.sh)
- [`tools/reference/synrail_guarded_side_effect_v0.sh`](../../tools/reference/synrail_guarded_side_effect_v0.sh)
