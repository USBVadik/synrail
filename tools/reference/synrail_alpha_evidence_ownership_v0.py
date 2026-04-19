#!/usr/bin/env python3
"""Classify whether an alpha run report should drive kernel roadmap decisions."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

VALID_FAILURE_OWNERS = {"none", "product", "harness", "agent", "operator", "mixed"}


def _strip_ticks(value: str) -> str:
    value = value.strip()
    if value.startswith("`") and value.endswith("`") and len(value) >= 2:
        return value[1:-1].strip()
    return value


def extract_markdown_field(text: str, label: str) -> str:
    """Extract a top-level markdown bullet field, including nested bullet values."""
    lines = text.splitlines()
    prefix = f"- {label}:"
    for index, line in enumerate(lines):
        if not line.startswith(prefix):
            continue
        inline = _strip_ticks(line[len(prefix):].strip())
        if inline:
            return inline
        next_index = index + 1
        while next_index < len(lines):
            candidate = lines[next_index]
            if not candidate.strip():
                next_index += 1
                continue
            if candidate.startswith("  - "):
                return _strip_ticks(candidate[4:].strip())
            if candidate.startswith("- "):
                break
            next_index += 1
        return ""
    return ""


def normalize_failure_owner(owner: str) -> str:
    normalized = owner.strip().lower().replace(" ", "_").replace("-", "_")
    return normalized if normalized in VALID_FAILURE_OWNERS else "unknown"


def verdict_strength(verdict: str) -> str:
    lowered = verdict.strip().lower()
    if not lowered:
        return "UNKNOWN"
    if "invalid as a product signal" in lowered or "harness evidence only" in lowered:
        return "INVALID"
    if re.search(r"\bstrong\b", lowered):
        return "STRONG"
    if re.search(r"\bmoderate\b", lowered):
        return "MODERATE"
    if re.search(r"\bweak\b|\btentative\b", lowered):
        return "WEAK"
    return "UNKNOWN"


def classify_roadmap_signal(*, failure_owner: str, verdict: str) -> dict:
    owner = normalize_failure_owner(failure_owner)
    strength = verdict_strength(verdict)

    if owner == "none":
        return {
            "failure_owner": owner,
            "verdict_strength": strength,
            "roadmap_signal_class": "CLEAN_PRODUCT_SIGNAL",
            "roadmap_track": "kernel",
            "kernel_roadmap_eligible": True,
            "why": "the run is not dominated by harness, operator, or mixed ownership, so it can directly update product judgment",
        }
    if owner == "product":
        return {
            "failure_owner": owner,
            "verdict_strength": strength,
            "roadmap_signal_class": "PRODUCT_OWNED_SIGNAL",
            "roadmap_track": "kernel",
            "kernel_roadmap_eligible": True,
            "why": "product-owned failures or wins should directly shape kernel roadmap decisions",
        }
    if owner == "mixed":
        if strength == "STRONG":
            return {
                "failure_owner": owner,
                "verdict_strength": strength,
                "roadmap_signal_class": "STRONG_MIXED_SIGNAL",
                "roadmap_track": "kernel_with_caution",
                "kernel_roadmap_eligible": True,
                "why": "mixed runs only drive roadmap decisions when the verdict is explicitly strong enough to isolate a real product seam despite residual harness or operator noise",
            }
        return {
            "failure_owner": owner,
            "verdict_strength": strength,
            "roadmap_signal_class": "MIXED_SIGNAL_TOO_WEAK",
            "roadmap_track": "manual_review",
            "kernel_roadmap_eligible": False,
            "why": "mixed ownership needs an explicitly strong verdict before it should move the kernel roadmap",
        }
    if owner == "harness":
        return {
            "failure_owner": owner,
            "verdict_strength": strength,
            "roadmap_signal_class": "HARNESS_ONLY_SIGNAL",
            "roadmap_track": "harness",
            "kernel_roadmap_eligible": False,
            "why": "harness-owned runs should inform harness repair, not kernel roadmap claims",
        }
    if owner == "operator":
        return {
            "failure_owner": owner,
            "verdict_strength": strength,
            "roadmap_signal_class": "OPERATOR_ONLY_SIGNAL",
            "roadmap_track": "operator",
            "kernel_roadmap_eligible": False,
            "why": "operator-owned runs should tighten operator flow or instructions, not be counted as kernel evidence",
        }
    if owner == "agent":
        return {
            "failure_owner": owner,
            "verdict_strength": strength,
            "roadmap_signal_class": "AGENT_BEHAVIOR_SIGNAL",
            "roadmap_track": "agent_conditioning",
            "kernel_roadmap_eligible": False,
            "why": "agent-behavior signals matter, but they should not masquerade as clean kernel roadmap evidence",
        }
    return {
        "failure_owner": owner,
        "verdict_strength": strength,
        "roadmap_signal_class": "UNKNOWN_OWNER_SIGNAL",
        "roadmap_track": "manual_review",
        "kernel_roadmap_eligible": False,
        "why": "unknown ownership needs manual review before it can influence roadmap decisions",
    }


def build_record(*, report_text: str, report_path: str = "") -> dict:
    failure_owner = extract_markdown_field(report_text, "Failure owner")
    verdict = extract_markdown_field(report_text, "Verdict")
    classification = classify_roadmap_signal(failure_owner=failure_owner, verdict=verdict)
    return {
        "schema_version": "alpha_evidence_ownership_record_v0",
        "report_path": report_path,
        "failure_owner": classification["failure_owner"],
        "verdict": verdict,
        "verdict_strength": classification["verdict_strength"],
        "roadmap_signal_class": classification["roadmap_signal_class"],
        "roadmap_track": classification["roadmap_track"],
        "kernel_roadmap_eligible": classification["kernel_roadmap_eligible"],
        "why": classification["why"],
    }


def load_report(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(prog="synrail-alpha-evidence-ownership-v0")
    parser.add_argument("--report-file", required=True)
    args = parser.parse_args()

    report_path = Path(args.report_file)
    record = build_record(report_text=load_report(report_path), report_path=str(report_path))
    print(json.dumps(record, indent=2, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
