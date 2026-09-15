#!/usr/bin/env python3
"""Read-only protected-admission observations for exact Git commit pairs."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

try:
    from .synrail_safe_git_v0 import SafeGitError, run_safe_git
    from .synrail_version_v0 import __version__
except ImportError:
    from synrail_safe_git_v0 import SafeGitError, run_safe_git
    from synrail_version_v0 import __version__


SCHEMA_VERSION = "protected_admission_shadow_v0"
POLICY_REVISION = "authority_paths_v0"
DIFF_SEMANTICS = "MERGE_BASE_TO_HEAD_NO_RENAMES"
CLASSIFIER_SCOPE = "PATH_RULES_ONLY"
MAX_CHANGED_ENTRIES = 10_000
MAX_GIT_OUTPUT_BYTES = 4 * 1024 * 1024
MAX_DETAIL_LENGTH = 500
FULL_COMMIT_SHA = re.compile(r"^(?:[0-9a-f]{40}|[0-9a-f]{64})$")
SURROGATE_ESCAPE = re.compile(r"[\udc80-\udcff]")

CATEGORY_REASON_CODES = {
    "TESTS": "AUTHORITY_CHANGE_TESTS",
    "CI_WORKFLOW": "AUTHORITY_CHANGE_CI_WORKFLOW",
    "POLICY": "AUTHORITY_CHANGE_POLICY",
    "PERMISSIONS_IAM": "AUTHORITY_CHANGE_PERMISSIONS_IAM",
    "DEPLOYMENT_GUARDRAIL": "AUTHORITY_CHANGE_DEPLOYMENT_GUARDRAIL",
}
CATEGORY_ORDER = tuple(CATEGORY_REASON_CODES)

TEST_PATH_SEGMENTS = {"test", "tests", "__tests__"}
TEST_CONFIG_FILES = {
    "conftest.py",
    "pytest.ini",
    "tox.ini",
    "noxfile.py",
    "jest.config.js",
    "jest.config.cjs",
    "jest.config.mjs",
    "jest.config.ts",
    "vitest.config.js",
    "vitest.config.mjs",
    "vitest.config.ts",
    "playwright.config.js",
    "playwright.config.ts",
    "karma.conf.js",
    "karma.conf.cjs",
}
CI_ROOT_FILES = {
    ".gitlab-ci.yml",
    ".gitlab-ci.yaml",
    "azure-pipelines.yml",
    "azure-pipelines.yaml",
    "bitbucket-pipelines.yml",
    "bitbucket-pipelines.yaml",
    "jenkinsfile",
    ".drone.yml",
    ".drone.yaml",
}
CI_PATH_PREFIXES = {
    (".github", "workflows"),
    (".github", "actions"),
    (".circleci",),
    (".buildkite",),
    (".woodpecker",),
}
POLICY_PATH_SEGMENTS = {"policy", "policies"}
POLICY_FILES = {
    "synrail.toml",
    "codeowners",
    ".github/codeowners",
    "docs/codeowners",
}
PERMISSION_PATH_SEGMENTS = {
    "iam",
    "rbac",
    "permissions",
    "access-control",
    "access_control",
    "authz",
}
DEPLOYMENT_PATH_SEGMENTS = {
    "deploy",
    "deployment",
    "deployments",
    "infra",
    "infrastructure",
    "terraform",
    "k8s",
    "kubernetes",
    "helm",
    "argocd",
}
DEPLOYMENT_FILES = {
    "docker-compose.yml",
    "docker-compose.yaml",
    "vercel.json",
    "netlify.toml",
    "fly.toml",
    "render.yaml",
    "render.yml",
    "procfile",
    "serverless.yml",
    "serverless.yaml",
    "pulumi.yaml",
    "pulumi.yml",
}
CHANGE_TYPES = {
    "A": "ADDED",
    "M": "MODIFIED",
    "D": "DELETED",
    "T": "TYPE_CHANGED",
}


class ProtectedAdmissionError(RuntimeError):
    """Expected failure that must become a stable NOT_EVALUATED payload."""

    def __init__(self, reason: str, detail: str) -> None:
        super().__init__(detail)
        self.reason = reason
        self.detail = detail


def _bounded_detail(value: str) -> str:
    printable = "".join(character if character.isprintable() else " " for character in value)
    normalized = " ".join(printable.split())
    return (normalized or "protected-admission evaluation failed")[:MAX_DETAIL_LENGTH]


def _safe_git_reason(error: SafeGitError) -> str:
    if error.reason == "GIT_REQUIRED":
        return "ADMISSION_GIT_REQUIRED"
    if error.reason == "GIT_TIMEOUT":
        return "ADMISSION_GIT_TIMEOUT"
    return "ADMISSION_GIT_SAFETY_REJECTED"


def _run_git(
    project_root: Path,
    args: list[str],
    *,
    failure_reason: str,
) -> str:
    try:
        completed = run_safe_git(project_root, args)
    except SafeGitError as error:
        raise ProtectedAdmissionError(
            _safe_git_reason(error),
            _bounded_detail(error.detail),
        ) from error

    if completed.returncode != 0:
        detail = completed.stderr or completed.stdout or "git command failed"
        raise ProtectedAdmissionError(failure_reason, _bounded_detail(detail))

    output_size = len(completed.stdout.encode("utf-8", errors="surrogateescape"))
    if output_size > MAX_GIT_OUTPUT_BYTES:
        raise ProtectedAdmissionError(
            "ADMISSION_CHANGE_SET_TOO_LARGE",
            "git output exceeded the bounded protected-admission limit",
        )
    return completed.stdout


def _single_line_git_output(output: str, reason: str, label: str) -> str:
    lines = output.splitlines()
    if len(lines) != 1 or not lines[0]:
        raise ProtectedAdmissionError(reason, f"git returned malformed {label}")
    return lines[0]


def resolve_project_root(value: str | Path) -> Path:
    try:
        project_root = Path(value).expanduser().resolve(strict=True)
    except (OSError, RuntimeError) as error:
        raise ProtectedAdmissionError(
            "ADMISSION_PROJECT_ROOT_INVALID",
            "project root does not resolve to a readable directory",
        ) from error

    if not project_root.is_dir() or not (project_root / ".git").exists():
        raise ProtectedAdmissionError(
            "ADMISSION_PROJECT_ROOT_INVALID",
            "--project-root must identify the root of a non-bare Git checkout",
        )

    output = _run_git(
        project_root,
        ["rev-parse", "--show-toplevel"],
        failure_reason="ADMISSION_PROJECT_ROOT_INVALID",
    )
    discovered_text = _single_line_git_output(
        output,
        "ADMISSION_PROJECT_ROOT_INVALID",
        "repository root",
    )
    if SURROGATE_ESCAPE.search(discovered_text):
        raise ProtectedAdmissionError(
            "ADMISSION_PATH_ENCODING_UNSUPPORTED",
            "repository root contains a path that is not valid UTF-8",
        )
    try:
        discovered = Path(discovered_text).resolve(strict=True)
    except (OSError, RuntimeError) as error:
        raise ProtectedAdmissionError(
            "ADMISSION_PROJECT_ROOT_INVALID",
            "Git reported a repository root that cannot be resolved",
        ) from error
    if discovered != project_root:
        raise ProtectedAdmissionError(
            "ADMISSION_PROJECT_ROOT_INVALID",
            "--project-root must point to the Git top-level directory",
        )
    return project_root


def validate_full_commit_sha(value: str, field: str) -> str:
    reason = "ADMISSION_BASE_SHA_INVALID" if field == "base" else "ADMISSION_HEAD_SHA_INVALID"
    if not isinstance(value, str) or FULL_COMMIT_SHA.fullmatch(value) is None:
        raise ProtectedAdmissionError(
            reason,
            f"--{field}-sha must be a full lowercase hexadecimal Git object ID",
        )
    return value


def resolve_commit_sha(project_root: Path, sha: str, field: str) -> str:
    reason = (
        "ADMISSION_BASE_COMMIT_UNAVAILABLE"
        if field == "base"
        else "ADMISSION_HEAD_COMMIT_UNAVAILABLE"
    )
    output = _run_git(
        project_root,
        ["rev-parse", "--verify", f"{sha}^{{commit}}"],
        failure_reason=reason,
    )
    resolved = _single_line_git_output(output, reason, f"{field} commit")
    if resolved != sha:
        raise ProtectedAdmissionError(
            reason,
            f"resolved {field} commit does not match the requested exact SHA",
        )
    return resolved


def compute_merge_base(project_root: Path, base_sha: str, head_sha: str) -> str:
    output = _run_git(
        project_root,
        ["merge-base", base_sha, head_sha],
        failure_reason="ADMISSION_MERGE_BASE_UNAVAILABLE",
    )
    merge_base = _single_line_git_output(
        output,
        "ADMISSION_MERGE_BASE_UNAVAILABLE",
        "merge base",
    )
    if FULL_COMMIT_SHA.fullmatch(merge_base) is None:
        raise ProtectedAdmissionError(
            "ADMISSION_MERGE_BASE_UNAVAILABLE",
            "Git returned a malformed merge-base SHA",
        )
    return merge_base


def validate_repo_relative_git_path(path: str) -> str:
    if SURROGATE_ESCAPE.search(path):
        raise ProtectedAdmissionError(
            "ADMISSION_PATH_ENCODING_UNSUPPORTED",
            "changed path is not valid UTF-8",
        )
    if not path or path.startswith("/") or "\0" in path:
        raise ProtectedAdmissionError(
            "ADMISSION_PATH_INVALID",
            "Git returned an invalid repository-relative path",
        )
    segments = path.split("/")
    if any(segment in {"", ".", ".."} for segment in segments):
        raise ProtectedAdmissionError(
            "ADMISSION_PATH_INVALID",
            "Git returned a path with an invalid relative segment",
        )
    return path


def parse_name_status_z(output: str) -> list[dict[str, str]]:
    if not output:
        return []
    if not output.endswith("\0"):
        raise ProtectedAdmissionError(
            "ADMISSION_GIT_OUTPUT_MALFORMED",
            "NUL-delimited Git diff output did not end with a delimiter",
        )
    tokens = output[:-1].split("\0")
    if len(tokens) % 2 != 0:
        raise ProtectedAdmissionError(
            "ADMISSION_GIT_OUTPUT_MALFORMED",
            "NUL-delimited Git diff output contained an incomplete record",
        )

    entries: list[dict[str, str]] = []
    for index in range(0, len(tokens), 2):
        status = tokens[index]
        path = validate_repo_relative_git_path(tokens[index + 1])
        change_type = CHANGE_TYPES.get(status)
        if change_type is None:
            raise ProtectedAdmissionError(
                "ADMISSION_GIT_OUTPUT_MALFORMED",
                f"unsupported Git change status: {status!r}",
            )
        entries.append({"change_type": change_type, "path": path})

    if len(entries) > MAX_CHANGED_ENTRIES:
        raise ProtectedAdmissionError(
            "ADMISSION_CHANGE_SET_TOO_LARGE",
            f"change set exceeded {MAX_CHANGED_ENTRIES} entries",
        )
    return entries


def changed_entries(project_root: Path, merge_base: str, head_sha: str) -> list[dict[str, str]]:
    output = _run_git(
        project_root,
        [
            "diff",
            "--name-status",
            "-z",
            "--no-renames",
            merge_base,
            head_sha,
            "--",
        ],
        failure_reason="ADMISSION_GIT_DIFF_FAILED",
    )
    return parse_name_status_z(output)


def _is_test_path(lower_path: str, segments: list[str], basename: str) -> bool:
    if any(segment in TEST_PATH_SEGMENTS for segment in segments):
        return True
    if basename in TEST_CONFIG_FILES:
        return True
    if basename.startswith("test_") or basename.startswith("test-"):
        return True
    stem = basename.rsplit(".", 1)[0]
    if stem.endswith("_test") or stem.endswith("-test"):
        return True
    return ".test." in basename or ".spec." in basename


def _is_ci_path(lower_path: str, segments: list[str], basename: str) -> bool:
    if lower_path in CI_ROOT_FILES or basename == "jenkinsfile":
        return True
    return any(tuple(segments[: len(prefix)]) == prefix for prefix in CI_PATH_PREFIXES)


def _is_policy_path(lower_path: str, segments: list[str], basename: str) -> bool:
    if lower_path in POLICY_FILES or basename == "codeowners":
        return True
    if any(segment in POLICY_PATH_SEGMENTS for segment in segments):
        return True
    return basename.endswith((".rego", ".sentinel"))


def _is_permissions_path(segments: list[str], basename: str) -> bool:
    if any(segment in PERMISSION_PATH_SEGMENTS for segment in segments):
        return True
    permission_prefixes = ("iam-", "iam_", "rbac-", "rbac_", "permissions.")
    return basename.startswith(permission_prefixes)


def _is_deployment_path(segments: list[str], basename: str) -> bool:
    if any(segment in DEPLOYMENT_PATH_SEGMENTS for segment in segments):
        return True
    if basename in DEPLOYMENT_FILES:
        return True
    return basename.endswith((".tf", ".tfvars", ".tf.json", ".tfvars.json"))


def classify_authority_path(path: str) -> list[str]:
    validated = validate_repo_relative_git_path(path)
    lower_path = validated.lower()
    segments = lower_path.split("/")
    basename = segments[-1]
    matches = {
        "TESTS": _is_test_path(lower_path, segments, basename),
        "CI_WORKFLOW": _is_ci_path(lower_path, segments, basename),
        "POLICY": _is_policy_path(lower_path, segments, basename),
        "PERMISSIONS_IAM": _is_permissions_path(segments, basename),
        "DEPLOYMENT_GUARDRAIL": _is_deployment_path(segments, basename),
    }
    return [category for category in CATEGORY_ORDER if matches[category]]


def _fingerprinted(payload: dict) -> dict:
    canonical = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")
    result = dict(payload)
    result["evaluation_fingerprint_sha256"] = hashlib.sha256(canonical).hexdigest()
    return result


def _base_payload() -> dict:
    return {
        "schema_version": SCHEMA_VERSION,
        "tool": {"name": "synrail", "version": __version__},
        "mode": "SHADOW",
        "merge_blocking": False,
        "policy_revision": POLICY_REVISION,
        "classifier_scope": CLASSIFIER_SCOPE,
        "diff_semantics": DIFF_SEMANTICS,
    }


def build_error_payload(reason: str, detail: str) -> dict:
    payload = {
        **_base_payload(),
        "evaluation_status": "ERROR",
        "result": "NOT_EVALUATED",
        "would_block": True,
        "changed_file_count": 0,
        "matched_file_count": 0,
        "reason_codes": [reason],
        "matches": [],
        "detail": _bounded_detail(detail),
    }
    return _fingerprinted(payload)


def build_shadow_evaluation(
    *,
    base_sha: str,
    head_sha: str,
    merge_base_sha: str,
    entries: list[dict[str, str]],
) -> dict:
    matches: list[dict] = []
    for entry in entries:
        categories = classify_authority_path(entry["path"])
        if not categories:
            continue
        matches.append(
            {
                "change_type": entry["change_type"],
                "path": entry["path"],
                "categories": categories,
                "reason_codes": [CATEGORY_REASON_CODES[value] for value in categories],
            }
        )
    matches.sort(key=lambda item: (item["path"], item["change_type"]))

    reason_codes = [
        CATEGORY_REASON_CODES[category]
        for category in CATEGORY_ORDER
        if any(category in item["categories"] for item in matches)
    ]
    observed = bool(matches)
    if not reason_codes:
        reason_codes = ["NO_AUTHORITY_CHANGE_OBSERVED"]

    detail = (
        f"Matched {len(matches)} of {len(entries)} changed paths against "
        f"{POLICY_REVISION}."
        if observed
        else f"No changed paths matched {POLICY_REVISION}."
    )
    payload = {
        **_base_payload(),
        "evaluation_status": "COMPLETE",
        "result": (
            "AUTHORITY_CHANGE_OBSERVED"
            if observed
            else "NO_AUTHORITY_CHANGE_OBSERVED"
        ),
        "would_block": observed,
        "base_sha": base_sha,
        "head_sha": head_sha,
        "merge_base_sha": merge_base_sha,
        "changed_file_count": len(entries),
        "matched_file_count": len(matches),
        "reason_codes": reason_codes,
        "matches": matches,
        "detail": detail,
    }
    return _fingerprinted(payload)


def evaluate_protected_admission(
    *,
    project_root: str | Path,
    base_sha: str,
    head_sha: str,
) -> tuple[int, dict]:
    """Evaluate one exact commit pair; matches never make shadow mode fail."""
    try:
        root = resolve_project_root(project_root)
        exact_base = validate_full_commit_sha(base_sha, "base")
        exact_head = validate_full_commit_sha(head_sha, "head")
        resolve_commit_sha(root, exact_base, "base")
        resolve_commit_sha(root, exact_head, "head")
        merge_base = compute_merge_base(root, exact_base, exact_head)
        entries = changed_entries(root, merge_base, exact_head)
        return 0, build_shadow_evaluation(
            base_sha=exact_base,
            head_sha=exact_head,
            merge_base_sha=merge_base,
            entries=entries,
        )
    except ProtectedAdmissionError as error:
        return 2, build_error_payload(error.reason, error.detail)
    except Exception as error:  # Defensive machine contract at the CLI boundary.
        return 2, build_error_payload(
            "ADMISSION_INTERNAL_ERROR",
            f"unexpected evaluator error: {error.__class__.__name__}",
        )
