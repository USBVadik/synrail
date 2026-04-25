#!/usr/bin/env python3
"""Shared focused repair-surface helpers for Synrail continuation."""

from __future__ import annotations

from pathlib import Path


def display_target_path(path: Path, *, target_path: str) -> str:
    if target_path:
        try:
            relative = path.resolve().relative_to(Path(target_path).resolve())
            return str(relative) or "."
        except ValueError:
            pass
    return str(path)


def proof_target_paths(*, artifact_root: str, target_path: str) -> dict[str, str]:
    if not artifact_root:
        return {
            "final_result": "final_result.json",
            "readback": "readback.txt",
            "scenario_proof": "scenario_proof.txt",
        }
    root = Path(artifact_root)
    return {
        "final_result": display_target_path(root / "final_result.json", target_path=target_path),
        "readback": display_target_path(root / "readback.txt", target_path=target_path),
        "scenario_proof": display_target_path(root / "scenario_proof.txt", target_path=target_path),
    }


def focused_repair_summary(*, current_step_id: str, current_step_subsurface_id: str, current_step_target_path: str) -> str:
    if current_step_id == "continue_forward_orchestration" or current_step_subsurface_id == "forward_orchestration_entrypoint":
        return "start this task through Synrail instead of editing proof artifacts"
    if current_step_subsurface_id == "clean_execution_surface_record":
        return "confirm the workspace is clean for this run via --clean-surface on the next retry"
    if current_step_subsurface_id == "final_result_payload":
        return f"update the result payload in {current_step_target_path}"
    if current_step_subsurface_id == "final_result_status_record":
        return f"set a trust-bearing final_result.status in {current_step_target_path}"
    if current_step_subsurface_id == "scope_alignment_record":
        return f"remove unrelated adjacent edits in {current_step_target_path} and keep only the requested additive change"
    if current_step_subsurface_id == "presentation_alignment_record":
        return f"remove extra emphasis styling in {current_step_target_path} and keep the new surface visually plain unless the task asked for styling"
    if current_step_subsurface_id == "diff_provenance_record":
        return f"record diff provenance in {current_step_target_path}"
    if current_step_subsurface_id == "artifact_identity_record":
        return f"record artifact identity in {current_step_target_path}"
    if current_step_subsurface_id == "cleanup_status_record":
        return f"record cleanup status in {current_step_target_path}"
    if current_step_subsurface_id == "readback_record":
        return f"record readback in {current_step_target_path}"
    if current_step_subsurface_id == "scenario_proof_record":
        return f"record scenario proof in {current_step_target_path}"
    if current_step_target_path:
        return f"edit {current_step_target_path} in place"
    if current_step_id == "repair_final_result_artifact":
        return "repair the final result artifact"
    if current_step_id == "complete_missing_proof_sections":
        return "complete the missing proof sections"
    return ""


def focused_repair_action_instruction(*, current_step_id: str, current_step_subsurface_id: str, current_step_target_path: str) -> str:
    if current_step_id == "continue_forward_orchestration" or current_step_subsurface_id == "forward_orchestration_entrypoint":
        return "Run synrail start for this task from the project root. Do not add forward_orchestration_entrypoint or proof-bundle fields to final_result.json."
    summary = focused_repair_summary(
        current_step_id=current_step_id,
        current_step_subsurface_id=current_step_subsurface_id,
        current_step_target_path=current_step_target_path,
    )
    if not summary:
        return ""
    capitalized = summary[0].upper() + summary[1:]
    if current_step_target_path:
        return f"{capitalized}. Leave every other proof surface unchanged."
    return f"{capitalized}. Stay inside the current bounded repair step."


def focused_repair_surface(
    *,
    current_step_id: str,
    stale_subsurfaces: list[str],
    artifact_root: str,
    target_path: str,
) -> dict[str, str]:
    proof_paths = proof_target_paths(artifact_root=artifact_root, target_path=target_path)
    stale_set = set(stale_subsurfaces)

    if current_step_id == "continue_forward_orchestration" and "forward_orchestration_entrypoint" in stale_set:
        return {
            "current_step_subsurface_id": "forward_orchestration_entrypoint",
            "current_step_target_path": "",
        }

    if current_step_id == "repair_final_result_artifact":
        focus_order = [
            ("final_result_payload", proof_paths["final_result"]),
            ("final_result_status_record", proof_paths["final_result"]),
            ("scope_alignment_record", proof_paths["final_result"]),
            ("presentation_alignment_record", proof_paths["final_result"]),
            ("diff_provenance_record", proof_paths["final_result"]),
            ("artifact_identity_record", proof_paths["final_result"]),
            ("cleanup_status_record", proof_paths["final_result"]),
        ]
        for subsurface_id, target in focus_order:
            if subsurface_id in stale_set:
                return {
                    "current_step_subsurface_id": subsurface_id,
                    "current_step_target_path": target,
                }

    if current_step_id == "complete_missing_proof_sections":
        final_result_focus_order = [
            ("diff_provenance_record", proof_paths["final_result"]),
            ("final_result_status_record", proof_paths["final_result"]),
            ("scope_alignment_record", proof_paths["final_result"]),
            ("presentation_alignment_record", proof_paths["final_result"]),
            ("artifact_identity_record", proof_paths["final_result"]),
            ("cleanup_status_record", proof_paths["final_result"]),
            ("final_result_payload", proof_paths["final_result"]),
        ]
        for subsurface_id, target in final_result_focus_order:
            if subsurface_id in stale_set:
                return {
                    "current_step_subsurface_id": subsurface_id,
                    "current_step_target_path": target,
                }
        focus_order = [
            ("readback_record", proof_paths["readback"]),
            ("scenario_proof_record", proof_paths["scenario_proof"]),
        ]
        matching = [
            {"current_step_subsurface_id": subsurface_id, "current_step_target_path": target}
            for subsurface_id, target in focus_order
            if subsurface_id in stale_set
        ]
        if len(matching) == 1:
            return matching[0]

    if current_step_id == "restore_readiness_truth" and "clean_execution_surface_record" in stale_set:
        return {
            "current_step_subsurface_id": "clean_execution_surface_record",
            "current_step_target_path": "",
        }

    return {
        "current_step_subsurface_id": "",
        "current_step_target_path": "",
    }
