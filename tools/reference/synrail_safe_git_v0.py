#!/usr/bin/env python3
"""Hardened Git subprocess construction for local untrusted worktrees."""

from __future__ import annotations

import os
import re
import shutil
import subprocess
from pathlib import Path


FILTER_KEY = re.compile(r"^filter\.([A-Za-z0-9_.-]+)\.(clean|smudge|process|required)$")
FILTER_KEY_PREFIX = re.compile(r"^filter\.(.+)\.(clean|smudge|process|required)$")
DEFAULT_TIMEOUT_SECONDS = 10


class SafeGitError(RuntimeError):
    def __init__(self, reason: str, detail: str) -> None:
        super().__init__(detail)
        self.reason = reason
        self.detail = detail


def trusted_external_executable(executable: str, project_root: Path) -> str:
    candidate = shutil.which(executable)
    if not candidate:
        raise SafeGitError(
            "COMMAND_REQUIRED",
            f"{executable} is not installed or not available on PATH",
        )
    resolved = Path(candidate).expanduser().resolve()
    root = project_root.expanduser().resolve()
    try:
        resolved.relative_to(root)
    except ValueError:
        return str(resolved)
    raise SafeGitError(
        "UNTRUSTED_COMMAND_EXECUTABLE",
        f"refusing to execute {executable} from inside the target repository: {resolved}",
    )


def trusted_git_executable(project_root: Path) -> str:
    try:
        return trusted_external_executable("git", project_root)
    except SafeGitError as exc:
        reason = "GIT_REQUIRED" if exc.reason == "COMMAND_REQUIRED" else exc.reason
        raise SafeGitError(reason, exc.detail) from exc


def safe_git_env() -> dict[str, str]:
    env = os.environ.copy()
    for key in list(env):
        # Git exposes many environment-controlled trust surfaces, including
        # alternate repositories, indexes, object stores, helpers, and config.
        # Start from no inherited GIT_* state and add back only bounded values.
        if key.startswith("GIT_"):
            env.pop(key, None)
    env.update(
        {
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_CONFIG_GLOBAL": os.devnull,
            "GIT_PAGER": "cat",
            "GIT_OPTIONAL_LOCKS": "0",
            "GIT_TERMINAL_PROMPT": "0",
        }
    )
    return env


def _base_config_args() -> list[str]:
    return [
        "-c",
        "core.fsmonitor=false",
        "-c",
        f"core.hooksPath={os.devnull}",
        "-c",
        "core.pager=cat",
    ]


def _raw_git(
    project_root: Path,
    args: list[str],
    *,
    timeout: int = DEFAULT_TIMEOUT_SECONDS,
) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            [
                trusted_git_executable(project_root),
                "--literal-pathspecs",
                *_base_config_args(),
                "-C",
                str(project_root.resolve()),
                *args,
            ],
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout,
            env=safe_git_env(),
        )
    except FileNotFoundError as exc:
        raise SafeGitError("GIT_REQUIRED", "git is not installed or not available on PATH") from exc
    except subprocess.TimeoutExpired as exc:
        raise SafeGitError("GIT_TIMEOUT", "git did not finish within the bounded timeout") from exc


def configured_filter_drivers(project_root: Path) -> list[str]:
    completed = _raw_git(
        project_root,
        [
            "config",
            "--includes",
            "--name-only",
            "--get-regexp",
            r"^filter\..*\.(clean|smudge|process|required)$",
        ],
    )
    if completed.returncode == 1:
        return []
    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout or "git config inspection failed").strip()
        raise SafeGitError("GIT_CONFIG_INSPECTION_FAILED", detail)

    drivers: set[str] = set()
    for raw_key in completed.stdout.splitlines():
        key = raw_key.strip()
        if not key:
            continue
        match = FILTER_KEY.fullmatch(key)
        if match is None:
            unsafe_match = FILTER_KEY_PREFIX.fullmatch(key)
            detail = (
                f"unsupported filter driver name in local git config: {unsafe_match.group(1)!r}"
                if unsafe_match
                else f"unexpected local git filter key: {key!r}"
            )
            raise SafeGitError("UNSAFE_GIT_FILTER_CONFIG", detail)
        drivers.add(match.group(1))
    return sorted(drivers)


def _filter_override_args(
    project_root: Path,
    *,
    reject_configured_filters: bool = False,
) -> list[str]:
    overrides: list[str] = []
    drivers = configured_filter_drivers(project_root)
    if drivers and reject_configured_filters:
        raise SafeGitError(
            "GIT_FILTERED_MUTATION_UNSUPPORTED",
            "Synrail will not run a workspace-mutating git command while local filter drivers are configured: "
            + ", ".join(drivers),
        )
    for driver in drivers:
        overrides.extend(
            [
                "-c",
                f"filter.{driver}.clean=",
                "-c",
                f"filter.{driver}.smudge=",
                "-c",
                f"filter.{driver}.process=",
                "-c",
                f"filter.{driver}.required=false",
            ]
        )
    return overrides


def safe_git_argv(
    project_root: Path,
    args: list[str],
    *,
    disable_filters: bool = True,
    reject_configured_filters: bool = False,
) -> list[str]:
    if not args:
        raise SafeGitError("GIT_COMMAND_REQUIRED", "a git subcommand is required")
    subcommand, *tail = args
    if subcommand in {"diff", "show", "log"}:
        tail = ["--no-ext-diff", "--no-textconv", *tail]
    overrides = (
        _filter_override_args(
            project_root,
            reject_configured_filters=reject_configured_filters,
        )
        if disable_filters
        else []
    )
    return [
        trusted_git_executable(project_root),
        "--literal-pathspecs",
        *_base_config_args(),
        *overrides,
        "-C",
        str(project_root.resolve()),
        subcommand,
        *tail,
    ]


def run_safe_git(
    project_root: Path,
    args: list[str],
    *,
    timeout: int = DEFAULT_TIMEOUT_SECONDS,
    disable_filters: bool = True,
    reject_configured_filters: bool = False,
) -> subprocess.CompletedProcess[str]:
    argv = safe_git_argv(
        project_root,
        args,
        disable_filters=disable_filters,
        reject_configured_filters=reject_configured_filters,
    )
    try:
        return subprocess.run(
            argv,
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout,
            env=safe_git_env(),
        )
    except FileNotFoundError as exc:
        raise SafeGitError("GIT_REQUIRED", "git is not installed or not available on PATH") from exc
    except subprocess.TimeoutExpired as exc:
        raise SafeGitError("GIT_TIMEOUT", "git did not finish within the bounded timeout") from exc
