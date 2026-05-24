"""Synrail evidence fingerprint.

Computes a SHA-256 fingerprint over a final_result.json bundle so a reviewer
can recompute and confirm the bundle was not edited after acceptance.

Honest naming
-------------
We call this a "reproducible verification fingerprint", not a tamper-evident
log, because the hash lives in the same file (or an adjacent file) that an
editor can modify. Reviewers gain assurance only when the fingerprint is also
recorded in an immutable channel: the git commit hash of the prompt repo, a
CI run log, or a CloudWatch Logs entry. This module supports all three by
emitting the fingerprint to stdout for capture.
"""

from __future__ import annotations

import hashlib
import json
import os
from typing import Any


FINGERPRINT_FIELD = "synrail_fingerprint"


def _canonicalize(payload: dict[str, Any]) -> bytes:
    """Produce a deterministic byte representation of a JSON-compatible dict.

    sort_keys ensures key order does not affect the hash. We strip an
    existing fingerprint field before hashing so re-hashing is idempotent.
    """
    cleaned = {k: v for k, v in payload.items() if k != FINGERPRINT_FIELD}
    return json.dumps(cleaned, sort_keys=True, separators=(",", ":")).encode("utf-8")


def compute_fingerprint(payload: dict[str, Any]) -> str:
    """Return SHA-256 hex digest over the canonicalized payload."""
    return hashlib.sha256(_canonicalize(payload)).hexdigest()


def write_fingerprint(
    final_result_path: str | os.PathLike[str],
) -> tuple[str, str]:
    """Compute, embed, and emit the fingerprint for a final_result.json file.

    Returns (fingerprint, fingerprint_message). The message is suitable for
    direct stdout printing and includes both the hash and the verification
    command a reviewer should run.
    """
    with open(final_result_path) as f:
        payload = json.load(f)
    fingerprint = compute_fingerprint(payload)
    payload[FINGERPRINT_FIELD] = fingerprint
    with open(final_result_path, "w") as f:
        json.dump(payload, f, indent=2, default=str)
    message = (
        f"Synrail fingerprint: sha256={fingerprint}\n"
        f"  Bundle: {final_result_path}\n"
        f"  Recompute: python -c \"from tools.reference.synrail_fingerprint_v0"
        f" import compute_fingerprint; import json; "
        f"print(compute_fingerprint(json.load(open('{final_result_path}'))))\""
    )
    return fingerprint, message


def verify_fingerprint(
    final_result_path: str | os.PathLike[str],
) -> tuple[bool, str, str]:
    """Read a bundle, recompute its fingerprint, and compare to the stored one.

    Returns (matches, stored, computed). If the bundle has no stored
    fingerprint, returns (False, "", computed).
    """
    with open(final_result_path) as f:
        payload = json.load(f)
    stored = payload.get(FINGERPRINT_FIELD, "")
    computed = compute_fingerprint(payload)
    return (stored == computed and stored != "", stored, computed)


__all__ = [
    "FINGERPRINT_FIELD",
    "compute_fingerprint",
    "write_fingerprint",
    "verify_fingerprint",
]
