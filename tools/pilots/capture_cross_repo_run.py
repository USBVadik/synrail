#!/usr/bin/env python3
"""Capture one privacy-bounded internal cross-repository Synrail pilot.

This tool records internal dogfood evidence only. It intentionally cannot label
a run as external empirical evidence and never copies raw verifier output or
absolute project/artifact paths into the resulting JSON.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import math
import os
import stat
import tempfile
from pathlib import Path

from tools.reference.synrail_safe_git_v0 import SafeGitError, run_safe_git


SCHEMA_VERSION = "internal_cross_repo_pilot_v0"
EVIDENCE_CLASS = "INTERNAL_CROSS_REPO_DOGFOOD"
CLAIM_SCOPE = "NOT_EXTERNAL_EMPIRICAL_EVIDENCE"
MAX_INPUT_BYTES = 4 * 1024 * 1024
FALSE_GREEN_VALUES = ("yes", "no", "unclear")
MAX_LABEL_CHARS = 200
MAX_TASK_CHARS = 1000
MAX_NOTE_CHARS = 4000
MAX_OBSERVATIONS = 50
MAX_OBSERVATION_CHARS = 500


class PilotCaptureError(Exception):
    """A named refusal while reading or writing a pilot record."""


def _now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def _read_regular_json(path: Path, *, required: bool = True) -> tuple[dict, str]:
    try:
        metadata = path.lstat()
    except FileNotFoundError:
        if required:
            raise PilotCaptureError(f"required Synrail artifact is missing: {path.name}") from None
        return {}, ""
    except OSError as exc:
        raise PilotCaptureError(f"cannot inspect Synrail artifact {path.name}: {exc}") from exc
    if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISREG(metadata.st_mode):
        raise PilotCaptureError(f"Synrail artifact must be a direct regular file: {path.name}")
    if metadata.st_size > MAX_INPUT_BYTES:
        raise PilotCaptureError(f"Synrail artifact exceeds capture limit: {path.name}")
    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0)
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = -1
    try:
        descriptor = os.open(path, flags)
        opened = os.fstat(descriptor)
        before_identity = (metadata.st_dev, metadata.st_ino, metadata.st_mode, metadata.st_size)
        opened_identity = (opened.st_dev, opened.st_ino, opened.st_mode, opened.st_size)
        if before_identity != opened_identity or not stat.S_ISREG(opened.st_mode):
            raise PilotCaptureError(f"Synrail artifact changed before capture: {path.name}")
        with os.fdopen(descriptor, "rb") as handle:
            descriptor = -1
            payload = handle.read(MAX_INPUT_BYTES + 1)
        if len(payload) > MAX_INPUT_BYTES:
            raise PilotCaptureError(f"Synrail artifact exceeds capture limit: {path.name}")
        after = path.lstat()
        after_identity = (after.st_dev, after.st_ino, after.st_mode, after.st_size)
        if before_identity != after_identity:
            raise PilotCaptureError(f"Synrail artifact changed during capture: {path.name}")
        parsed = json.loads(payload)
    except PilotCaptureError:
        raise
    except (OSError, json.JSONDecodeError) as exc:
        raise PilotCaptureError(f"cannot read Synrail artifact {path.name}: {exc}") from exc
    finally:
        if descriptor >= 0:
            os.close(descriptor)
    if not isinstance(parsed, dict):
        raise PilotCaptureError(f"Synrail artifact must contain a JSON object: {path.name}")
    return parsed, hashlib.sha256(payload).hexdigest()


def _git_revision(project_root: Path) -> str:
    try:
        completed = run_safe_git(project_root, ["rev-parse", "HEAD"])
    except SafeGitError as exc:
        raise PilotCaptureError(f"project revision is unavailable: {exc.detail}") from exc
    if completed.returncode != 0:
        raise PilotCaptureError("project revision is unavailable; capture requires a git-backed run")
    revision = completed.stdout.strip()
    if len(revision) != 40 or any(character not in "0123456789abcdef" for character in revision.lower()):
        raise PilotCaptureError("project revision is not a full git object id")
    return revision


def _seconds(value: float | None, *, field: str) -> float | None:
    if value is None:
        return None
    if not math.isfinite(value) or value < 0:
        raise PilotCaptureError(f"{field} must be non-negative")
    return round(value, 3)


def _bounded_text(value: str, *, field: str, maximum: int) -> str:
    normalized = value.strip()
    if not normalized:
        raise PilotCaptureError(f"{field} is required")
    if len(normalized) > maximum:
        raise PilotCaptureError(f"{field} exceeds the {maximum}-character limit")
    return normalized


def _bounded_observations(values: list[str], *, field: str) -> list[str]:
    if len(values) > MAX_OBSERVATIONS:
        raise PilotCaptureError(f"{field} exceeds the {MAX_OBSERVATIONS}-item limit")
    normalized = []
    for value in values:
        item = value.strip()
        if not item or len(item) > MAX_OBSERVATION_CHARS:
            raise PilotCaptureError(
                f"{field} entries must contain 1-{MAX_OBSERVATION_CHARS} characters"
            )
        normalized.append(item)
    return normalized


def _elapsed_seconds(started: object, closed: object) -> float | None:
    if not isinstance(started, str) or not started or not isinstance(closed, str) or not closed:
        return None
    try:
        start = dt.datetime.fromisoformat(started.replace("Z", "+00:00"))
        end = dt.datetime.fromisoformat(closed.replace("Z", "+00:00"))
    except ValueError:
        return None
    if start.tzinfo is None or end.tzinfo is None or end < start:
        return None
    return round((end - start).total_seconds(), 3)


def build_pilot_record(
    *,
    project_root: Path,
    artifact_root: Path,
    repository_label: str,
    task_summary: str,
    task_class: str,
    ecosystem: str,
    setup_seconds: float,
    total_operator_seconds: float | None,
    time_to_first_blocker_seconds: float | None,
    false_green_prevented: str,
    blocked_report_path: Path | None,
    operator_interventions: list[str],
    confusion_moments: list[str],
    notes: str,
) -> dict:
    project_root = project_root.resolve()
    artifact_root = artifact_root.resolve()
    if not project_root.is_dir():
        raise PilotCaptureError("project root must be an existing directory")
    if not artifact_root.is_dir():
        raise PilotCaptureError("artifact root must be an existing directory")
    if false_green_prevented not in FALSE_GREEN_VALUES:
        raise PilotCaptureError("false-green outcome must be yes, no, or unclear")
    repository_label = _bounded_text(
        repository_label,
        field="repository label",
        maximum=MAX_LABEL_CHARS,
    )
    task_summary = _bounded_text(task_summary, field="task summary", maximum=MAX_TASK_CHARS)
    task_class = _bounded_text(task_class, field="task class", maximum=MAX_LABEL_CHARS)
    operator_interventions = _bounded_observations(
        operator_interventions,
        field="operator interventions",
    )
    confusion_moments = _bounded_observations(confusion_moments, field="confusion moments")
    if len(notes.strip()) > MAX_NOTE_CHARS:
        raise PilotCaptureError(f"notes exceed the {MAX_NOTE_CHARS}-character limit")

    state, state_hash = _read_regular_json(artifact_root / "state.json")
    profile, profile_hash = _read_regular_json(artifact_root / "project_profile.json")
    report, report_hash = _read_regular_json(artifact_root / "report.json")
    final_result, final_result_hash = _read_regular_json(artifact_root / "final_result.json")
    receipt_payload, receipts_hash = _read_regular_json(artifact_root / "verification_receipts.json")

    recorded_project_root = profile.get("project_root", "")
    if (
        not isinstance(recorded_project_root, str)
        or not recorded_project_root
        or Path(recorded_project_root).resolve() != project_root
    ):
        raise PilotCaptureError("project root does not match the Synrail project profile")
    recorded_artifact_root = profile.get("artifact_root", "")
    if (
        not isinstance(recorded_artifact_root, str)
        or not recorded_artifact_root
        or Path(recorded_artifact_root).resolve() != artifact_root
    ):
        raise PilotCaptureError("artifact root does not match the Synrail project profile")
    run_id = state.get("run_id", "")
    if not isinstance(run_id, str) or not run_id or report.get("run_id") != run_id:
        raise PilotCaptureError("state and report do not bind to the same non-empty run id")
    if final_result.get("request_id") != run_id:
        raise PilotCaptureError("final_result.json does not bind to the captured run id")
    state_closure = state.get("closure", {})
    state_closure_status = state_closure.get("status", "") if isinstance(state_closure, dict) else ""
    if not state_closure_status or report.get("closure_status") != state_closure_status:
        raise PilotCaptureError("state and report do not agree on the final closure status")

    blocked_report_hash = ""
    first_blocker_reason = ""
    if blocked_report_path is not None:
        blocked_report, blocked_report_hash = _read_regular_json(blocked_report_path.expanduser())
        if blocked_report.get("run_id") != run_id:
            raise PilotCaptureError("blocked report belongs to a different run")
        if blocked_report.get("closure_status") == "ACCEPTED" or blocked_report.get("result") != "BLOCKED":
            raise PilotCaptureError("blocked report does not contain a non-accepted blocked verdict")
        first_blocker_reason = str(blocked_report.get("reason", "")).strip()
        if not first_blocker_reason or first_blocker_reason == "NONE":
            raise PilotCaptureError("blocked report does not name the blocker reason")
    if false_green_prevented == "yes" and not blocked_report_hash:
        raise PilotCaptureError("false-green=yes requires a preserved blocked report from the same run")

    receipts = receipt_payload.get("receipts", {})
    if not isinstance(receipts, dict):
        raise PilotCaptureError("verification receipt collection must be an object")
    lock = profile.get("verification_profiles", {})
    locked_profiles = lock.get("profiles", {}) if isinstance(lock, dict) else {}
    if not isinstance(locked_profiles, dict):
        raise PilotCaptureError("verification profile lock must contain a profile object")
    required_profiles = {
        name for name, item in locked_profiles.items() if isinstance(item, dict) and item.get("required", True)
    }
    if not required_profiles:
        raise PilotCaptureError("internal cross-repo pilots require at least one locked required profile")
    missing_receipts = sorted(required_profiles - set(receipts))
    if missing_receipts:
        raise PilotCaptureError("required verification receipts are missing: " + ", ".join(missing_receipts))
    profile_results = []
    for name in sorted(receipts):
        receipt = receipts[name]
        if not isinstance(name, str) or not isinstance(receipt, dict):
            raise PilotCaptureError("verification receipt entries must be named objects")
        duration = receipt.get("duration_seconds")
        exit_code = receipt.get("exit_code")
        if isinstance(duration, bool) or not isinstance(duration, (int, float)):
            raise PilotCaptureError(f"verification receipt duration is invalid: {name}")
        if not math.isfinite(float(duration)) or duration < 0:
            raise PilotCaptureError(f"verification receipt duration is invalid: {name}")
        if isinstance(exit_code, bool) or not isinstance(exit_code, int):
            raise PilotCaptureError(f"verification receipt exit code is invalid: {name}")
        if receipt.get("run_id") != run_id or receipt.get("config_sha256") != lock.get("config_sha256"):
            raise PilotCaptureError(f"verification receipt belongs to a different run or config: {name}")
        profile_results.append(
            {
                "profile": name,
                "duration_seconds": round(float(duration), 3),
                "exit_code": exit_code,
                "green": exit_code == 0 and not bool(receipt.get("timed_out", False)),
            }
        )

    closure_status = report.get("closure_status", "")
    accepted = closure_status == "ACCEPTED"
    verification_seconds = round(sum(item["duration_seconds"] for item in profile_results), 3)
    return {
        "schema_version": SCHEMA_VERSION,
        "evidence_class": EVIDENCE_CLASS,
        "claim_scope": CLAIM_SCOPE,
        "captured_at": _now_iso(),
        "run_id": run_id,
        "repository": {
            "label": repository_label,
            "revision": _git_revision(project_root),
            "ecosystem": _bounded_text(
                ecosystem or str(profile.get("project_type", "unknown")),
                field="ecosystem",
                maximum=100,
            ),
        },
        "task": {
            "summary": task_summary,
            "class": task_class,
        },
        "timing": {
            "setup_seconds": _seconds(setup_seconds, field="setup_seconds"),
            "time_to_first_blocker_seconds": _seconds(
                time_to_first_blocker_seconds,
                field="time_to_first_blocker_seconds",
            ),
            "verification_seconds": verification_seconds,
            "time_to_accepted_seconds": _elapsed_seconds(
                state.get("start_timestamp_utc"),
                state.get("closure_timestamp_utc"),
            ),
            "total_operator_seconds": _seconds(
                total_operator_seconds,
                field="total_operator_seconds",
            ),
        },
        "outcome": {
            "accepted": accepted,
            "closure_status": closure_status or "UNKNOWN",
            "report_result": str(report.get("result", "UNKNOWN")),
            "report_reason": str(report.get("reason", "UNKNOWN")),
            "false_green_prevented": false_green_prevented,
            "first_blocker_reason": first_blocker_reason or None,
            "operator_interventions": operator_interventions,
            "confusion_moments": confusion_moments,
        },
        "verification_profiles": profile_results,
        "artifact_bindings": {
            "state_sha256": state_hash,
            "project_profile_sha256": profile_hash,
            "report_sha256": report_hash,
            "final_result_sha256": final_result_hash,
            "verification_receipts_sha256": receipts_hash,
            "blocked_report_sha256": blocked_report_hash or None,
        },
        "notes": notes.strip(),
    }


def _atomic_write_json(path: Path, payload: dict, *, force: bool) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and not force:
        raise PilotCaptureError(f"output already exists: {path}")
    if path.is_symlink() or (path.exists() and not path.is_file()):
        raise PilotCaptureError("output must be a direct regular file path")
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(payload, handle, indent=2, ensure_ascii=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--project-root", type=Path, required=True)
    result.add_argument("--artifact-root", type=Path, required=True)
    result.add_argument("--output", type=Path, required=True)
    result.add_argument("--repository-label", required=True)
    result.add_argument("--task-summary", required=True)
    result.add_argument("--task-class", required=True)
    result.add_argument("--ecosystem", default="")
    result.add_argument("--setup-seconds", type=float, required=True)
    result.add_argument("--total-operator-seconds", type=float)
    result.add_argument("--time-to-first-blocker-seconds", type=float)
    result.add_argument("--false-green-prevented", choices=FALSE_GREEN_VALUES, required=True)
    result.add_argument(
        "--blocked-report",
        type=Path,
        help="Preserved blocked report from the same run; required when false-green-prevented=yes.",
    )
    result.add_argument("--intervention", action="append", default=[])
    result.add_argument("--confusion", action="append", default=[])
    result.add_argument("--notes", default="")
    result.add_argument("--force", action="store_true")
    return result


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        record = build_pilot_record(
            project_root=args.project_root,
            artifact_root=args.artifact_root,
            repository_label=args.repository_label,
            task_summary=args.task_summary,
            task_class=args.task_class,
            ecosystem=args.ecosystem,
            setup_seconds=args.setup_seconds,
            total_operator_seconds=args.total_operator_seconds,
            time_to_first_blocker_seconds=args.time_to_first_blocker_seconds,
            false_green_prevented=args.false_green_prevented,
            blocked_report_path=args.blocked_report,
            operator_interventions=args.intervention,
            confusion_moments=args.confusion,
            notes=args.notes,
        )
        _atomic_write_json(args.output, record, force=args.force)
    except PilotCaptureError as exc:
        print(f"Pilot capture blocked: {exc}")
        return 2
    print(f"Internal pilot record: {args.output}")
    print(f"Evidence class: {EVIDENCE_CLASS}")
    print(f"Claim scope: {CLAIM_SCOPE}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
