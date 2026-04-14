"""Thin alpha entrypoint for the installable Synrail CLI."""

from __future__ import annotations

import sys
from pathlib import Path


def main() -> int:
    helpers_dir = Path(__file__).resolve().parent / "tools" / "reference"
    if str(helpers_dir) not in sys.path:
        sys.path.insert(0, str(helpers_dir))
    from synrail.tools.reference.synrail_cli_v0 import main as cli_main

    return cli_main()


if __name__ == "__main__":
    raise SystemExit(main())
