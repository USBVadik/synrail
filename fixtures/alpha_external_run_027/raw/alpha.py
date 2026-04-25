"""Thin alpha entrypoint for the installable Synrail CLI."""

from __future__ import annotations

def main() -> int:
    """Thin alpha entrypoint for the installable Synrail CLI."""
    from tools.reference.synrail_cli_v0 import main as cli_main

    return cli_main()


if __name__ == "__main__":
    raise SystemExit(main())
