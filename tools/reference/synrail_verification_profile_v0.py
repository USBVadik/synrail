#!/usr/bin/env python3
"""Operator-owned verification profiles for Synrail v0.

The operator approves behavioral verification commands once, in
``synrail.toml`` at the project root:

    [verification.unit]
    argv = ["@synrail-python", "-m", "pytest", "-q"]
    timeout_seconds = 300
    required = true

``synrail start`` locally authenticates the parsed config, its git
provenance, and the path and content of each resolved ``argv[0]``.
``synrail verify`` re-executes the locked commands without a shell, captures
output with bounded memory, performs best-effort descendant cleanup, and writes
HMAC-signed receipts bound to the run id, config, executable, environment
policy, and workspace fingerprint. The orchestration gate refuses
acceptance while any required profile lacks a fresh green receipt and
fails closed if the lock, config, executable, or workspace binding drifts.

Same-machine limit: an agent with local write access can still tamper with
project code that the verification command loads (test files, conftest,
sitecustomize) and can reach the local receipt key when it shares the
operator account. Receipts detect ordinary drift and artifact edits; the
tamper-resistant lane remains CI or another surface the agent cannot write
to.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import hmac
import json
import os
import secrets
import signal
import shutil
import stat
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import BinaryIO

try:
    from .synrail_safe_git_v0 import SafeGitError, run_safe_git
except ImportError:
    from synrail_safe_git_v0 import SafeGitError, run_safe_git

CONFIG_FILE_NAME = "synrail.toml"
SYNRAIL_PYTHON_ARGV0 = "@synrail-python"
RECEIPTS_FILE_NAME = "verification_receipts.json"
RECEIPT_KEY_FILE_NAME = "receipt_hmac.key"
RECEIPT_SCHEMA_VERSION = "verification_receipt_v0"
LOCK_SCHEMA_VERSION = "verification_profile_lock_v0"
ENV_POLICY_VERSION = "verification_env_v0"

MAX_PROFILES = 16
MAX_CONFIG_BYTES = 256 * 1024
MAX_PROFILE_NAME_CHARS = 80
MAX_ARGV_ITEMS = 128
MAX_ARG_CHARS = 4096
DEFAULT_TIMEOUT_SECONDS = 300
MAX_TIMEOUT_SECONDS = 3600
OUTPUT_EXCERPT_BYTES = 2000
OUTPUT_READ_CHUNK_BYTES = 64 * 1024
OUTPUT_DRAIN_TIMEOUT_SECONDS = 2.0
PROCESS_TERMINATION_GRACE_SECONDS = 0.1
MAX_UNTRACKED_HASHED_FILES = 200

GATE_PASS = "PASS"
GATE_NOT_CONFIGURED = "NOT_CONFIGURED"
GATE_BLOCKED = "BLOCKED"

VERIFICATION_GATE_REASONS = {
    "VERIFICATION_LOCK_INVALID",
    "VERIFICATION_CONFIG_INVALID",
    "VERIFICATION_CONFIG_UNTRUSTED",
    "VERIFICATION_CONFIG_CHANGED",
    "VERIFICATION_PROJECT_ROOT_CHANGED",
    "VERIFICATION_BINARY_CHANGED",
    "VERIFICATION_WORKSPACE_UNBOUND",
    "VERIFICATION_WORKSPACE_MUTATED",
    "VERIFICATION_RECEIPT_MISSING",
    "VERIFICATION_RECEIPT_INVALID",
    "VERIFICATION_RECEIPT_STALE",
    "VERIFICATION_FAILED",
}

UNSAFE_ENVIRONMENT_NAMES = {
    "BASH_ENV",
    "CLASSPATH",
    "COVERAGE_PROCESS_START",
    "ENV",
    "JAVA_TOOL_OPTIONS",
    "NODE_OPTIONS",
    "NODE_PATH",
    "NPM_CONFIG_USERCONFIG",
    "PERL5LIB",
    "PERL5OPT",
    "PYTEST_ADDOPTS",
    "PYTHONBREAKPOINT",
    "PYTHONHOME",
    "PYTHONINSPECT",
    "PYTHONPATH",
    "PYTHONSTARTUP",
    "RUBYLIB",
    "RUBYOPT",
    "_JAVA_OPTIONS",
}
UNSAFE_ENVIRONMENT_PREFIXES = ("DYLD_", "GIT_", "LD_")


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


def sha256_regular_file(path: Path) -> str:
    """Hash one regular file without blocking on a configured special file."""
    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0)
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    if hasattr(os, "O_NONBLOCK"):
        flags |= os.O_NONBLOCK
    descriptor = os.open(path, flags)
    try:
        opened = os.fstat(descriptor)
        if not stat.S_ISREG(opened.st_mode):
            raise OSError(f"not a regular file: {path}")
        digest = hashlib.sha256()
        with os.fdopen(descriptor, "rb") as handle:
            descriptor = -1
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()
    finally:
        if descriptor >= 0:
            os.close(descriptor)


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


def sign_verification_lock(lock: dict, *, cache_root: Path | None = None) -> dict:
    unsigned = {key: value for key, value in lock.items() if key != "hmac_sha256"}
    signature = hmac.new(
        _receipt_key(cache_root),
        b"verification-lock\0" + canonical_json(unsigned).encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    signed = dict(unsigned)
    signed["hmac_sha256"] = signature
    return signed


def verification_lock_signature_valid(lock: dict, *, cache_root: Path | None = None) -> bool:
    recorded = lock.get("hmac_sha256", "")
    if not isinstance(recorded, str) or not recorded:
        return False
    unsigned = {key: value for key, value in lock.items() if key != "hmac_sha256"}
    expected = hmac.new(
        _receipt_key(cache_root),
        b"verification-lock\0" + canonical_json(unsigned).encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(recorded, expected)


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


def verification_subprocess_env() -> dict[str, str]:
    """Remove common runtime override/injection variables from profile execution."""
    env = os.environ.copy()
    for key in list(env):
        if key in UNSAFE_ENVIRONMENT_NAMES or key.startswith(UNSAFE_ENVIRONMENT_PREFIXES):
            env.pop(key, None)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["PYTHONNOUSERSITE"] = "1"
    return env


def load_verification_config(project_root: Path) -> dict:
    """Parse synrail.toml into normalized profiles plus a canonical hash."""
    path = config_path(project_root)
    if path.is_symlink():
        return _config_error(
            "VERIFICATION_CONFIG_UNTRUSTED",
            "synrail.toml must be a regular file at the project root, not a symlink or special file",
        )
    if not path.exists():
        return {
            "status": "ABSENT",
            "profiles": {},
            "config_sha256": "",
            "config_file_sha256": "",
        }
    if not path.is_file():
        return _config_error(
            "VERIFICATION_CONFIG_UNTRUSTED",
            "synrail.toml must be a regular file at the project root, not a symlink or special file",
        )
    try:
        raw_bytes = path.read_bytes()
    except OSError as exc:
        return _config_error("VERIFICATION_CONFIG_UNREADABLE", str(exc))
    if len(raw_bytes) > MAX_CONFIG_BYTES:
        return _config_error(
            "VERIFICATION_CONFIG_PARSE_ERROR",
            f"synrail.toml exceeds the {MAX_CONFIG_BYTES}-byte verification config limit",
        )
    try:
        import tomllib

        parsed = tomllib.loads(raw_bytes.decode("utf-8"))
    except (UnicodeDecodeError, ValueError) as exc:
        return _config_error("VERIFICATION_CONFIG_PARSE_ERROR", str(exc))
    section = parsed.get("verification", {})
    if not isinstance(section, dict):
        return _config_error("VERIFICATION_CONFIG_PARSE_ERROR", "[verification] must be a table of profiles")
    if not section:
        return {
            "status": "ABSENT",
            "profiles": {},
            "config_sha256": "",
            "config_file_sha256": sha256_bytes(raw_bytes),
        }
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
        "config_file_sha256": sha256_bytes(raw_bytes),
    }


def _config_error(reason: str, detail: str) -> dict:
    return {
        "status": "ERROR",
        "reason": reason,
        "detail": detail,
        "profiles": {},
        "config_sha256": "",
        "config_file_sha256": "",
    }


def _normalize_profile_entry(name: str, entry: object) -> tuple[dict, str]:
    if not isinstance(name, str) or not name.strip():
        return {}, "verification profile names must be non-empty strings"
    if len(name) > MAX_PROFILE_NAME_CHARS:
        return {}, f"verification profile names may not exceed {MAX_PROFILE_NAME_CHARS} characters"
    if not isinstance(entry, dict):
        return {}, f"verification profile '{name}' must be a table"
    argv = entry.get("argv")
    if not isinstance(argv, list) or not argv or not all(isinstance(item, str) and item.strip() for item in argv):
        return {}, f"verification profile '{name}' needs argv as a non-empty list of non-empty strings"
    if len(argv) > MAX_ARGV_ITEMS:
        return {}, f"verification profile '{name}' exceeds the {MAX_ARGV_ITEMS}-argument limit"
    if any(len(item) > MAX_ARG_CHARS for item in argv):
        return {}, f"verification profile '{name}' has an argument longer than {MAX_ARG_CHARS} characters"
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
    if argv0 == SYNRAIL_PYTHON_ARGV0:
        return str(Path(sys.executable).resolve())
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


def _execution_argv0(argv0: str, *, project_root: Path) -> str:
    """Preserve interpreter environment semantics while identity-locking its target."""
    if argv0 == SYNRAIL_PYTHON_ARGV0:
        candidate = Path(os.path.abspath(sys.executable))
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return str(candidate)
        return ""
    return _resolve_argv0(argv0, project_root=project_root)


def _verification_config_git_provenance(project_root: Path) -> dict:
    """Require the operator profile to be tracked and unchanged from HEAD."""
    path = config_path(project_root)
    try:
        top = run_safe_git(project_root, ["rev-parse", "--show-toplevel"])
        head = run_safe_git(project_root, ["rev-parse", "HEAD"])
    except SafeGitError as exc:
        return {
            "status": "ERROR",
            "reason": "VERIFICATION_CONFIG_UNTRUSTED",
            "detail": exc.detail,
            "next_action": "FIX_GIT_PROVENANCE",
        }
    if top.returncode != 0 or head.returncode != 0:
        return {
            "status": "ERROR",
            "reason": "VERIFICATION_CONFIG_UNTRUSTED",
            "detail": "verification profiles require a git-backed project with an existing HEAD commit",
            "next_action": "INITIALIZE_AND_COMMIT",
        }
    git_root = Path(top.stdout.strip()).resolve()
    try:
        relative = path.resolve().relative_to(git_root).as_posix()
    except ValueError:
        return {
            "status": "ERROR",
            "reason": "VERIFICATION_CONFIG_UNTRUSTED",
            "detail": "synrail.toml must live inside the git repository that owns the controlled run",
            "next_action": "FIX_PROJECT_ROOT",
        }
    try:
        tracked = run_safe_git(project_root, ["ls-files", "--error-unmatch", "--", relative])
        clean = run_safe_git(project_root, ["diff", "--quiet", "HEAD", "--", relative])
    except SafeGitError as exc:
        return {
            "status": "ERROR",
            "reason": "VERIFICATION_CONFIG_UNTRUSTED",
            "detail": exc.detail,
            "next_action": "FIX_GIT_PROVENANCE",
        }
    if tracked.returncode != 0:
        return {
            "status": "ERROR",
            "reason": "VERIFICATION_CONFIG_UNTRUSTED",
            "detail": "synrail.toml must be tracked in git before it can be treated as operator-owned",
            "next_action": "REVIEW_AND_COMMIT",
        }
    if clean.returncode != 0:
        return {
            "status": "ERROR",
            "reason": "VERIFICATION_CONFIG_UNTRUSTED",
            "detail": "synrail.toml must match HEAD at controlled start; commit or restore the operator-approved profile first",
            "next_action": "REVIEW_AND_COMMIT",
        }
    return {
        "status": "OK",
        "git_root": str(git_root),
        "repo_path": relative,
        "head_commit": head.stdout.strip(),
    }


def _live_provenance_matches_lock(project_root: Path, lock: dict) -> dict:
    root_binding = _locked_project_root_matches(project_root, lock)
    if root_binding["status"] != "OK":
        return root_binding
    provenance = _verification_config_git_provenance(project_root)
    if provenance["status"] != "OK":
        return {
            "status": "ERROR",
            "reason": "VERIFICATION_CONFIG_CHANGED",
            "detail": provenance.get("detail", "synrail.toml no longer has trusted git provenance"),
        }
    if (
        provenance.get("head_commit", "") != lock.get("config_git_head", "")
        or provenance.get("git_root", "") != lock.get("config_git_root", "")
        or provenance.get("repo_path", "") != lock.get("config_repo_path", "")
    ):
        return {
            "status": "ERROR",
            "reason": "VERIFICATION_CONFIG_CHANGED",
            "detail": "the git revision or repository path owning synrail.toml changed after controlled start",
        }
    return provenance


def _resolved_binary_state(locked_profile: dict, *, project_root: Path) -> dict:
    argv = locked_profile.get("argv", [])
    if not isinstance(argv, list) or not argv:
        return {"status": "ERROR", "detail": "the locked verification argv is missing"}
    current_realpath = _resolve_argv0(argv[0], project_root=project_root)
    locked_realpath = locked_profile.get("argv0_realpath", "")
    if not current_realpath or current_realpath != locked_realpath:
        return {
            "status": "ERROR",
            "detail": (
                f"argv[0] resolves to '{current_realpath or 'nothing'}' "
                f"but was locked to '{locked_realpath}' at start"
            ),
        }
    execution_path = current_realpath
    if argv[0] == SYNRAIL_PYTHON_ARGV0:
        execution_path = _execution_argv0(argv[0], project_root=project_root)
        locked_execution_path = locked_profile.get("argv0_execution_path", "")
        if not locked_execution_path:
            return {
                "status": "ERROR",
                "detail": "the @synrail-python lock predates virtualenv execution binding; start a new controlled run",
            }
        if execution_path != locked_execution_path:
            return {
                "status": "ERROR",
                "detail": (
                    f"@synrail-python now invokes '{execution_path or 'nothing'}' "
                    f"but was locked to '{locked_execution_path}' at start"
                ),
            }
        if str(Path(execution_path).resolve()) != current_realpath:
            return {
                "status": "ERROR",
                "detail": "the locked @synrail-python invocation no longer resolves to its authenticated binary",
            }
    try:
        current_sha256 = sha256_regular_file(Path(current_realpath))
    except OSError as exc:
        return {"status": "ERROR", "detail": f"the locked verification binary is unreadable: {exc}"}
    locked_sha256 = locked_profile.get("argv0_sha256", "")
    if not locked_sha256 or current_sha256 != locked_sha256:
        return {
            "status": "ERROR",
            "detail": f"the executable content at '{current_realpath}' changed after controlled start",
        }
    return {
        "status": "OK",
        "execution_path": execution_path,
        "realpath": current_realpath,
        "sha256": current_sha256,
    }


def _prepare_verification_profiles(project_root: Path) -> dict:
    """Validate the exact profile inputs that controlled start would lock."""
    config = load_verification_config(project_root)
    if config["status"] == "ABSENT":
        return {"status": "ABSENT", "stage": "config"}
    if config["status"] == "ERROR":
        return {
            "status": "ERROR",
            "stage": "config",
            "reason": config["reason"],
            "detail": config["detail"],
        }
    provenance = _verification_config_git_provenance(project_root)
    if provenance["status"] != "OK":
        return {
            "status": "ERROR",
            "stage": "provenance",
            "reason": provenance["reason"],
            "detail": provenance["detail"],
            "next_action": provenance.get("next_action", "FIX_GIT_PROVENANCE"),
        }
    locked_profiles: dict[str, dict] = {}
    for name, profile in config["profiles"].items():
        execution_path = _execution_argv0(profile["argv"][0], project_root=project_root)
        realpath = _resolve_argv0(profile["argv"][0], project_root=project_root)
        if not execution_path or not realpath:
            return {
                "status": "ERROR",
                "stage": "executable",
                "reason": "VERIFICATION_BINARY_UNRESOLVED",
                "detail": f"verification profile '{name}' argv[0] '{profile['argv'][0]}' does not resolve to an executable",
            }
        try:
            binary_sha256 = sha256_regular_file(Path(realpath))
        except OSError as exc:
            return {
                "status": "ERROR",
                "stage": "executable",
                "reason": "VERIFICATION_BINARY_UNRESOLVED",
                "detail": f"verification profile '{name}' argv[0] could not be hashed: {exc}",
            }
        locked_profiles[name] = dict(
            profile,
            argv0_execution_path=execution_path,
            argv0_realpath=realpath,
            argv0_sha256=binary_sha256,
        )
    return {
        "status": "OK",
        "stage": "ready",
        "config": config,
        "provenance": provenance,
        "profiles": locked_profiles,
    }


def inspect_verification_readiness(project_root: Path) -> dict:
    """Report start-time verification readiness without executing or signing."""
    prepared = _prepare_verification_profiles(project_root)
    if prepared["status"] == "ABSENT":
        return {
            "status": "NOT_CONFIGURED",
            "configured": False,
            "profile_count": 0,
            "required_profile_count": 0,
            "profiles": [],
            "next_action": "CONFIGURE",
        }
    if prepared["status"] == "ERROR":
        stage = prepared.get("stage", "config")
        if stage == "provenance":
            next_action = prepared.get("next_action", "FIX_GIT_PROVENANCE")
        elif stage == "executable":
            next_action = "FIX_EXECUTABLE"
        else:
            next_action = "FIX_CONFIG"
        return {
            "status": (
                "REVIEW_REQUIRED"
                if next_action in {"REVIEW_AND_COMMIT", "INITIALIZE_AND_COMMIT"}
                else "BLOCKED"
            ),
            "configured": True,
            "reason": prepared["reason"],
            "detail": prepared["detail"],
            "profile_count": 0,
            "required_profile_count": 0,
            "profiles": [],
            "next_action": next_action,
        }

    profiles = [
        {
            "name": name,
            "argv0": profile["argv"][0],
            "argv0_execution_path": profile["argv0_execution_path"],
            "argv0_realpath": profile["argv0_realpath"],
            "required": profile["required"],
            "timeout_seconds": profile["timeout_seconds"],
        }
        for name, profile in sorted(prepared["profiles"].items())
    ]
    required_profile_count = sum(1 for profile in profiles if profile["required"])
    if required_profile_count == 0:
        return {
            "status": "REVIEW_REQUIRED",
            "configured": True,
            "reason": "VERIFICATION_NO_REQUIRED_PROFILES",
            "detail": "synrail.toml has no required verification profile, so behavioral acceptance would remain ungated",
            "profile_count": len(profiles),
            "required_profile_count": 0,
            "profiles": profiles,
            "next_action": "MAKE_PROFILE_REQUIRED",
        }
    return {
        "status": "READY",
        "configured": True,
        "profile_count": len(profiles),
        "required_profile_count": required_profile_count,
        "profiles": profiles,
        "config_repo_path": prepared["provenance"]["repo_path"],
        "config_git_head": prepared["provenance"]["head_commit"],
        "next_action": "START",
    }


def lock_verification_profiles(project_root: Path) -> dict:
    """Snapshot the config for one run; called once at controlled start."""
    prepared = _prepare_verification_profiles(project_root)
    if prepared["status"] == "ABSENT":
        return sign_verification_lock(
            {
                "schema_version": LOCK_SCHEMA_VERSION,
                "present": False,
                "locked_at": now_iso(),
                "environment_policy": ENV_POLICY_VERSION,
                "project_root_realpath": str(project_root.resolve()),
            }
        )
    if prepared["status"] == "ERROR":
        return {
            "schema_version": LOCK_SCHEMA_VERSION,
            "present": False,
            "status": "ERROR",
            "reason": prepared["reason"],
            "detail": prepared["detail"],
        }

    config = prepared["config"]
    provenance = prepared["provenance"]
    return sign_verification_lock({
        "schema_version": LOCK_SCHEMA_VERSION,
        "present": True,
        "locked_at": now_iso(),
        "config_sha256": config["config_sha256"],
        "config_file_sha256": config["config_file_sha256"],
        "config_git_head": provenance["head_commit"],
        "config_git_root": provenance["git_root"],
        "config_repo_path": provenance["repo_path"],
        "environment_policy": ENV_POLICY_VERSION,
        "project_root_realpath": str(project_root.resolve()),
        "profiles": prepared["profiles"],
    })


def verification_lock_from_profile(project_profile: dict | None) -> dict:
    lock = (project_profile or {}).get("verification_profiles")
    if isinstance(lock, dict):
        return lock
    # A missing lock cannot be distinguished from an artifact downgrade. Old
    # active runs must restart rather than silently falling back to no gate.
    return {
        "schema_version": LOCK_SCHEMA_VERSION,
        "present": False,
        "status": "ERROR",
        "reason": "VERIFICATION_LOCK_INVALID",
        "detail": "the project profile has no authenticated verification lock; start a new controlled run",
    }


def _locked_project_root_matches(project_root: Path, lock: dict) -> dict:
    current = str(project_root.resolve())
    locked = lock.get("project_root_realpath", "")
    if not isinstance(locked, str) or not locked or current != locked:
        return {
            "status": "ERROR",
            "reason": "VERIFICATION_PROJECT_ROOT_CHANGED",
            "detail": (
                f"the active project root '{current}' does not match the root "
                f"locked at controlled start ('{locked or 'missing'}')"
            ),
        }
    return {"status": "OK"}


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
            return {"git": False, "complete": False, "reason": "git HEAD is unavailable"}
        diff = run_safe_git(project_root, ["diff", "HEAD", "--binary"], timeout=60)
        status = run_safe_git(project_root, ["status", "--porcelain=v1", "-z"], timeout=60)
        untracked = run_safe_git(
            project_root,
            ["ls-files", "-z", "--others", "--exclude-standard"],
            timeout=60,
        )
        if diff.returncode != 0 or status.returncode != 0 or untracked.returncode != 0:
            return {"git": False, "complete": False, "reason": "git workspace inspection failed"}
    except SafeGitError as exc:
        return {"git": False, "complete": False, "reason": exc.detail}
    excluded_prefix = _artifact_relative_prefix(project_root, artifact_root)

    def excluded(relative: str) -> bool:
        if not excluded_prefix:
            return False
        normalized = relative.strip().strip('"')
        return normalized.startswith(excluded_prefix) or normalized.rstrip("/") + "/" == excluded_prefix

    status_records: list[str] = []
    status_tokens = [token for token in status.stdout.split("\0") if token]
    token_index = 0
    while token_index < len(status_tokens):
        record = status_tokens[token_index]
        token_index += 1
        record_parts = [record]
        status_code = record[:2]
        if ("R" in status_code or "C" in status_code) and token_index < len(status_tokens):
            record_parts.append(status_tokens[token_index])
            token_index += 1
        relative = record[3:] if len(record) > 3 else record
        if not excluded(relative):
            status_records.append("\0".join(record_parts))
    untracked_paths = [
        path for path in untracked.stdout.split("\0") if path and not excluded(path)
    ]
    untracked_digest = hashlib.sha256()
    hashed_untracked_contents = len(untracked_paths) <= MAX_UNTRACKED_HASHED_FILES
    untracked_binding_error = ""
    for relative in sorted(untracked_paths):
        untracked_digest.update(relative.encode("utf-8", errors="surrogateescape") + b"\0")
        if not hashed_untracked_contents:
            continue
        candidate = project_root / relative
        if candidate.is_symlink():
            untracked_binding_error = (
                f"visible untracked path '{relative}' is a symlink and cannot be content-bound safely"
            )
            break
        try:
            if not candidate.is_file():
                untracked_binding_error = (
                    f"visible untracked path '{relative}' is not a regular file"
                )
                break
            untracked_digest.update(sha256_file(candidate).encode("ascii") + b"\0")
        except OSError as exc:
            untracked_binding_error = (
                f"visible untracked path '{relative}' could not be content-bound: {exc}"
            )
            break
    complete = hashed_untracked_contents and not untracked_binding_error
    return {
        "git": True,
        "complete": complete,
        "reason": (
            "too many untracked files to bind their contents safely"
            if not hashed_untracked_contents
            else untracked_binding_error
        ),
        "head_commit": head.stdout.strip(),
        "diff_sha256": sha256_bytes(diff.stdout.encode("utf-8", errors="surrogateescape")),
        "status_sha256": sha256_bytes(
            "\0".join(status_records).encode("utf-8", errors="surrogateescape")
        ),
        "untracked_sha256": untracked_digest.hexdigest(),
        "untracked_contents_hashed": complete,
    }


def fingerprints_match(recorded: object, current: object) -> bool:
    if not isinstance(recorded, dict) or not isinstance(current, dict):
        return False
    if not recorded.get("git", False) or not current.get("git", False):
        return False
    if not recorded.get("complete", False) or not current.get("complete", False):
        return False
    return all(
        recorded.get(field, "") == current.get(field, "")
        for field in ["head_commit", "diff_sha256", "status_sha256", "untracked_sha256"]
    )


class _BoundedOutputCapture:
    """Hash an arbitrary stream while retaining only a bounded diagnostic sample."""

    def __init__(self) -> None:
        self.digest = hashlib.sha256()
        self.total_bytes = 0
        self.head = bytearray()
        self.tail = bytearray()
        self.small: bytearray | None = bytearray()
        self.error = ""

    def update(self, chunk: bytes) -> None:
        self.digest.update(chunk)
        self.total_bytes += len(chunk)
        if len(self.head) < OUTPUT_EXCERPT_BYTES:
            remaining = OUTPUT_EXCERPT_BYTES - len(self.head)
            self.head.extend(chunk[:remaining])
        self.tail.extend(chunk)
        if len(self.tail) > OUTPUT_EXCERPT_BYTES:
            del self.tail[:-OUTPUT_EXCERPT_BYTES]
        if self.small is not None:
            self.small.extend(chunk)
            if len(self.small) > 2 * OUTPUT_EXCERPT_BYTES:
                self.small = None

    def excerpt(self) -> str:
        if self.small is not None:
            payload = bytes(self.small)
        else:
            payload = bytes(self.head) + b"\n[...output truncated...]\n" + bytes(self.tail)
        return payload.decode("utf-8", errors="replace")


def _drain_output(stream: BinaryIO, capture: _BoundedOutputCapture) -> None:
    try:
        for chunk in iter(lambda: stream.read(OUTPUT_READ_CHUNK_BYTES), b""):
            capture.update(chunk)
    except (OSError, ValueError) as exc:
        capture.error = str(exc)
    finally:
        try:
            stream.close()
        except OSError:
            pass


def _verification_popen_kwargs() -> dict:
    if os.name == "posix":
        return {"start_new_session": True}
    if os.name == "nt":
        return {"creationflags": getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)}
    return {}


def _terminate_process_tree(process: subprocess.Popen[bytes]) -> None:
    """Best-effort cleanup for the verifier and descendants it started."""
    if os.name == "posix":
        try:
            os.killpg(process.pid, signal.SIGTERM)
        except ProcessLookupError:
            return
        except OSError:
            if process.poll() is None:
                try:
                    process.kill()
                except OSError:
                    pass
            return
        time.sleep(PROCESS_TERMINATION_GRACE_SECONDS)
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        except OSError:
            # The process group can disappear or change ownership between signals.
            if process.poll() is None:
                try:
                    process.kill()
                except OSError:
                    pass
        return
    if os.name == "nt":
        system_root = Path(os.environ.get("SystemRoot", r"C:\Windows"))
        taskkill = system_root / "System32" / "taskkill.exe"
        if taskkill.is_file():
            try:
                subprocess.run(
                    [str(taskkill), "/PID", str(process.pid), "/T", "/F"],
                    check=False,
                    capture_output=True,
                    timeout=5,
                    env=verification_subprocess_env(),
                )
            except (OSError, subprocess.TimeoutExpired):
                pass
    if process.poll() is None:
        try:
            process.kill()
        except OSError:
            pass


def _execute_bounded_process(
    argv: list[str],
    *,
    project_root: Path,
    timeout_seconds: int,
) -> dict:
    stdout_capture = _BoundedOutputCapture()
    stderr_capture = _BoundedOutputCapture()
    try:
        process = subprocess.Popen(
            argv,
            cwd=project_root,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=verification_subprocess_env(),
            **_verification_popen_kwargs(),
        )
    except OSError as exc:
        return {"status": "ERROR", "detail": str(exc)}
    assert process.stdout is not None
    assert process.stderr is not None
    stdout_thread = threading.Thread(
        target=_drain_output,
        args=(process.stdout, stdout_capture),
        daemon=True,
    )
    stderr_thread = threading.Thread(
        target=_drain_output,
        args=(process.stderr, stderr_capture),
        daemon=True,
    )
    stdout_thread.start()
    stderr_thread.start()
    timed_out = False
    try:
        exit_code = process.wait(timeout=timeout_seconds)
    except subprocess.TimeoutExpired:
        timed_out = True
        exit_code = -1
    finally:
        # Verification commands are not allowed to leave background work
        # running after their foreground process has completed or timed out.
        _terminate_process_tree(process)
        try:
            process.wait(timeout=OUTPUT_DRAIN_TIMEOUT_SECONDS)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
    stdout_thread.join(timeout=OUTPUT_DRAIN_TIMEOUT_SECONDS)
    stderr_thread.join(timeout=OUTPUT_DRAIN_TIMEOUT_SECONDS)
    for stream, thread in (
        (process.stdout, stdout_thread),
        (process.stderr, stderr_thread),
    ):
        if thread.is_alive():
            try:
                stream.close()
            except OSError:
                pass
            thread.join(timeout=OUTPUT_DRAIN_TIMEOUT_SECONDS)
    if stdout_thread.is_alive() or stderr_thread.is_alive():
        return {"status": "ERROR", "detail": "verification output pipes did not close after process cleanup"}
    if stdout_capture.error or stderr_capture.error:
        return {
            "status": "ERROR",
            "detail": "verification output capture failed: "
            + (stdout_capture.error or stderr_capture.error),
        }
    return {
        "status": "OK",
        "exit_code": exit_code,
        "timed_out": timed_out,
        "stdout": stdout_capture,
        "stderr": stderr_capture,
    }


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
    binary = _resolved_binary_state(locked_profile, project_root=project_root)
    if binary["status"] != "OK":
        return {
            "status": "ERROR",
            "reason": "VERIFICATION_BINARY_CHANGED",
            "detail": f"profile '{name}' {binary['detail']}",
        }
    current_realpath = binary["realpath"]
    fingerprint_before = workspace_fingerprint(project_root, artifact_root=artifact_root)
    if not fingerprint_before.get("complete", False):
        return {
            "status": "ERROR",
            "reason": "VERIFICATION_WORKSPACE_UNBOUND",
            "detail": (
                f"profile '{name}' cannot bind a complete git workspace fingerprint: "
                f"{fingerprint_before.get('reason', 'workspace inspection is incomplete')}"
            ),
        }
    started = time.monotonic()
    execution = _execute_bounded_process(
        [binary["execution_path"], *argv[1:]],
        project_root=project_root,
        timeout_seconds=locked_profile["timeout_seconds"],
    )
    if execution["status"] != "OK":
        return {
            "status": "ERROR",
            "reason": "VERIFICATION_EXECUTION_ERROR",
            "detail": f"profile '{name}' could not execute safely: {execution['detail']}",
        }
    exit_code = execution["exit_code"]
    timed_out = execution["timed_out"]
    stdout_capture = execution["stdout"]
    stderr_capture = execution["stderr"]
    duration = round(time.monotonic() - started, 3)
    fingerprint_after = workspace_fingerprint(project_root, artifact_root=artifact_root)
    if not fingerprint_after.get("complete", False):
        return {
            "status": "ERROR",
            "reason": "VERIFICATION_WORKSPACE_UNBOUND",
            "detail": (
                f"profile '{name}' could not bind the post-verification workspace: "
                f"{fingerprint_after.get('reason', 'workspace inspection is incomplete')}"
            ),
        }
    if not fingerprints_match(fingerprint_before, fingerprint_after):
        return {
            "status": "ERROR",
            "reason": "VERIFICATION_WORKSPACE_MUTATED",
            "detail": f"profile '{name}' changed tracked or visible untracked workspace content while it ran",
        }
    receipt = {
        "schema_version": RECEIPT_SCHEMA_VERSION,
        "profile": name,
        "run_id": run_id,
        "config_sha256": config_sha256,
        "environment_policy": ENV_POLICY_VERSION,
        "project_root_realpath": str(project_root.resolve()),
        "argv": argv,
        "argv0_execution_path": binary["execution_path"],
        "argv0_realpath": current_realpath,
        "argv0_sha256": binary["sha256"],
        "executed_at": now_iso(),
        "duration_seconds": duration,
        "exit_code": exit_code,
        "timed_out": timed_out,
        "stdout_sha256": stdout_capture.digest.hexdigest(),
        "stdout_bytes": stdout_capture.total_bytes,
        "stdout_excerpt": stdout_capture.excerpt(),
        "stderr_sha256": stderr_capture.digest.hexdigest(),
        "stderr_bytes": stderr_capture.total_bytes,
        "stderr_excerpt": stderr_capture.excerpt(),
        "workspace_fingerprint": fingerprint_after,
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
    if not verification_lock_signature_valid(lock, cache_root=cache_root):
        return {
            "status": "ERROR",
            "reason": "VERIFICATION_LOCK_INVALID",
            "detail": "the verification profile lock failed local signature validation; start a new controlled run",
        }
    provenance = _live_provenance_matches_lock(project_root, lock)
    if provenance["status"] != "OK":
        return provenance
    live = load_verification_config(project_root)
    if (
        live["status"] != "OK"
        or live["config_sha256"] != lock.get("config_sha256", "")
        or live["config_file_sha256"] != lock.get("config_file_sha256", "")
    ):
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
                lock.get("reason", "VERIFICATION_LOCK_INVALID"),
                lock.get("detail", "the verification lock is missing or invalid"),
                "start a new controlled run so Synrail can build an authenticated verification lock",
            )
        if not verification_lock_signature_valid(lock, cache_root=cache_root):
            return _gate_block(
                "VERIFICATION_LOCK_INVALID",
                "the no-profile verification lock failed local signature validation",
                "start a new controlled run so Synrail can rebuild the verification lock",
            )
        root_binding = _locked_project_root_matches(project_root, lock)
        if root_binding["status"] != "OK":
            return _gate_block(
                root_binding["reason"],
                root_binding["detail"],
                "restore the original project root or start a new controlled run there",
            )
        if live["status"] == "OK":
            return _gate_block(
                "VERIFICATION_CONFIG_CHANGED",
                "synrail.toml appeared after this run started, so its commands were never locked",
                "start a new run so the verification config is locked at start",
            )
        return {"status": GATE_NOT_CONFIGURED}
    if not verification_lock_signature_valid(lock, cache_root=cache_root):
        return _gate_block(
            "VERIFICATION_LOCK_INVALID",
            "the verification profile lock failed local signature validation",
            "start a new controlled run so Synrail can rebuild the operator-approved lock",
        )
    provenance = _live_provenance_matches_lock(project_root, lock)
    if provenance["status"] != "OK":
        return _gate_block(
            provenance.get("reason", "VERIFICATION_CONFIG_UNTRUSTED"),
            provenance.get("detail", "synrail.toml no longer has trusted git provenance"),
            "restore the tracked synrail.toml and original HEAD, or start a new controlled run",
        )
    if live["status"] == "ERROR":
        return _gate_block(
            "VERIFICATION_CONFIG_INVALID",
            live.get("detail", "synrail.toml is unreadable"),
            "restore a valid synrail.toml matching the config locked at start",
        )
    if (
        live["status"] == "ABSENT"
        or live["config_sha256"] != lock.get("config_sha256", "")
        or live["config_file_sha256"] != lock.get("config_file_sha256", "")
    ):
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
    if not current_fingerprint.get("complete", False):
        return _gate_block(
            "VERIFICATION_WORKSPACE_UNBOUND",
            "Synrail could not bind a complete git workspace fingerprint: "
            + current_fingerprint.get("reason", "workspace inspection is incomplete"),
            "restore a git-backed workspace with at most 200 visible untracked files, then rerun synrail verify",
        )
    checked = []
    for name in sorted(required):
        binary = _resolved_binary_state(required[name], project_root=project_root)
        if binary["status"] != "OK":
            return _gate_block(
                "VERIFICATION_BINARY_CHANGED",
                f"profile '{name}' {binary['detail']}",
                "restore the executable locked at start or start a new run to adopt the new binary",
            )
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
        if receipt.get("environment_policy", "") != lock.get("environment_policy", ""):
            return _gate_block(
                "VERIFICATION_RECEIPT_INVALID",
                f"the receipt for profile '{name}' used a different verification environment policy",
                "run synrail verify to regenerate the receipt, then rerun synrail check",
            )
        if receipt.get("project_root_realpath", "") != lock.get("project_root_realpath", ""):
            return _gate_block(
                "VERIFICATION_RECEIPT_INVALID",
                f"the receipt for profile '{name}' belongs to a different project root",
                "run synrail verify from the original project root, then rerun synrail check",
            )
        if receipt.get("argv0_sha256", "") != required[name].get("argv0_sha256", ""):
            return _gate_block(
                "VERIFICATION_RECEIPT_INVALID",
                f"the receipt for profile '{name}' is not bound to the executable locked at start",
                "run synrail verify to regenerate the receipt, then rerun synrail check",
            )
        if receipt.get("argv0_execution_path", "") != required[name].get("argv0_execution_path", ""):
            return _gate_block(
                "VERIFICATION_RECEIPT_INVALID",
                f"the receipt for profile '{name}' used a different executable invocation path",
                "run synrail verify to regenerate the receipt, then rerun synrail check",
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
