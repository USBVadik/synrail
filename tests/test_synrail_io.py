#!/usr/bin/env python3
"""Regression tests for shared Synrail IO helpers."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
TOOLS_ROOT = REPO_ROOT / "tools" / "reference"

if str(TOOLS_ROOT) not in sys.path:
    sys.path.insert(0, str(TOOLS_ROOT))

from synrail_io_v0 import save_json  # noqa: E402


class SynrailIoTests(unittest.TestCase):
    def test_save_json_creates_parent_directories(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_io_parent_") as tmpdir:
            path = Path(tmpdir) / "missing" / "nested" / "record.json"

            save_json(path, {"status": "OK"})

            self.assertEqual(json.loads(path.read_text()), {"status": "OK"})


if __name__ == "__main__":
    unittest.main()
