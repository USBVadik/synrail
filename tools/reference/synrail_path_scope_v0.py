#!/usr/bin/env python3
"""Shared path-scope validation for Synrail entrypoints."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

ARTIFACT_SCOPE = "artifact_root"
PROJECT_SCOPE = "project_root"
DUAL_SCOPE = "project_or_artifact"


class PathScopeValidationError(ValueError):
    def __init__(
        self,
        *,
        field: str,
        value: str,
        resolved_path: Path,
        scope: str,
        detail: str,
        project_root: Path | None,
        artifact_root: Path | None,
    ) -> None:
        super().__init__(detail)
        self.field = field
        self.value = value
        self.resolved_path = resolved_path
        self.scope = scope
        self.detail = detail
        self.project_root = project_root.resolve() if project_root is not None else None
        self.artifact_root = artifact_root.resolve() if artifact_root is not None else None

    def as_payload(self) -> dict:
        payload = {
            "result": "ERROR",
            "reason": "PATH_SCOPE_VIOLATION",
            "path_arg": cli_flag_for_field(self.field),
            "path": self.value,
            "resolved_path": str(self.resolved_path),
            "scope": self.scope,
            "detail": self.detail,
        }
        if self.project_root is not None:
            payload["project_root"] = str(self.project_root)
        if self.artifact_root is not None:
            payload["artifact_root"] = str(self.artifact_root)
        return payload


def cli_flag_for_field(field: str) -> str:
    return f"--{field.replace('_', '-')}"


def path_in_root(candidate: Path, root: Path) -> bool:
    try:
        candidate.relative_to(root.resolve())
        return True
    except ValueError:
        return False


def _resolved_path(value: str) -> Path:
    return Path(value).expanduser().resolve()


def resolved_path_for_value(value: str) -> Path:
    return Path(value).expanduser().resolve()


def path_within_scope(path_value: str, *, scope: str, project_root: Path | None, artifact_root: Path | None) -> bool:
    resolved = resolved_path_for_value(path_value)
    if scope == PROJECT_SCOPE:
        return bool(project_root is not None and path_in_root(resolved, project_root))
    if scope == ARTIFACT_SCOPE:
        return bool(artifact_root is not None and path_in_root(resolved, artifact_root))
    if scope == DUAL_SCOPE:
        allowed_roots = [root for root in [project_root, artifact_root] if root is not None]
        return any(path_in_root(resolved, root) for root in allowed_roots)
    raise ValueError(f"unsupported path scope: {scope}")


def symlinked_ancestor_within(path: Path, *, stop_at: Path) -> Path | None:
    resolved_stop = stop_at.resolve()
    for candidate in [path, *path.parents]:
        try:
            candidate_resolved = candidate.resolve()
        except OSError:
            candidate_resolved = candidate
        if candidate.is_symlink():
            return candidate
        if candidate == stop_at or candidate_resolved == resolved_stop:
            return None
    return None


def path_surface_violation(
    path_value: str,
    *,
    field: str,
    scope: str,
    surface_label: str,
    expected_surface: str,
    stop_at: Path,
    project_root: Path | None,
    artifact_root: Path | None,
) -> PathScopeValidationError | None:
    candidate = Path(path_value).expanduser()
    if candidate.is_symlink():
        detail = f"{surface_label} is a symlink, expected {expected_surface}"
        resolved_path = candidate.resolve()
    elif candidate.parent.is_symlink():
        detail = f"{surface_label} parent is a symlink, expected {expected_surface}"
        resolved_path = candidate.parent.resolve()
    else:
        ancestor = symlinked_ancestor_within(candidate.parent, stop_at=stop_at)
        if ancestor is not None:
            detail = f"{surface_label} ancestor is a symlink, expected {expected_surface}"
            resolved_path = ancestor.resolve()
        else:
            return None
    return PathScopeValidationError(
        field=field,
        value=path_value,
        resolved_path=resolved_path,
        scope=scope,
        detail=detail,
        project_root=project_root,
        artifact_root=artifact_root,
    )


def reject_path_surface(
    path_value: str,
    *,
    field: str,
    scope: str,
    surface_label: str,
    expected_surface: str,
    stop_at: Path,
    project_root: Path | None,
    artifact_root: Path | None,
) -> int | None:
    violation = path_surface_violation(
        path_value,
        field=field,
        scope=scope,
        surface_label=surface_label,
        expected_surface=expected_surface,
        stop_at=stop_at,
        project_root=project_root,
        artifact_root=artifact_root,
    )
    if violation is None:
        return None
    print(json.dumps(violation.as_payload(), ensure_ascii=True))
    return 2


def validate_root_within_project(
    field: str,
    value: str,
    *,
    root: Path,
    project_root: Path | None,
    artifact_root: Path | None,
) -> None:
    resolved = root.resolve()
    if project_root is None:
        raise PathScopeValidationError(
            field=field,
            value=value,
            resolved_path=resolved,
            scope=PROJECT_SCOPE,
            detail="project root is unavailable for path-scope validation",
            project_root=project_root,
            artifact_root=artifact_root,
        )
    if path_in_root(resolved, project_root):
        return
    raise PathScopeValidationError(
        field=field,
        value=value,
        resolved_path=resolved,
        scope=PROJECT_SCOPE,
        detail="resolved path escapes project root",
        project_root=project_root,
        artifact_root=artifact_root,
    )


def validate_path_value(
    field: str,
    value: str,
    *,
    scope: str,
    project_root: Path | None,
    artifact_root: Path | None,
) -> None:
    text = value.strip()
    if not text:
        return
    resolved = _resolved_path(text)

    if scope == PROJECT_SCOPE:
        if project_root is None:
            raise PathScopeValidationError(
                field=field,
                value=text,
                resolved_path=resolved,
                scope=scope,
                detail="project root is unavailable for path-scope validation",
                project_root=project_root,
                artifact_root=artifact_root,
            )
        if path_in_root(resolved, project_root):
            return
        raise PathScopeValidationError(
            field=field,
            value=text,
            resolved_path=resolved,
            scope=scope,
            detail="resolved path escapes project root",
            project_root=project_root,
            artifact_root=artifact_root,
        )

    if scope == ARTIFACT_SCOPE:
        if artifact_root is None:
            raise PathScopeValidationError(
                field=field,
                value=text,
                resolved_path=resolved,
                scope=scope,
                detail="artifact root is unavailable for path-scope validation",
                project_root=project_root,
                artifact_root=artifact_root,
            )
        if path_in_root(resolved, artifact_root):
            return
        raise PathScopeValidationError(
            field=field,
            value=text,
            resolved_path=resolved,
            scope=scope,
            detail="resolved path escapes artifact root",
            project_root=project_root,
            artifact_root=artifact_root,
        )

    if scope == DUAL_SCOPE:
        allowed_roots = [root for root in [project_root, artifact_root] if root is not None]
        if not allowed_roots:
            raise PathScopeValidationError(
                field=field,
                value=text,
                resolved_path=resolved,
                scope=scope,
                detail="no scope root is available for path-scope validation",
                project_root=project_root,
                artifact_root=artifact_root,
            )
        if any(path_in_root(resolved, root) for root in allowed_roots):
            return
        raise PathScopeValidationError(
            field=field,
            value=text,
            resolved_path=resolved,
            scope=scope,
            detail="resolved path escapes project and artifact roots",
            project_root=project_root,
            artifact_root=artifact_root,
        )

    raise ValueError(f"unsupported path scope: {scope}")


def validate_namespace_paths(
    args: argparse.Namespace,
    *,
    field_scopes: dict[str, str],
    project_root: Path | None,
    artifact_root: Path | None,
) -> None:
    for field, scope in field_scopes.items():
        value = getattr(args, field, None)
        if value in {None, ""}:
            continue
        validate_path_value(
            field,
            str(value),
            scope=scope,
            project_root=project_root,
            artifact_root=artifact_root,
        )
