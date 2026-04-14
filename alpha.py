"""Thin alpha entrypoint for the installable Synrail CLI."""

from __future__ import annotations

import sys
from pathlib import Path


def main() -> int:
    module_dir = Path(__file__).resolve().parent
    helper_candidates = [
        module_dir / "tools" / "reference",
        module_dir / "synrail" / "tools" / "reference",
    ]
    for helpers_dir in helper_candidates:
        if helpers_dir.exists() and str(helpers_dir) not in sys.path:
            sys.path.insert(0, str(helpers_dir))
    try:
        from synrail.tools.reference.synrail_cli_v0 import main as cli_main
    except ModuleNotFoundError:
        from tools.reference.synrail_cli_v0 import main as cli_main
    return cli_main()


if __name__ == "__main__":
    raise SystemExit(main())
