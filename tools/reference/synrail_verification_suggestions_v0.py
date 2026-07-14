#!/usr/bin/env python3
"""Read-only suggestions for operator-owned verification profiles.

Discovery is deliberately weaker than configuration. It inspects a bounded
set of conventional project-root markers and proposes exact argv for operator
review. It never executes a candidate or writes ``synrail.toml``.
"""

from __future__ import annotations

import json
import os
import re
import stat
import tomllib
from dataclasses import dataclass
from pathlib import Path

try:
    from .synrail_verification_profile_v0 import SYNRAIL_PYTHON_ARGV0
except ImportError:
    from synrail_verification_profile_v0 import SYNRAIL_PYTHON_ARGV0


SUGGESTIONS_SCHEMA_VERSION = "verification_suggestions_v0"
MAX_MARKER_BYTES = 256 * 1024
MAX_DEPENDENCY_NODES = 4096
PYTEST_DEPENDENCY = re.compile(r"^\s*pytest(?:$|[\s<>=!~;\[.\-])", re.IGNORECASE | re.MULTILINE)
PYTEST_CONFIG_SECTION = re.compile(r"^\s*\[(?:tool:)?pytest\]\s*$", re.IGNORECASE | re.MULTILINE)
TOX_TESTENV_SECTION = re.compile(r"^\s*\[testenv(?::[^\]]+)?\]\s*$", re.IGNORECASE | re.MULTILINE)
PLACEHOLDER_NODE_TEST = re.compile(r"no test specified", re.IGNORECASE)


class VerificationSuggestionError(Exception):
    """A named refusal before suggestion discovery can start."""

    def __init__(self, reason: str, detail: str, next_step: str) -> None:
        super().__init__(detail)
        self.reason = reason
        self.detail = detail
        self.next_step = next_step


@dataclass(frozen=True)
class VerificationSuggestion:
    candidate_id: str
    profile_name: str
    argv: tuple[str, ...]
    detected_from: tuple[str, ...]
    rationale: str
    priority: int

    def as_record(self, *, command: str) -> dict[str, object]:
        scaffold_argv = [
            command,
            "init-verification",
            "--name",
            self.profile_name,
            "--",
            *self.argv,
        ]
        return {
            "candidate_id": self.candidate_id,
            "profile_name": self.profile_name,
            "argv": list(self.argv),
            "detected_from": list(self.detected_from),
            "rationale": self.rationale,
            "trust_state": "REVIEW_REQUIRED",
            "source_trust": "NOT_ATTESTED",
            "scaffold_argv": scaffold_argv,
        }


def _warning(path: str, reason: str, detail: str) -> dict[str, str]:
    return {"path": path, "reason": reason, "detail": detail}


def _read_marker(
    project_root: Path,
    relative_path: str,
    warnings: list[dict[str, str]],
) -> bytes | None:
    """Read one known root marker without following a final symlink."""
    relative = Path(relative_path)
    if relative.is_absolute() or ".." in relative.parts:
        raise ValueError(f"unsafe internal marker path: {relative_path}")
    path = project_root / relative
    try:
        before = path.lstat()
    except FileNotFoundError:
        return None
    except OSError as exc:
        warnings.append(_warning(relative_path, "MARKER_UNREADABLE", str(exc)))
        return None
    if stat.S_ISLNK(before.st_mode) or not stat.S_ISREG(before.st_mode):
        warnings.append(
            _warning(
                relative_path,
                "MARKER_UNTRUSTED",
                "discovery ignores symlinks and non-regular marker files",
            )
        )
        return None
    if before.st_size > MAX_MARKER_BYTES:
        warnings.append(
            _warning(
                relative_path,
                "MARKER_TOO_LARGE",
                f"marker exceeds the {MAX_MARKER_BYTES}-byte discovery limit",
            )
        )
        return None

    flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = -1
    try:
        descriptor = os.open(path, flags)
        opened = os.fstat(descriptor)
        if not stat.S_ISREG(opened.st_mode):
            warnings.append(
                _warning(relative_path, "MARKER_UNTRUSTED", "marker changed into a non-regular file")
            )
            return None
        if (before.st_dev, before.st_ino, before.st_mode) != (
            opened.st_dev,
            opened.st_ino,
            opened.st_mode,
        ):
            warnings.append(
                _warning(relative_path, "MARKER_CHANGED", "marker changed before discovery opened it")
            )
            return None
        with os.fdopen(descriptor, "rb") as handle:
            descriptor = -1
            payload = handle.read(MAX_MARKER_BYTES + 1)
    except OSError as exc:
        warnings.append(_warning(relative_path, "MARKER_UNREADABLE", str(exc)))
        return None
    finally:
        if descriptor >= 0:
            os.close(descriptor)
    if len(payload) > MAX_MARKER_BYTES:
        warnings.append(
            _warning(
                relative_path,
                "MARKER_TOO_LARGE",
                f"marker exceeds the {MAX_MARKER_BYTES}-byte discovery limit",
            )
        )
        return None
    try:
        after = path.lstat()
    except OSError as exc:
        warnings.append(_warning(relative_path, "MARKER_CHANGED", str(exc)))
        return None
    identity_before = (before.st_dev, before.st_ino, before.st_mode, before.st_size, before.st_mtime_ns)
    identity_after = (after.st_dev, after.st_ino, after.st_mode, after.st_size, after.st_mtime_ns)
    if identity_before != identity_after:
        warnings.append(_warning(relative_path, "MARKER_CHANGED", "marker changed while discovery read it"))
        return None
    return payload


def _regular_marker_exists(
    project_root: Path,
    relative_path: str,
    warnings: list[dict[str, str]],
) -> bool:
    """Recognize one known marker by type without reading its contents."""
    relative = Path(relative_path)
    if relative.is_absolute() or ".." in relative.parts:
        raise ValueError(f"unsafe internal marker path: {relative_path}")
    try:
        marker = (project_root / relative).lstat()
    except FileNotFoundError:
        return False
    except OSError as exc:
        warnings.append(_warning(relative_path, "MARKER_UNREADABLE", str(exc)))
        return False
    if stat.S_ISLNK(marker.st_mode) or not stat.S_ISREG(marker.st_mode):
        warnings.append(
            _warning(
                relative_path,
                "MARKER_UNTRUSTED",
                "discovery ignores symlinks and non-regular marker files",
            )
        )
        return False
    return True


def _decode_text(payload: bytes, path: str, warnings: list[dict[str, str]]) -> str | None:
    try:
        return payload.decode("utf-8")
    except UnicodeDecodeError:
        warnings.append(_warning(path, "MARKER_ENCODING_INVALID", "marker is not valid UTF-8"))
        return None


def _nested_values(value: object):
    stack = [value]
    visited = 0
    while stack and visited < MAX_DEPENDENCY_NODES:
        current = stack.pop()
        visited += 1
        if isinstance(current, dict):
            stack.extend(current.values())
        elif isinstance(current, list):
            stack.extend(current)
        elif isinstance(current, str):
            yield current


def _pyproject_declares_pytest(pyproject: dict[str, object]) -> bool:
    tool = pyproject.get("tool", {})
    if isinstance(tool, dict) and "pytest" in tool:
        return True

    dependency_surfaces: list[object] = []
    poetry_dependency_names: list[str] = []
    project = pyproject.get("project", {})
    if isinstance(project, dict):
        dependency_surfaces.extend(
            [
                project.get("dependencies", []),
                project.get("optional-dependencies", {}),
            ]
        )
    dependency_surfaces.append(pyproject.get("dependency-groups", {}))
    if isinstance(tool, dict):
        poetry = tool.get("poetry", {})
        if isinstance(poetry, dict):
            for section_name in ("dependencies", "dev-dependencies"):
                section = poetry.get(section_name, {})
                if isinstance(section, dict):
                    poetry_dependency_names.extend(str(name) for name in section)
            groups = poetry.get("group", {})
            if isinstance(groups, dict):
                for group in groups.values():
                    if not isinstance(group, dict):
                        continue
                    dependencies = group.get("dependencies", {})
                    if isinstance(dependencies, dict):
                        poetry_dependency_names.extend(str(name) for name in dependencies)
    return any(PYTEST_DEPENDENCY.search(name) for name in poetry_dependency_names) or any(
        PYTEST_DEPENDENCY.search(item)
        for surface in dependency_surfaces
        for item in _nested_values(surface)
    )


def _python_suggestion(
    project_root: Path,
    warnings: list[dict[str, str]],
) -> VerificationSuggestion | None:
    marker_payloads: dict[str, bytes] = {}
    for marker in (
        "pyproject.toml",
        "pytest.ini",
        "setup.cfg",
        "tox.ini",
        "requirements.txt",
        "requirements-dev.txt",
        "dev-requirements.txt",
    ):
        payload = _read_marker(project_root, marker, warnings)
        if payload is not None:
            marker_payloads[marker] = payload

    pytest_sources: list[str] = []
    if "pytest.ini" in marker_payloads:
        pytest_sources.append("pytest.ini")

    pyproject_payload = marker_payloads.get("pyproject.toml")
    if pyproject_payload is not None:
        try:
            pyproject = tomllib.loads(pyproject_payload.decode("utf-8"))
        except (UnicodeDecodeError, tomllib.TOMLDecodeError, RecursionError) as exc:
            warnings.append(_warning("pyproject.toml", "MARKER_PARSE_FAILED", str(exc)))
        else:
            if isinstance(pyproject, dict) and _pyproject_declares_pytest(pyproject):
                pytest_sources.append("pyproject.toml")

    for marker in ("setup.cfg", "requirements.txt", "requirements-dev.txt", "dev-requirements.txt"):
        payload = marker_payloads.get(marker)
        if payload is None:
            continue
        text = _decode_text(payload, marker, warnings)
        if text is None:
            continue
        if PYTEST_CONFIG_SECTION.search(text) or PYTEST_DEPENDENCY.search(text):
            pytest_sources.append(marker)

    if pytest_sources:
        return VerificationSuggestion(
            candidate_id="python-pytest",
            profile_name="python-tests",
            argv=(SYNRAIL_PYTHON_ARGV0, "-m", "pytest", "-q"),
            detected_from=tuple(sorted(set(pytest_sources))),
            rationale=(
                "Python project declares pytest configuration or a pytest dependency; "
                "review that Synrail's interpreter contains the target dependencies."
            ),
            priority=10,
        )

    tox_payload = marker_payloads.get("tox.ini")
    if tox_payload is not None:
        text = _decode_text(tox_payload, "tox.ini", warnings)
        if text is not None and TOX_TESTENV_SECTION.search(text):
            return VerificationSuggestion(
                candidate_id="python-tox",
                profile_name="python-tests",
                argv=(SYNRAIL_PYTHON_ARGV0, "-m", "tox"),
                detected_from=("tox.ini",),
                rationale=(
                    "Python project declares at least one tox test environment; review that "
                    "Synrail's interpreter contains tox and the target dependencies."
                ),
                priority=11,
            )
    return None


def _node_suggestion(
    project_root: Path,
    warnings: list[dict[str, str]],
) -> VerificationSuggestion | None:
    payload = _read_marker(project_root, "package.json", warnings)
    if payload is None:
        return None
    try:
        package = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError, RecursionError) as exc:
        warnings.append(_warning("package.json", "MARKER_PARSE_FAILED", str(exc)))
        return None
    scripts = package.get("scripts", {}) if isinstance(package, dict) else {}
    test_script = scripts.get("test") if isinstance(scripts, dict) else None
    if not isinstance(test_script, str) or not test_script.strip() or PLACEHOLDER_NODE_TEST.search(test_script):
        return None

    package_manager = "npm"
    argv = ("npm", "test")
    detected_from = ["package.json"]
    declared_manager = package.get("packageManager") if isinstance(package, dict) else None
    declared_name = declared_manager.split("@", 1)[0] if isinstance(declared_manager, str) else ""
    manager_commands = {
        "npm": ("npm", "test"),
        "pnpm": ("pnpm", "test"),
        "yarn": ("yarn", "test"),
        "bun": ("bun", "run", "test"),
    }
    if declared_name in manager_commands:
        package_manager = declared_name
        argv = manager_commands[declared_name]
    else:
        for marker, manager, command in (
            ("pnpm-lock.yaml", "pnpm", ("pnpm", "test")),
            ("yarn.lock", "yarn", ("yarn", "test")),
            ("bun.lock", "bun", ("bun", "run", "test")),
            ("bun.lockb", "bun", ("bun", "run", "test")),
            ("package-lock.json", "npm", ("npm", "test")),
            ("npm-shrinkwrap.json", "npm", ("npm", "test")),
        ):
            if _regular_marker_exists(project_root, marker, warnings):
                package_manager = manager
                argv = command
                detected_from.append(marker)
                break
    return VerificationSuggestion(
        candidate_id=f"node-{package_manager}-test",
        profile_name="node-tests",
        argv=argv,
        detected_from=tuple(detected_from),
        rationale=f"package.json declares a non-placeholder test script; {package_manager} was selected from root markers.",
        priority=20,
    )


def _marker_suggestion(
    project_root: Path,
    warnings: list[dict[str, str]],
    *,
    marker: str,
    candidate_id: str,
    profile_name: str,
    argv: tuple[str, ...],
    rationale: str,
    priority: int,
) -> VerificationSuggestion | None:
    if not _regular_marker_exists(project_root, marker, warnings):
        return None
    return VerificationSuggestion(
        candidate_id=candidate_id,
        profile_name=profile_name,
        argv=argv,
        detected_from=(marker,),
        rationale=rationale,
        priority=priority,
    )


def discover_verification_suggestions(
    project_root: Path,
    *,
    command: str = "synrail",
) -> dict[str, object]:
    """Return bounded profile candidates without executing or writing them."""
    root = Path(project_root).expanduser()
    try:
        root = root.resolve(strict=True)
    except OSError as exc:
        raise VerificationSuggestionError(
            "PROJECT_ROOT_INVALID",
            f"project root does not resolve to an existing directory: {exc}",
            "Pass the repository root with --project-root and rerun suggest-verification.",
        ) from exc
    if not root.is_dir():
        raise VerificationSuggestionError(
            "PROJECT_ROOT_INVALID",
            f"project root is not a directory: {root}",
            "Pass the repository root with --project-root and rerun suggest-verification.",
        )

    warnings: list[dict[str, str]] = []
    suggestions = [
        item
        for item in (
            _python_suggestion(root, warnings),
            _node_suggestion(root, warnings),
            _marker_suggestion(
                root,
                warnings,
                marker="go.mod",
                candidate_id="go-test",
                profile_name="go-tests",
                argv=("go", "test", "./..."),
                rationale="A root go.mod declares a Go module.",
                priority=30,
            ),
            _marker_suggestion(
                root,
                warnings,
                marker="Cargo.toml",
                candidate_id="rust-cargo-test",
                profile_name="rust-tests",
                argv=("cargo", "test"),
                rationale="A root Cargo.toml declares a Rust package or workspace.",
                priority=40,
            ),
        )
        if item is not None
    ]
    suggestions.sort(key=lambda item: (item.priority, item.candidate_id))
    records = [item.as_record(command=command) for item in suggestions]
    found = bool(records)
    return {
        "schema_version": SUGGESTIONS_SCHEMA_VERSION,
        "status": "SUGGESTIONS_FOUND" if found else "NO_SUGGESTIONS",
        "project_root": str(root),
        "discovery_only": True,
        "source_provenance_verified": False,
        "verification_commands_executed": False,
        "files_written": False,
        "candidate_count": len(records),
        "candidates": records,
        "warnings": warnings,
        "next_step": (
            "Choose one candidate, inspect its exact argv, then run its Scaffold command and review synrail.toml."
            if found
            else "Choose the project's real test command and pass its exact argv to synrail init-verification."
        ),
    }
