#!/usr/bin/env python3
"""Offline-safe local installer for the current Synrail alpha lane."""

from __future__ import annotations

import argparse
import os
import stat
import subprocess
import sys
import textwrap
import venv
from pathlib import Path


def repo_root_from_script() -> Path:
    """Return the repository root by walking two levels up from this script's location."""
    return Path(__file__).resolve().parents[2]


def is_windows() -> bool:
    return os.name == "nt"


def scripts_dir_for_venv(venv_root: Path) -> Path:
    return venv_root / ("Scripts" if is_windows() else "bin")


def python_bin_for_venv(venv_root: Path) -> Path:
    return scripts_dir_for_venv(venv_root) / ("python.exe" if is_windows() else "python")


def synrail_bin_for_venv(venv_root: Path) -> Path:
    return scripts_dir_for_venv(venv_root) / ("synrail.cmd" if is_windows() else "synrail")


def ensure_venv(venv_root: Path) -> Path:
    builder = venv.EnvBuilder(with_pip=True, clear=False, symlinks=not is_windows())
    builder.create(venv_root)
    python_bin = python_bin_for_venv(venv_root)
    if not python_bin.exists():
        raise RuntimeError(f"venv python not found at {python_bin}")
    return python_bin


def site_packages_for_python(python_bin: Path) -> Path:
    completed = subprocess.run(
        [str(python_bin), "-c", "import sysconfig; print(sysconfig.get_path('purelib'))"],
        check=True,
        capture_output=True,
        text=True,
    )
    return Path(completed.stdout.strip())


def install_repo_path(site_packages: Path, repo_root: Path) -> Path:
    site_packages.mkdir(parents=True, exist_ok=True)
    pth_file = site_packages / "synrail_local_repo.pth"
    pth_file.write_text(str(repo_root) + "\n")
    return pth_file


def install_unix_script(target: Path) -> None:
    script = textwrap.dedent(
        f"""\
        #!/bin/sh
        exec "{target.parent / 'python'}" -c 'from alpha import main; raise SystemExit(main())' "$@"
        """
    )
    target.write_text(script)
    target.chmod(target.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def install_windows_script(target: Path) -> None:
    script = "@echo off\r\n\"%~dp0python.exe\" -c \"from alpha import main; raise SystemExit(main())\" %*\r\n"
    target.write_text(script)


def install_synrail_script(venv_root: Path) -> Path:
    target = synrail_bin_for_venv(venv_root)
    target.parent.mkdir(parents=True, exist_ok=True)
    if is_windows():
        install_windows_script(target)
    else:
        install_unix_script(target)
    return target


def verify_install(synrail_bin: Path) -> None:
    subprocess.run(
        [str(synrail_bin), "start", "--help"],
        check=True,
        capture_output=True,
        text=True,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Install the current Synrail alpha lane into a local venv without pip build isolation.")
    parser.add_argument("--venv", default=".venv", help="Virtualenv path to create or reuse. Default: .venv")
    parser.add_argument(
        "--project-root",
        help="Optional project root where the freshly installed synrail should immediately run `install-agent-files`.",
    )
    parser.add_argument(
        "--force-agent-files",
        action="store_true",
        help="If --project-root is set, pass --force to `synrail install-agent-files` after creating the venv.",
    )
    parser.add_argument("--skip-verify", action="store_true", help="Skip the final `synrail start --help` verification.")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    repo_root = repo_root_from_script()
    venv_root = Path(args.venv).resolve()
    python_bin = ensure_venv(venv_root)
    site_packages = site_packages_for_python(python_bin)
    pth_file = install_repo_path(site_packages, repo_root)
    synrail_bin = install_synrail_script(venv_root)

    if not args.skip_verify:
        verify_install(synrail_bin)

    project_root: Path | None = None
    if args.project_root:
        project_root = Path(args.project_root).resolve()
        project_root.mkdir(parents=True, exist_ok=True)
        install_cmd = [
            str(synrail_bin),
            "install-agent-files",
            "--project-root",
            str(project_root),
        ]
        if args.force_agent_files:
            install_cmd.append("--force")
        subprocess.run(
            install_cmd,
            check=True,
            capture_output=False,
            text=True,
        )

    rel_venv = os.path.relpath(venv_root, Path.cwd())
    rel_synrail = os.path.relpath(synrail_bin, Path.cwd())
    print("Synrail alpha install complete.")
    print(f"Virtualenv: {rel_venv}")
    print(f"Repo path linked via: {pth_file}")
    print(f"Command: {rel_synrail}")
    if project_root is not None:
        rel_project = os.path.relpath(project_root, Path.cwd())
        print(f"Agent files installed into: {rel_project}")
    print(f"Quick status: run `{rel_synrail}` inside your project.")
    print(f'Start a run: `{rel_synrail} start "Describe the bounded local change."`')
    print("If you already have `synrail` on PATH, you can use `synrail` instead.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
