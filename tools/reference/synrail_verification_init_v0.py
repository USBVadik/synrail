#!/usr/bin/env python3
"""Fail-safe scaffold writer for operator-owned verification profiles."""

from __future__ import annotations

import datetime as dt
import json
import os
import re
import stat
import tempfile
from dataclasses import dataclass
from pathlib import Path

try:
    from .synrail_verification_profile_v0 import (
        CONFIG_FILE_NAME,
        DEFAULT_TIMEOUT_SECONDS,
        MAX_ARG_CHARS,
        MAX_ARGV_ITEMS,
        MAX_CONFIG_BYTES,
        MAX_PROFILE_NAME_CHARS,
        MAX_TIMEOUT_SECONDS,
    )
except ImportError:
    from synrail_verification_profile_v0 import (
        CONFIG_FILE_NAME,
        DEFAULT_TIMEOUT_SECONDS,
        MAX_ARG_CHARS,
        MAX_ARGV_ITEMS,
        MAX_CONFIG_BYTES,
        MAX_PROFILE_NAME_CHARS,
        MAX_TIMEOUT_SECONDS,
    )


SAFE_PROFILE_NAME = re.compile(r"[A-Za-z0-9_-]+\Z")


class VerificationInitError(Exception):
    """Named, actionable refusal from the verification scaffold writer."""

    def __init__(self, reason: str, detail: str, next_step: str) -> None:
        super().__init__(detail)
        self.reason = reason
        self.detail = detail
        self.next_step = next_step


@dataclass(frozen=True)
class VerificationScaffoldResult:
    path: Path
    state: str
    profile_name: str
    argv: tuple[str, ...]
    timeout_seconds: int
    backup_path: Path | None = None


def _validate_profile_name(name: object) -> str:
    if not isinstance(name, str) or not name:
        raise VerificationInitError(
            "VERIFICATION_PROFILE_NAME_INVALID",
            "profile name must be a non-empty string.",
            "Pass a simple name such as --name unit.",
        )
    if len(name) > MAX_PROFILE_NAME_CHARS:
        raise VerificationInitError(
            "VERIFICATION_PROFILE_NAME_INVALID",
            f"profile name exceeds the {MAX_PROFILE_NAME_CHARS}-character limit.",
            "Choose a shorter profile name.",
        )
    if not SAFE_PROFILE_NAME.fullmatch(name):
        raise VerificationInitError(
            "VERIFICATION_PROFILE_NAME_INVALID",
            "profile name may contain only ASCII letters, digits, underscores, and hyphens.",
            "Choose a simple name such as unit, lint, or integration-tests.",
        )
    return name


def _validate_argv(argv: object) -> tuple[str, ...]:
    if not isinstance(argv, (list, tuple)) or not argv:
        raise VerificationInitError(
            "VERIFICATION_ARGV_REQUIRED",
            "no verification command was provided.",
            "Pass the exact argv after --, for example: -- python -m pytest -q.",
        )
    if len(argv) > MAX_ARGV_ITEMS:
        raise VerificationInitError(
            "VERIFICATION_ARGV_INVALID",
            f"verification argv exceeds the {MAX_ARGV_ITEMS}-item limit.",
            "Use a shorter direct command or a reviewed repository script.",
        )
    normalized: list[str] = []
    for item in argv:
        if not isinstance(item, str) or not item.strip():
            raise VerificationInitError(
                "VERIFICATION_ARGV_INVALID",
                "every verification argv item must be a non-empty string.",
                "Remove empty arguments and rerun init-verification.",
            )
        if len(item) > MAX_ARG_CHARS:
            raise VerificationInitError(
                "VERIFICATION_ARGV_INVALID",
                f"a verification argument exceeds the {MAX_ARG_CHARS}-character limit.",
                "Use a shorter argument or a reviewed repository script.",
            )
        if any(character in item for character in ("\0", "\n", "\r")):
            raise VerificationInitError(
                "VERIFICATION_ARGV_INVALID",
                "verification arguments may not contain NUL bytes or line breaks.",
                "Pass each command argument as one plain argv item.",
            )
        normalized.append(item)
    return tuple(normalized)


def _validate_timeout(timeout_seconds: object) -> int:
    if isinstance(timeout_seconds, bool) or not isinstance(timeout_seconds, int):
        raise VerificationInitError(
            "VERIFICATION_TIMEOUT_INVALID",
            "timeout_seconds must be an integer.",
            f"Choose an integer from 1 through {MAX_TIMEOUT_SECONDS}.",
        )
    if timeout_seconds < 1 or timeout_seconds > MAX_TIMEOUT_SECONDS:
        raise VerificationInitError(
            "VERIFICATION_TIMEOUT_INVALID",
            f"timeout_seconds must be between 1 and {MAX_TIMEOUT_SECONDS}.",
            f"Choose an integer from 1 through {MAX_TIMEOUT_SECONDS}.",
        )
    return timeout_seconds


def render_verification_scaffold(
    *,
    profile_name: object,
    argv: object,
    timeout_seconds: object = DEFAULT_TIMEOUT_SECONDS,
) -> str:
    """Render a single required profile without executing or trusting it."""
    name = _validate_profile_name(profile_name)
    command = _validate_argv(argv)
    timeout = _validate_timeout(timeout_seconds)
    encoded_argv = ", ".join(json.dumps(item, ensure_ascii=False) for item in command)
    rendered = (
        "# REVIEW REQUIRED: confirm this exact argv and timeout before committing.\n"
        "# Synrail trusts it only after synrail.toml is a regular, tracked file matching HEAD.\n"
        "# This scaffold command did not execute the argv below.\n"
        "# Do not put secrets in argv; this file is intended to be reviewed and committed.\n"
        "\n"
        f"[verification.{name}]\n"
        f"argv = [{encoded_argv}]\n"
        f"timeout_seconds = {timeout}\n"
        "required = true\n"
    )
    if len(rendered.encode("utf-8")) > MAX_CONFIG_BYTES:
        raise VerificationInitError(
            "VERIFICATION_CONFIG_TOO_LARGE",
            f"generated synrail.toml exceeds the {MAX_CONFIG_BYTES}-byte config limit.",
            "Use a shorter direct argv or an operator-reviewed repository script.",
        )
    return rendered


def _read_regular_file(path: Path) -> tuple[bytes, int]:
    try:
        before = path.lstat()
    except FileNotFoundError:
        raise
    except OSError as exc:
        raise VerificationInitError(
            "VERIFICATION_CONFIG_UNREADABLE",
            f"could not inspect {path}: {exc}",
            "Fix the path permissions and rerun init-verification.",
        ) from exc
    if stat.S_ISLNK(before.st_mode) or not stat.S_ISREG(before.st_mode):
        raise VerificationInitError(
            "VERIFICATION_CONFIG_UNTRUSTED",
            "synrail.toml must be a regular file, not a symlink or special file.",
            "Remove or relocate the unsafe path before rerunning init-verification.",
        )

    flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        descriptor = os.open(path, flags)
    except OSError as exc:
        raise VerificationInitError(
            "VERIFICATION_CONFIG_UNREADABLE",
            f"could not open {path} safely: {exc}",
            "Fix the file type or permissions and rerun init-verification.",
        ) from exc
    try:
        opened = os.fstat(descriptor)
        if not stat.S_ISREG(opened.st_mode):
            raise VerificationInitError(
                "VERIFICATION_CONFIG_UNTRUSTED",
                "synrail.toml changed into a symlink or special file while it was inspected.",
                "Remove or relocate the unsafe path before rerunning init-verification.",
            )
        with os.fdopen(descriptor, "rb") as handle:
            descriptor = -1
            payload = handle.read()
    finally:
        if descriptor >= 0:
            os.close(descriptor)

    try:
        after = path.lstat()
    except OSError as exc:
        raise VerificationInitError(
            "VERIFICATION_CONFIG_CHANGED",
            f"synrail.toml changed while it was inspected: {exc}",
            "Inspect the concurrent change and rerun init-verification.",
        ) from exc
    if (
        not stat.S_ISREG(after.st_mode)
        or (before.st_dev, before.st_ino, before.st_mode, before.st_size, before.st_mtime_ns)
        != (after.st_dev, after.st_ino, after.st_mode, after.st_size, after.st_mtime_ns)
    ):
        raise VerificationInitError(
            "VERIFICATION_CONFIG_CHANGED",
            "synrail.toml changed while it was inspected.",
            "Inspect the concurrent change and rerun init-verification.",
        )
    return payload, stat.S_IMODE(opened.st_mode)


def _sync_parent_directory(path: Path) -> None:
    if os.name != "posix" or not hasattr(os, "O_DIRECTORY"):
        return
    try:
        descriptor = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
    except OSError:
        return
    try:
        os.fsync(descriptor)
    except OSError:
        pass
    finally:
        os.close(descriptor)


def _atomic_write_bytes(path: Path, payload: bytes, *, mode: int = 0o644) -> None:
    descriptor = -1
    temp_name = ""
    try:
        descriptor, temp_name = tempfile.mkstemp(prefix=f".{path.name}.tmp-", dir=path.parent)
        with os.fdopen(descriptor, "wb") as handle:
            descriptor = -1
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        try:
            os.chmod(temp_name, mode)
        except OSError:
            pass
        os.replace(temp_name, path)
        temp_name = ""
        _sync_parent_directory(path)
    except OSError as exc:
        raise VerificationInitError(
            "VERIFICATION_CONFIG_WRITE_FAILED",
            f"could not write {path}: {exc}",
            "Fix the project-root permissions and rerun init-verification.",
        ) from exc
    finally:
        if descriptor >= 0:
            os.close(descriptor)
        if temp_name:
            try:
                Path(temp_name).unlink()
            except FileNotFoundError:
                pass


def _unused_backup_path(path: Path) -> Path:
    timestamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    candidate = path.with_name(f"{path.name}.synrail.bak.{timestamp}")
    counter = 1
    while candidate.exists() or candidate.is_symlink():
        candidate = path.with_name(f"{path.name}.synrail.bak.{timestamp}.{counter}")
        counter += 1
    return candidate


def write_verification_scaffold(
    *,
    project_root: Path,
    profile_name: object,
    argv: object,
    timeout_seconds: object = DEFAULT_TIMEOUT_SECONDS,
    force: bool = False,
) -> VerificationScaffoldResult:
    """Write one review-required profile, preserving existing config by default."""
    root = project_root.expanduser().resolve()
    if not root.exists() or not root.is_dir():
        raise VerificationInitError(
            "PROJECT_ROOT_INVALID",
            f"project root is not an existing directory: {root}",
            "Pass --project-root for the repository that should own synrail.toml.",
        )

    name = _validate_profile_name(profile_name)
    command = _validate_argv(argv)
    timeout = _validate_timeout(timeout_seconds)
    rendered = render_verification_scaffold(
        profile_name=name,
        argv=command,
        timeout_seconds=timeout,
    )
    payload = rendered.encode("utf-8")
    path = root / CONFIG_FILE_NAME
    backup_path: Path | None = None

    try:
        existing_record = _read_regular_file(path)
    except FileNotFoundError:
        existing_record = None

    existing = existing_record[0] if existing_record else None
    existing_mode = existing_record[1] if existing_record else 0o644

    if existing == payload:
        return VerificationScaffoldResult(path, "unchanged", name, command, timeout)
    if existing is not None and not force:
        raise VerificationInitError(
            "VERIFICATION_CONFIG_EXISTS",
            f"{path} already exists with different content; Synrail left it unchanged.",
            "Review the existing profiles, or rerun with --force to create an exact backup before replacement.",
        )
    if existing is not None:
        backup_path = _unused_backup_path(path)
        _atomic_write_bytes(backup_path, existing, mode=existing_mode)
        current_record = _read_regular_file(path)
        if current_record != existing_record:
            raise VerificationInitError(
                "VERIFICATION_CONFIG_CHANGED",
                "synrail.toml changed while its force-replacement backup was being created.",
                "Inspect the concurrent change and rerun init-verification only after other writers stop.",
            )
        state = "updated"
    else:
        state = "written"

    _atomic_write_bytes(path, payload, mode=existing_mode)
    return VerificationScaffoldResult(path, state, name, command, timeout, backup_path)
