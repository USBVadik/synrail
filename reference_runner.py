"""Package-safe runner for reference helper modules."""

from __future__ import annotations

import importlib
import sys


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: python -m reference_runner <helper_module> [args...]", file=sys.stderr)
        return 2
    helper_module = sys.argv[1]
    module = importlib.import_module(f"tools.reference.{helper_module}")
    argv = [helper_module, *sys.argv[2:]]
    previous = sys.argv
    try:
        sys.argv = argv
        return int(module.main())
    finally:
        sys.argv = previous


if __name__ == "__main__":
    raise SystemExit(main())
