# Deploy Guard Integration 001

This document describes the current **guard-first side-effect pattern** for `Synrail`.

It is intentionally narrow.

It does **not** turn the current alpha lane into a first-class remote or production execution lane.

What it does provide is one reusable rule:

- no deploy or restart side effect should run unless the current `Synrail` run is still accepted

## What This Pattern Is For

Use this when:

- the agent acts on one local trusted worktree
- closure happens locally under `Synrail`
- a later shell script wants to perform a side effect:
  - `rsync`
  - `scp`
  - `ssh ... pm2 restart`
  - `systemctl restart`
  - any other deploy or restart step

The value is simple:

- a once-authorized receipt should not survive a later regression
- a stale run id should not authorize a fresh side effect
- a stale target identity should not authorize the wrong target

## What This Pattern Does Not Claim

It does **not** mean:

- remote execution is now a first-class supported alpha lane
- remote proof capture is solved
- remote restore and reconcile are solved
- arbitrary manual restarts on arbitrary hosts are governed automatically

The current supported claim is smaller:

- `Synrail` now provides one reusable deploy-authorization boundary for external side-effect scripts

## Required Runtime Truth

Before any side effect is allowed, the guard requires:

- `deploy_receipt.json` exists
- receipt result is `DEPLOY_AUTHORIZED`
- current `state.json` still says `CLOSURE_ACCEPTED`
- receipt `run_id` matches the current run
- receipt `target_identity` exists
- current `target_identity.txt` exists
- receipt target identity matches the current target identity

If any of these drift, side effect must stop.

## Provided Helpers

Current reusable helpers:

- [`tools/reference/synrail_deploy_guard.sh`](../../tools/reference/synrail_deploy_guard.sh)
- [`tools/reference/synrail_guarded_side_effect_v0.sh`](../../tools/reference/synrail_guarded_side_effect_v0.sh)
- [`examples/deploy_guard/README.md`](../../examples/deploy_guard/README.md)
- [`examples/deploy_guard/systemd_service_override.conf`](../../examples/deploy_guard/systemd_service_override.conf)

## Smallest Manual Pattern

```bash
ARTIFACT_ROOT=".synrail"

synrail deploy --artifact-root "$ARTIFACT_ROOT" --deploy-target "$(cat "$ARTIFACT_ROOT/target_identity.txt")"
tools/reference/synrail_deploy_guard.sh --artifact-root "$ARTIFACT_ROOT"
rsync ...
ssh remote-host 'pm2 restart my-app'
```

This is the simplest explicit split:

1. authorize deploy
2. re-check authorization immediately before side effect
3. only then run the side effect

## Wrapped Side-Effect Pattern

Use the wrapper when you want one guarded command:

```bash
tools/reference/synrail_guarded_side_effect_v0.sh --artifact-root ".synrail" -- rsync -avz ./ remote:/srv/app/
tools/reference/synrail_guarded_side_effect_v0.sh --artifact-root ".synrail" -- ssh remote-host 'pm2 restart my-app'
```

This keeps the shell script simpler and makes the guard harder to “forget”.

## PM2 / Restart Script Pattern

For a deploy shell script, the current recommended pattern is:

1. check the guard before any file copy or backup
2. perform the bounded side effect
3. check the guard again immediately before restart

Minimal shape:

```bash
SYNRAIL_ARTIFACT_ROOT="${SYNRAIL_ARTIFACT_ROOT:-/root/.synrail}"
SYNRAIL_GUARD="${SYNRAIL_GUARD:-/path/to/synrail_deploy_guard.sh}"

echo "Checking Synrail deploy authorization..."
"$SYNRAIL_GUARD" --artifact-root "$SYNRAIL_ARTIFACT_ROOT"

rsync -avz ./ remote:/srv/app/

echo "Re-checking Synrail deploy authorization before restart..."
"$SYNRAIL_GUARD" --artifact-root "$SYNRAIL_ARTIFACT_ROOT"

ssh remote-host 'pm2 restart my-app'
```

This is the current productized pattern.

The exact host paths, process names, and deploy layout are still environment-specific integration details.

## systemd Shape

The same rule applies to `systemctl restart`:

```bash
tools/reference/synrail_guarded_side_effect_v0.sh --artifact-root ".synrail" -- ssh remote-host 'systemctl restart my-app'
```

Or in a host-local script:

```bash
tools/reference/synrail_deploy_guard.sh --artifact-root ".synrail"
systemctl restart my-app
```

Copyable examples now live in:

- [`examples/deploy_guard/systemd_restart_with_synrail.sh`](../../examples/deploy_guard/systemd_restart_with_synrail.sh)
- [`examples/deploy_guard/systemd_service_override.conf`](../../examples/deploy_guard/systemd_service_override.conf)

## Review Boundary

Treat this integration as:

- productized side-effect gating

Do not treat it as:

- full remote lane support

That larger claim would require:

- remote target attestation as a first-class lane
- remote proof capture
- remote restore / reconcile truth
- remote second-operator and replay guarantees

Those are still outside the current alpha support boundary.
