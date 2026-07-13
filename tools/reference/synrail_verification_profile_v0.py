#!/usr/bin/env python3
"""Operator-owned verification profiles for Synrail v0.

The operator approves behavioral verification commands once, in
``synrail.toml`` at the project root:

    [verification.unit]
    argv = ["python", "-m", "pytest", "-q"]
    timeout_seconds = 300
    required = true

``synrail start`` locks the parsed config (content hash plus the realpath
of each ``argv[0]``) into the project profile. ``synrail verify``
re-executes the locked commands without a shell and writes HMAC-signed
receipts bound to the run id, the config hash, and a workspace
fingerprint. The orchestration gate refuses acceptance while any required
profile lacks a fresh green receipt, and refuses to continue at all if the
config or a resolved binary changed mid-run.

Same-machine limit: an agent with local write access can still tamper with
project code that the verification command loads (test files, conftest,
sitecustomize). Receipts raise the cost of forgery; the tamper-proof lane
remains CI or another surface the agent cannot write to.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import hmac
import json
import os
import secrets
import shutil
import subprocess
import sys
import time
from pathlib import Path

try:
    from .synrail_safe_git_v0 import SafeGitError, run_safe_git
except ImportError:
    from synrail_safe_git_v0 import SafeGitError, run_safe_git

CONFIG_FILE_NAME = "synrail.toml"
RECEIPTS_FILE_NAME = "verification_receipts.json"
RECEIPT_KEY_FILE_NAME = "receipt_hmac.key"
RECEIPT_SCHEMA_VERSION = "verification_receipt_v0"
LOCK_SCHEMA_VERSION = "verification_profile_lock_v0"

MAX_PROFILES = 16
DEFAULT_TIMEOUT_SECONDS = 300
MAX_TIMEOUT_SECONDS = 3600
OUTPUT_EXCERPT_CHARS = 2000
MAX_UNTRACKED_HASHED_FILES = 200

GATE_PASS = "PASS"
GATE_NOT_CONFIGURED = "NOT_CONFIGURED"
GATE_BLOCKED = "BLOCKED"

VERIFICATION_GATE_REASONS = {
    "VERIFICATION_CONFIG_INVALID",
    "VERIFICATION_CONFIG_CHANGED",
    "VERIFICATION_BINARY_CHANGED",
    "VERIFICATION_RECEIPT_MISSING",
    "VERIFICATION_RECEIPT_INVALID",
    "VERIFICATION_RECEIPT_STALE",
    "VERIFICATION_FAILED",
}


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_json(payload: dict) -> str:
    return json.dumps(payload, sort_keys=True, ensure_ascii=True, separators=(",", ":"))


def config_path(project_root: Path) -> Path:
    return project_root / CONFIG_FILE_NAME


def receipts_path(artifact_root: Path) -> Path:
    return artifact_root / RECEIPTS_FILE_NAME


def receipt_cache_root() -> Path:
    # Mirrors default_cache_root in synrail_cli_v0; duplicated because the
    # CLI imports this module and the key must resolve without that cycle.
    explicit_cache = os.environ.get("SYNRAIL_CACHE_HOME", "").strip()
    if explicit_cache:
        return Path(explicit_cache).expanduser().resolve()
    if sys.platform == "darwin":
        return (Path.home() / "Library" / "Caches" / "synrail").resolve()
    xdg_cache = os.environ.get("XDG_CACHE_HOME", "").strip()
    if xdg_cache:
        return (Path(xdg_cache).expanduser() / "synrail").resolve()
    return (Path.home() / ".cache" / "synrail").resolve()


def _receipt_key(cache_root: Path | None = None) -> bytes:
    root = cache_root or receipt_cache_root()
    key_path = root / RECEIPT_KEY_FILE_NAME
    if key_path.exists():
        return key_path.read_bytes()
    root.mkdir(parents=True, exist_ok=True)
    key = secrets.token_hex(32).encode("ascii")
    key_path.write_bytes(key)
    try:
        key_path.chmod(0o600)
    except OSError:
        pass
    return key


def sign_receipt(receipt: dict, *, cache_root: Path | None = None) -> dict:
    unsigned = {key: value for key, value in receipt.items() if key != "hmac_sha256"}
    signature = hmac.new(
        _receipt_key(cache_root),
        canonical_json(unsigned).encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    signed = dict(unsigned)
    signed["hmac_sha256"] = signature
    return signed


def receipt_signature_valid(receipt: dict, *, cache_root: Path | None = None) -> bool:
    recorded = receipt.get("hmac_sha256", "")
    if not isinstance(recorded, str) or not recorded:
        return False
    unsigned = {key: value for key, value in receipt.items() if key != "hmac_sha256"}
    expected = hmac.new(
        _receipt_key(cache_root),
        canonical_json(unsigned).encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(recorded, expected)


def load_verification_config(project_root: Path) -> dict:
    """Parse synrail.toml into normalized profiles plus a canonical hash."""
    path = config_path(project_root)
    if not path.exists():
        return {"status": "ABSENT", "profiles": {}, "config_sha256": ""}
    try:
        raw_bytes = path.read_bytes()
    except OSError as exc:
        return _config_error("VERIFICATION_CONFIG_UNREADABLE", str(exc))
    try:
        import tomllib

        parsed = tomllib.loads(raw_bytes.decode("utf-8"))
    except (UnicodeDecodeError, ValueError) as exc:
        return _config_error("VERIFICATION_CONFIG_PARSE_ERROR", str(exc))
    section = parsed.get("verification", {})
    if not isinstance(section, dict):
        return _config_error("VERIFICATION_CONFIG_PARSE_ERROR", "[verification] must be a table of profiles")
    if not section:
        return {"status": "ABSENT", "profiles": {}, "config_sha256": ""}
    if len(section) > MAX_PROFILES:
        return _config_error(
            "VERIFICATION_CONFIG_PARSE_ERROR",
            f"at most {MAX_PROFILES} verification profiles are supported",
        )
    profiles: dict[str, dict] = {}
    for name, entry in section.items():
        normalized, error_detail = _normalize_profile_entry(name, entry)
        if error_detail:
            return _config_error("VERIFICATION_CONFIG_PARSE_ERROR", error_detail)
        profiles[name] = normalized
    return {
        "status": "OK",
        "profiles": profiles,
        "config_sha256": sha256_bytes(canonical_json({"verification": profiles}).encode("utf-8")),
    }


def _config_error(reason: str, detail: str) -> dict:
    return {"status": "ERROR", "reason": reason, "detail": detail, "profiles": {}, "config_sha256": ""}


def _normalize_profile_entry(name: str, entry: object) -> tuple[dict, str]:
    if not isinstance(name, str) or not name.strip():
        return {}, "verification profile names must be non-empty strings"
    if not isinstance(entry, dict):
        return {}, f"verification profile '{name}' must be a table"
    argv = entry.get("argv")
    if not isinstance(argv, list) or not argv or not all(isinstance(item, str) and item.strip() for item in argv):
        return {}, f"verification profile '{name}' needs argv as a non-empty list of non-empty strings"
    timeout_raw = entry.get("timeout_seconds", DEFAULT_TIMEOUT_SECONDS)
    if isinstance(timeout_raw, bool) or not isinstance(timeout_raw, int):
        return {}, f"verification profile '{name}' timeout_seconds must be an integer"
    timeout = min(max(timeout_raw, 1), MAX_TIMEOUT_SECONDS)
    required = entry.get("required", True)
    if not isinstance(required, bool):
        return {}, f"verification profile '{name}' required must be a boolean"
    unknown = sorted(set(entry) - {"argv", "timeout_seconds", "required"})
    if unknown:
        return {}, f"verification profile '{name}' has unsupported keys: {', '.join(unknown)}"
    return {"argv": list(argv), "timeout_seconds": timeout, "required": required}, ""


def _resolve_argv0(argv0: str, *, project_root: Path) -> str:
    candidate = Path(argv0)
    if not candidate.is_absolute() and (os.sep in argv0 or "/" in argv0):
        candidate = project_root / candidate
    if candidate.is_absolute() or (os.sep in argv0 or "/" in argv0):
        if candidate.exists() and os.access(candidate, os.X_OK):
            return str(candidate.resolve())
        return ""
    located = shutil.which(argv0)
    if not located:
        return ""
    return str(Path(located).resolve())


def lock_verification_profiles(project_root: Path) -> dict:
    """Snapshot the config for one run; called once at controlled start."""
    config = load_verification_config(project_root)
    if config["status"] == "ABSENT":
        return {"schema_version": LOCK_SCHEMA_VERSION, "present": False}
    if config["status"] == "ERROR":
        return {
            "schema_version": LOCK_SCHEMA_VERSION,
            "present": False,
            "status": "ERROR",
            "reason": config["reason"],
            "detail": config["detail"],
        }
    locked_profiles: dict[str, dict] = {}
    for name, profile in config["profiles"].items():
        realpath = _resolve_argv0(profile["argv"][0], project_root=project_root)
        if not realpath:
            return {
                "schema_version": LOCK_SCHEMA_VERSION,
                "present": False,
                "status": "ERROR",
                "reason": "VERIFICATION_BINARY_UNRESOLVED",
                "detail": f"verification profile '{name}' argv[0] '{profile['argv'][0]}' does not resolve to an executable",
            }
        locked_profiles[name] = dict(profile, argv0_realpath=realpath)
    return {
        "schema_version": LOCK_SCHEMA_VERSION,
        "present": True,
        "locked_at": now_iso(),
        "config_sha256": config["config_sha256"],
        "profiles": locked_profiles,
    }


def verification_lock_from_profile(project_profile: dict | None) -> dict:
    lock = (project_profile or {}).get("verification_profiles")
    if isinstance(lock, dict):
        return lock
    # Runs started before verification profiles existed carry no lock.
    return {"schema_version": LOCK_SCHEMA_VERSION, "present": False, "prelock_run": True}


def _artifact_relative_prefix(project_root: Path, artifact_root: Path | None) -> str:
    if artifact_root is None:
        return ""
    try:
        relative = artifact_root.resolve().relative_to(project_root.resolve())
    except ValueError:
        return ""
    return relative.as_posix().rstrip("/") + "/"


def workspace_fingerprint(project_root: Path, *, artifact_root: Path | None = None) -> dict:
    """Bind receipts to HEAD plus tracked and untracked worktree content.

    Synrail's own artifact root mutates on every check, so it is excluded
    from the untracked and status surfaces to keep receipts comparable.
    """
    try:
        head = run_safe_git(project_root, ["rev-parse", "HEAD"])
        if head.returncode != 0:
            return {"git": False}
        diff = run_safe_git(project_root, ["diff", "HEAD", "--binary"], timeout=60)
        status = run_safe_git(project_root, ["status", "--porcelain"], timeout=60)
        untracked = run_safe_git(project_root, ["ls-files", "--others", "--exclude-standard"], timeout=60)
        if diff.returncode != 0 or status.returncode != 0 or untracked.returncode != 0:
            return {"git": False}
    except SafeGitError:
        return {"git": False}
    excluded_prefix = _artifact_relative_prefix(project_root, artifact_root)

    def excluded(relative: str) -> bool:
        if not excluded_prefix:
            return False
        normalized = relative.strip().strip('"')
        return normalized.startswith(excluded_prefix) or normalized.rstrip("/") + "/" == excluded_prefix

    status_lines = [
        line
        for line in status.stdout.splitlines()
        if line.strip() and not excluded(line[3:] if len(line) > 3 else line)
    ]
    untracked_paths = [line for line in untracked.stdout.splitlines() if line.strip() and not excluded(line)]
    untracked_digest = hashlib.sha256()
    hashed_untracked_contents = len(untracked_paths) <= MAX_UNTRACKED_HASHED_FILES
    for relative in sorted(untracked_paths):
        untracked_digest.update(relative.encode("utf-8", errors="replace") + b"\0")
        if not hashed_untracked_contents:
            continue
        candidate = project_root / relative
        try:
            untracked_digest.update(sha256_file(candidate).encode("ascii") + b"\0")
        except OSError:
            untracked_digest.update(b"unreadable\0")
    return {
        "git": True,
        "head_commit": head.stdout.strip(),
        "diff_sha256": sha256_bytes(diff.stdout.encode("utf-8", errors="replace")),
        "status_sha256": sha256_bytes("\n".join(status_lines).encode("utf-8", errors="replace")),
        "untracked_sha256": untracked_digest.hexdigest(),
        "untracked_contents_hashed": hashed_untracked_contents,
    }


def fingerprints_match(recorded: object, current: object) -> bool:
    if not isinstance(recorded, dict) or not isinstance(current, dict):
        return False
    if not recorded.get("git", False) or not current.get("git", False):
        # Without git there is no content binding; freshness degrades to
        # run/config binding only, mirroring the documented weaker no-git lane.
        return recorded.get("git", False) == current.get("git", False)
    return all(
        recorded.get(field, "") == current.get(field, "")
        for field in ["head_commit", "diff_sha256", "status_sha256", "untracked_sha256"]
    )


def _excerpt(payload: bytes) -> str:
    text = payload.decode("utf-8", errors="replace")
    if len(text) <= 2 * OUTPUT_EXCERPT_CHARS:
        return text
    return text[:OUTPUT_EXCERPT_CHARS] + "\n[...output truncated...]\n" + text[-OUTPUT_EXCERPT_CHARS:]


def execute_profile(
    *,
    name: str,
    locked_profile: dict,
    project_root: Path,
    artifact_root: Path,
    run_id: str,
    config_sha256: str,
    cache_root: Path | None = None,
) -> dict:
    """Execute one locked profile without a shell and return a signed receipt."""
    argv = list(locked_profile["argv"])
    locked_realpath = locked_profile.get("argv0_realpath", "")
    current_realpath = _resolve_argv0(argv[0], project_root=project_root)
    if not current_realpath or current_realpath != locked_realpath:
        return {
            "status": "ERROR",
            "reason": "VERIFICATION_BINARY_CHANGED",
            "detail": (
                f"profile '{name}' argv[0] resolves to '{current_realpath or 'nothing'}' "
                f"but was locked to '{locked_realpath}' at start"
            ),
        }
    timed_out = False
    started = time.monotonic()
    try:
        completed = subprocess.run(
            [current_realpath, *argv[1:]],
            cwd=project_root,
            check=False,
            capture_output=True,
            timeout=locked_profile["timeout_seconds"],
        )
        exit_code = completed.returncode
        stdout_bytes = completed.stdout
        stderr_bytes = completed.stderr
    except subprocess.TimeoutExpired as exc:
        timed_out = True
        exit_code = -1
        stdout_bytes = exc.stdout or b""
        stderr_bytes = exc.stderr or b""
    except OSError as exc:
        return {
            "status": "ERROR",
            "reason": "VERIFICATION_EXECUTION_ERROR",
            "detail": f"profile '{name}' could not execute: {exc}",
        }
    duration = round(time.monotonic() - started, 3)
    receipt = {
        "schema_version": RECEIPT_SCHEMA_VERSION,
        "profile": name,
        "run_id": run_id,
        "config_sha256": config_sha256,
        "argv": argv,
        "argv0_realpath": current_realpath,
        "argv0_sha256": sha256_file(Path(current_realpath)),
        "executed_at": now_iso(),
        "duration_seconds": duration,
        "exit_code": exit_code,
        "timed_out": timed_out,
        "stdout_sha256": sha256_bytes(stdout_bytes),
        "stdout_bytes": len(stdout_bytes),
        "stdout_excerpt": _excerpt(stdout_bytes),
        "stderr_sha256": sha256_bytes(stderr_bytes),
        "stderr_bytes": len(stderr_bytes),
        "stderr_excerpt": _excerpt(stderr_bytes),
        "workspace_fingerprint": workspace_fingerprint(project_root, artifact_root=artifact_root),
    }
    return {"status": "OK", "receipt": sign_receipt(receipt, cache_root=cache_root)}


def load_receipts(artifact_root: Path) -> dict:
    path = receipts_path(artifact_root)
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return {}
    receipts = payload.get("receipts", {})
    return receipts if isinstance(receipts, dict) else {}


def save_receipts(artifact_root: Path, receipts: dict) -> Path:
    path = receipts_path(artifact_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {"schema_version": "verification_receipts_v0", "receipts": receipts},
            indent=2,
            ensure_ascii=True,
        )
        + "\n"
    )
    return path


def run_verification_profiles(
    *,
    project_root: Path,
    artifact_root: Path,
    lock: dict,
    run_id: str,
    profile_names: list[str] | None = None,
    cache_root: Path | None = None,
) -> dict:
    """Execute locked profiles, persist receipts, and summarize outcomes."""
    if not lock.get("present", False):
        return {"status": "ERROR", "reason": "VERIFICATION_NOT_CONFIGURED", "detail": "no verification profiles were locked at start"}
    live = load_verification_config(project_root)
    if live["status"] != "OK" or live["config_sha256"] != lock.get("config_sha256", ""):
        return {
            "status": "ERROR",
            "reason": "VERIFICATION_CONFIG_CHANGED",
            "detail": "synrail.toml no longer matches the config locked at start; start a new run to adopt it",
        }
    locked_profiles = lock.get("profiles", {})
    selected = profile_names or sorted(locked_profiles)
    unknown = [name for name in selected if name not in locked_profiles]
    if unknown:
        return {
            "status": "ERROR",
            "reason": "VERIFICATION_PROFILE_UNKNOWN",
            "detail": "unknown verification profiles: " + ", ".join(sorted(unknown)),
        }
    receipts = load_receipts(artifact_root)
    results = []
    for name in selected:
        outcome = execute_profile(
            name=name,
            locked_profile=locked_profiles[name],
            project_root=project_root,
            artifact_root=artifact_root,
            run_id=run_id,
            config_sha256=lock["config_sha256"],
            cache_root=cache_root,
        )
        if outcome["status"] != "OK":
            return outcome
        receipt = outcome["receipt"]
        receipts[name] = receipt
        results.append(
            {
                "profile": name,
                "exit_code": receipt["exit_code"],
                "timed_out": receipt["timed_out"],
                "duration_seconds": receipt["duration_seconds"],
                "green": receipt["exit_code"] == 0 and not receipt["timed_out"],
            }
        )
    path = save_receipts(artifact_root, receipts)
    return {
        "status": "OK",
        "receipts_file": str(path),
        "results": results,
        "all_green": all(item["green"] for item in results),
    }


def evaluate_verification_gate(
    *,
    project_root: Path,
    artifact_root: Path,
    lock: dict,
    run_id: str,
    cache_root: Path | None = None,
) -> dict:
    """Judge whether required profiles hold fresh green receipts for this run."""
    live = load_verification_config(project_root)
    if not lock.get("present", False):
        if lock.get("status", "") == "ERROR":
            return _gate_block(
                "VERIFICATION_CONFIG_INVALID",
                lock.get("detail", "the verification config failed to lock at start"),
                "fix synrail.toml, then start a new run",
            )
        if live["status"] == "OK":
            return _gate_block(
                "VERIFICATION_CONFIG_CHANGED",
                "synrail.toml appeared after this run started, so its commands were never locked",
                "start a new run so the verification config is locked at start",
            )
        return {"status": GATE_NOT_CONFIGURED}
    if live["status"] == "ERROR":
        return _gate_block(
            "VERIFICATION_CONFIG_INVALID",
            live.get("detail", "synrail.toml is unreadable"),
            "restore a valid synrail.toml matching the config locked at start",
        )
    if live["status"] == "ABSENT" or live["config_sha256"] != lock.get("config_sha256", ""):
        return _gate_block(
            "VERIFICATION_CONFIG_CHANGED",
            "synrail.toml no longer matches the config locked at start",
            "restore the locked synrail.toml or start a new run to adopt the new config",
        )
    required = {name: profile for name, profile in lock.get("profiles", {}).items() if profile.get("required", True)}
    if not required:
        return {"status": GATE_PASS, "profiles": []}
    receipts = load_receipts(artifact_root)
    current_fingerprint = workspace_fingerprint(project_root, artifact_root=artifact_root)
    checked = []
    for name in sorted(required):
        receipt = receipts.get(name)
        if not isinstance(receipt, dict):
            return _gate_block(
                "VERIFICATION_RECEIPT_MISSING",
                f"required verification profile '{name}' has no receipt for this run",
                "run synrail verify, then rerun synrail check",
            )
        if not receipt_signature_valid(receipt, cache_root=cache_root):
            return _gate_block(
                "VERIFICATION_RECEIPT_INVALID",
                f"the receipt for profile '{name}' failed signature validation",
                "run synrail verify to regenerate the receipt, then rerun synrail check",
            )
        if receipt.get("run_id", "") != run_id or receipt.get("config_sha256", "") != lock.get("config_sha256", ""):
            return _gate_block(
                "VERIFICATION_RECEIPT_MISSING",
                f"the receipt for profile '{name}' belongs to a different run or config",
                "run synrail verify, then rerun synrail check",
            )
        if not fingerprints_match(receipt.get("workspace_fingerprint"), current_fingerprint):
            return _gate_block(
                "VERIFICATION_RECEIPT_STALE",
                f"the workspace changed after profile '{name}' was verified",
                "run synrail verify again on the current workspace, then rerun synrail check",
            )
        if receipt.get("timed_out", False) or receipt.get("exit_code", 1) != 0:
            return _gate_block(
                "VERIFICATION_FAILED",
                f"required verification profile '{name}' is not green (exit {receipt.get('exit_code', 'unknown')})",
                "fix the change until the verification command passes, run synrail verify, then rerun synrail check",
            )
        checked.append(name)
    return {"status": GATE_PASS, "profiles": checked}


def _gate_block(reason: str, detail: str, next_step: str) -> dict:
    return {
        "status": GATE_BLOCKED,
        "blocking_reason": reason,
        "detail": detail,
        "next_step": next_step,
    }


def write_verification_gate_block(*, gate: dict, state_file: Path, report_file: Path) -> None:
    """Persist a blocked verdict in the same shape the bootstrap block uses."""
    try:
        state = json.loads(state_file.read_text())
    except (OSError, json.JSONDecodeError):
        state = {}
    closure = state.setdefault("closure", {})
    closure["status"] = "CLAIMED_NOT_ACCEPTED"
    closure["blocking_reason"] = gate["blocking_reason"]
    closure["next_allowed_transition"] = "VERIFICATION_REFRESH"
    closure["narrow_next_safe_step"] = gate["next_step"]
    closure["missing_sections"] = []
    state["next_safe_step"] = gate["next_step"]
    state_file.write_text(json.dumps(state, indent=2, ensure_ascii=True) + "\n")
    report = {
        "schema_version": "orchestration_report_v0",
        "run_id": state.get("run_id", ""),
        "task_class": state.get("task_class", ""),
        "result": "BLOCKED",
        "stopping_stage": "verification_gate",
        "reason": gate["blocking_reason"],
        "reason_detail": gate["detail"],
        "doctor_verdict": "",
        "resume_applied": False,
        "resume_from_state": "",
        "repair_handoff_applied": False,
        "repair_handoff_from_state": "",
        "repair_handoff_required_inputs": [],
        "missing_continuation_inputs": [],
        "selection_applied": False,
        "selected_mode": "",
        "selected_with_preparation": False,
        "preparation_applied": False,
        "preparation_ready_for_closure": False,
        "bundle_status": state.get("proof_bundle", {}).get("status", ""),
        "closure_status": closure["status"],
        "refresh_applied": False,
        "refresh_resulting_closure_status": "",
        "comparison_applied": False,
        "comparison_verdict": "",
        "repair_termination_status": "",
        "repair_termination_reason": "",
        "repair_attempt_count": 0,
        "repair_max_attempts": 0,
        "repair_no_progress_window": 0,
        "repair_stalled_step_id": "",
        "blockers": [gate["blocking_reason"]],
        "dominant_blocker": gate["blocking_reason"],
        "resulting_state": state.get("state", ""),
        "next_safe_step": gate["next_step"],
    }
    report_file.parent.mkdir(parents=True, exist_ok=True)
    report_file.write_text(json.dumps(report, indent=2, ensure_ascii=True) + "\n")
