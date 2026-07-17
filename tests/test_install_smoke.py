#!/usr/bin/env python3
"""Install smoke for the supported Synrail tester path."""

from __future__ import annotations

import json
import os
import re
import shutil
import sys
import subprocess
import tempfile
import time
import tomllib
import unittest
from importlib import metadata as importlib_metadata
from pathlib import Path
from unittest import mock


REPO_ROOT = Path(__file__).resolve().parents[1]
INSTALLER = REPO_ROOT / "tools" / "reference" / "synrail_install_v0.py"
PYTHON = sys.executable


def installed_synrail_bin(venv_dir: Path) -> Path:
    if os.name == "nt":
        return venv_dir / "Scripts" / "synrail.cmd"
    return venv_dir / "bin" / "synrail"


def installed_synrail_command(synrail_bin: Path, *args: str) -> list[str]:
    if os.name == "nt":
        return [os.environ.get("COMSPEC", "cmd.exe"), "/c", str(synrail_bin), *args]
    return [str(synrail_bin), *args]


def json_load(path: Path) -> dict:
    return json.loads(path.read_text())


def run_checked(args: list[str], **kwargs) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(args, capture_output=True, text=True, **kwargs)
    if result.returncode != 0:
        command = " ".join(args)
        raise AssertionError(
            f"command failed with exit code {result.returncode}: {command}\n"
            f"--- stdout ---\n{result.stdout}\n"
            f"--- stderr ---\n{result.stderr}"
        )
    return result


class InstallSmokeTests(unittest.TestCase):
    def test_alpha_entrypoint_delegates_to_public_cli(self) -> None:
        import alpha

        with mock.patch("tools.reference.synrail_cli_v0.main", return_value=0) as cli_main:
            self.assertEqual(0, alpha.main())
        cli_main.assert_called_once_with()

    def test_package_and_runtime_version_share_one_source(self) -> None:
        project = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text())
        makefile = (REPO_ROOT / "Makefile").read_text()
        from tools.reference.synrail_alpha_telemetry_v0 import synrail_version
        from tools.reference.synrail_version_v0 import __version__

        self.assertIn("version", project["project"]["dynamic"])
        self.assertEqual(
            "tools.reference.synrail_version_v0.__version__",
            project["tool"]["setuptools"]["dynamic"]["version"]["attr"],
        )
        self.assertIn(
            "$(DEV_STAMP): pyproject.toml constraints-dev.txt tools/reference/synrail_version_v0.py $(PYTHON)",
            makefile,
        )
        with mock.patch(
            "tools.reference.synrail_alpha_telemetry_v0.importlib_metadata.version",
            side_effect=importlib_metadata.PackageNotFoundError,
        ):
            self.assertEqual(__version__, synrail_version())

    def test_dev_build_backend_is_locked_and_audited(self) -> None:
        constraints = (REPO_ROOT / "constraints-dev.txt").read_text()
        makefile = (REPO_ROOT / "Makefile").read_text()
        workflow = (REPO_ROOT / ".github" / "workflows" / "security-hygiene.yml").read_text()

        self.assertIn("setuptools==83.0.0", constraints)
        self.assertIn(
            "$(PYTHON) -m pip install --upgrade setuptools -c $(CONSTRAINTS)",
            makefile,
        )
        self.assertIn(
            "python -m pip install --upgrade pip setuptools -c constraints-dev.txt",
            workflow,
        )

    def test_public_cli_does_not_advertise_retired_contest_commands(self) -> None:
        result = subprocess.run(
            [PYTHON, str(REPO_ROOT / "alpha.py"), "--help"],
            check=True,
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
        )

        self.assertNotIn("verify-aws-state", result.stdout)
        self.assertNotIn("fingerprint", result.stdout)
        self.assertIn("suggest-verification", result.stdout)

    def test_tracked_agent_policies_expose_current_behavioral_lifecycle(self) -> None:
        for name in ("AGENTS.md", "CLAUDE.md", "GEMINI.md"):
            policy = (REPO_ROOT / name).read_text(encoding="utf-8")
            with self.subTest(policy=name):
                self.assertIn("## Behavioral Verification Gate", policy)
                self.assertIn("synrail preflight", policy)
                self.assertIn("synrail suggest-verification", policy)
                self.assertIn("synrail verify", policy)
                self.assertIn("Never change it during an active run to evade a failed profile", policy)

    def test_false_green_demo_executes_real_block_and_repair_loop(self) -> None:
        bash = shutil.which("bash")
        self.assertIsNotNone(bash, "the live false-green demo requires bash")
        env = os.environ.copy()
        env["SYNRAIL_PYTHON"] = PYTHON
        result = subprocess.run(
            [bash, str(REPO_ROOT / "examples" / "false-green-demo" / "run_demo.sh")],
            check=True,
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            env=env,
        )

        self.assertIn("Verification unit: FAIL (exit 1)", result.stdout)
        self.assertIn("Synrail: Status: Verification Failed", result.stdout)
        self.assertIn("Verification unit: GREEN", result.stdout)
        self.assertIn("Synrail: Status: Accepted", result.stdout)
        self.assertIn(
            "Demo result: plausible proof blocked while tests were red; verified behavior accepted.",
            result.stdout,
        )

    @unittest.skipIf(os.name == "nt", "The source-checkout fallback test uses a POSIX-only isolated PATH")
    def test_false_green_demo_falls_back_to_repo_local_alpha(self) -> None:
        bash = shutil.which("bash")
        self.assertIsNotNone(bash, "the live false-green demo requires bash")
        with tempfile.TemporaryDirectory(prefix="synrail_demo_alpha_fallback_") as tmpdir:
            isolated_root = Path(tmpdir) / "synrail"
            script_dir = isolated_root / "examples" / "false-green-demo"
            script_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy2(REPO_ROOT / "alpha.py", isolated_root / "alpha.py")
            shutil.copy2(REPO_ROOT / "reference_runner.py", isolated_root / "reference_runner.py")
            shutil.copytree(REPO_ROOT / "tools", isolated_root / "tools")
            # A source checkout includes the doctor-coverage corpus fixtures; without
            # them, a real fallback rightly refuses to claim the workspace is ready.
            shutil.copytree(REPO_ROOT / "fixtures", isolated_root / "fixtures")
            shutil.copy2(
                REPO_ROOT / "examples" / "false-green-demo" / "run_demo.sh",
                script_dir / "run_demo.sh",
            )

            env = os.environ.copy()
            env["SYNRAIL_PYTHON"] = PYTHON
            env["PATH"] = os.pathsep.join(
                path
                for path in os.get_exec_path(env)
                if not (Path(path) / "synrail").exists()
            )
            result = subprocess.run(
                [bash, str(script_dir / "run_demo.sh")],
                check=True,
                cwd=isolated_root,
                capture_output=True,
                text=True,
                env=env,
            )

        self.assertIn("Synrail: Status: Verification Failed", result.stdout)
        self.assertIn("Synrail: Status: Accepted", result.stdout)

    def _assert_installed_start_path(self, synrail_bin: Path, project_root: Path) -> None:
        artifact_root = project_root / ".synrail"

        help_result = subprocess.run(
            installed_synrail_command(synrail_bin, "start", "--help"),
            check=True,
            capture_output=True,
            text=True,
        )
        self.assertIn("--project-root", help_result.stdout)
        self.assertIn("--ephemeral", help_result.stdout)
        self.assertIn("--task-identity", help_result.stdout)
        self.assertIn("task_request", help_result.stdout)

        project_root.mkdir(parents=True, exist_ok=True)
        start_result = subprocess.run(
            installed_synrail_command(synrail_bin, "start", "install smoke"),
            check=True,
            cwd=project_root,
            capture_output=True,
            text=True,
        )

        self.assertIn("Controlled run started.", start_result.stdout)
        self.assertIn(
            "Do this now: make the bounded change and run local verification; then use synrail record for one tracked file, synrail record --all-modified for a small tracked batch, or strengthen final_result.json for other contours.",
            start_result.stdout,
        )
        self.assertIn("Starter proof surface is ready for this run.", start_result.stdout)
        self.assertIn("Artifact root: .synrail", start_result.stdout)
        self.assertIn("fallback note: readback.txt and scenario_proof.txt stay hidden by default unless a later synrail check names one.", start_result.stdout)
        self.assertIn("Need a canonical final_result shape? run synrail final-result-template", start_result.stdout)
        self.assertIn("Then run: synrail check", start_result.stdout)
        self.assertIn("Fast tracked single-file path:", start_result.stdout)
        self.assertIn("record path/to/file", start_result.stdout)
        self.assertTrue((artifact_root / "state.json").exists())
        self.assertTrue((artifact_root / "acceptance_criteria.json").exists())
        self.assertTrue((artifact_root / "project_profile.json").exists())
        self.assertTrue((artifact_root / "bootstrap.json").exists())
        self.assertTrue((artifact_root / "proof_request.json").exists())
        self.assertTrue((artifact_root / "final_result.json").exists())
        self.assertFalse((artifact_root / "readback.txt").exists())
        self.assertFalse((artifact_root / "scenario_proof.txt").exists())
        self.assertTrue((artifact_root / "target_identity.txt").exists())
        self.assertTrue((artifact_root / "task_identity.txt").exists())
        self.assertTrue((artifact_root / "prompt_identity.txt").exists())

    def test_supported_installer_boots_synrail_start(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_install_smoke_") as tmpdir:
            root = Path(tmpdir)
            venv_dir = root / "venv"
            project_root = root / "project"

            run_checked(
                [PYTHON, str(INSTALLER), "--venv", str(venv_dir)],
                cwd=REPO_ROOT,
            )
            self._assert_installed_start_path(
                installed_synrail_bin(venv_dir),
                project_root,
            )

    def test_supported_installer_is_idempotent(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_editable_install_smoke_") as tmpdir:
            root = Path(tmpdir)
            venv_dir = root / "venv"
            project_root = root / "project"

            run_checked(
                [PYTHON, str(INSTALLER), "--venv", str(venv_dir)],
                cwd=REPO_ROOT,
            )
            run_checked(
                [PYTHON, str(INSTALLER), "--venv", str(venv_dir)],
                cwd=REPO_ROOT,
            )
            self._assert_installed_start_path(
                installed_synrail_bin(venv_dir),
                project_root,
            )

    def test_ephemeral_artifact_root_stays_outside_project_and_can_be_cleaned(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_ephemeral_smoke_") as tmpdir:
            project_root = Path(tmpdir) / "project"
            project_root.mkdir(parents=True, exist_ok=True)

            start = subprocess.run(
                [
                    PYTHON,
                    str(REPO_ROOT / "alpha.py"),
                    "start",
                    "--ephemeral",
                    "--project-root",
                    str(project_root),
                    "ephemeral smoke",
                ],
                check=True,
                cwd=REPO_ROOT,
                capture_output=True,
                text=True,
            )

            artifact_line = next(line for line in start.stdout.splitlines() if line.startswith("Artifact root: "))
            artifact_root = Path(artifact_line.split(": ", 1)[1]).expanduser().resolve()
            self.assertTrue(artifact_root.exists())
            self.assertTrue((artifact_root / "state.json").exists())
            self.assertTrue((artifact_root / "final_result.json").exists())
            self.assertFalse((project_root / ".synrail").exists())
            self.assertNotEqual(artifact_root.parent, project_root)

            check = subprocess.run(
                [
                    PYTHON,
                    str(REPO_ROOT / "alpha.py"),
                    "check",
                    "--ephemeral",
                    "--project-root",
                    str(project_root),
                ],
                cwd=REPO_ROOT,
                capture_output=True,
                text=True,
            )
            self.assertNotIn("PATH_SCOPE_VIOLATION", check.stdout)
            self.assertNotIn("PATH_SCOPE_VIOLATION", check.stderr)

            cleanup = subprocess.run(
                [
                    PYTHON,
                    str(REPO_ROOT / "alpha.py"),
                    "cleanup",
                    "--ephemeral",
                    "--project-root",
                    str(project_root),
                ],
                check=True,
                cwd=REPO_ROOT,
                capture_output=True,
                text=True,
            )
            self.assertIn("Synrail artifacts removed.", cleanup.stdout)
            self.assertFalse(artifact_root.exists())
            self.assertFalse((project_root / ".synrail").exists())

    def test_ephemeral_start_prunes_stale_cache_runs(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_ephemeral_janitor_") as tmpdir:
            root = Path(tmpdir)
            project_root = root / "project"
            cache_root = root / "cache"
            stale_root = cache_root / "runs" / "stale-run" / "current"
            project_root.mkdir(parents=True, exist_ok=True)
            stale_root.mkdir(parents=True, exist_ok=True)
            (stale_root / "state.json").write_text("{}\n")
            old = time.time() - (3 * 24 * 60 * 60)
            for path in [stale_root / "state.json", stale_root, stale_root.parent]:
                os.utime(path, (old, old))
            env = {**os.environ, "SYNRAIL_CACHE_HOME": str(cache_root)}

            start = subprocess.run(
                [
                    PYTHON,
                    str(REPO_ROOT / "alpha.py"),
                    "start",
                    "--ephemeral",
                    "--project-root",
                    str(project_root),
                    "ephemeral janitor smoke",
                ],
                check=True,
                cwd=REPO_ROOT,
                env=env,
                capture_output=True,
                text=True,
            )

            artifact_line = next(line for line in start.stdout.splitlines() if line.startswith("Artifact root: "))
            artifact_root = Path(artifact_line.split(": ", 1)[1]).expanduser().resolve()
            self.assertTrue(artifact_root.exists())
            self.assertFalse(stale_root.exists())
            self.assertFalse((project_root / ".synrail").exists())

            cleanup = subprocess.run(
                [
                    PYTHON,
                    str(REPO_ROOT / "alpha.py"),
                    "cleanup",
                    "--ephemeral",
                    "--project-root",
                    str(project_root),
                ],
                check=True,
                cwd=REPO_ROOT,
                env=env,
                capture_output=True,
                text=True,
            )
            self.assertIn("Synrail artifacts removed.", cleanup.stdout)

    def test_ephemeral_reused_run_names_safe_abandon_command(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_ephemeral_reuse_") as tmpdir:
            root = Path(tmpdir)
            project_root = root / "project"
            cache_root = root / "cache"
            project_root.mkdir(parents=True, exist_ok=True)
            env = {**os.environ, "SYNRAIL_CACHE_HOME": str(cache_root)}

            first = subprocess.run(
                [
                    PYTHON,
                    str(REPO_ROOT / "alpha.py"),
                    "start",
                    "--ephemeral",
                    "--project-root",
                    str(project_root),
                    "first ephemeral task",
                ],
                check=True,
                cwd=REPO_ROOT,
                env=env,
                capture_output=True,
                text=True,
            )
            artifact_line = next(line for line in first.stdout.splitlines() if line.startswith("Artifact root: "))
            artifact_root = Path(artifact_line.split(": ", 1)[1]).expanduser().resolve()
            first_state = json.loads((artifact_root / "state.json").read_text())

            second = subprocess.run(
                [
                    PYTHON,
                    str(REPO_ROOT / "alpha.py"),
                    "start",
                    "--ephemeral",
                    "--project-root",
                    str(project_root),
                    "different task after an abandoned run",
                ],
                check=True,
                cwd=REPO_ROOT,
                env=env,
                capture_output=True,
                text=True,
            )

            self.assertIn("Synrail already has a controlled run in progress.", second.stdout)
            self.assertIn("If this task was intentionally abandoned", second.stdout)
            self.assertIn("cleanup --ephemeral --project-root", second.stdout)
            self.assertIn("it does not modify project files", second.stdout)
            self.assertEqual(first_state["run_id"], json.loads((artifact_root / "state.json").read_text())["run_id"])

            cleanup = subprocess.run(
                [
                    PYTHON,
                    str(REPO_ROOT / "alpha.py"),
                    "cleanup",
                    "--ephemeral",
                    "--project-root",
                    str(project_root),
                ],
                check=True,
                cwd=REPO_ROOT,
                env=env,
                capture_output=True,
                text=True,
            )
            self.assertIn("Synrail artifacts removed.", cleanup.stdout)
            self.assertFalse(artifact_root.exists())

    @unittest.skipUnless(shutil.which("git"), "git is required for git-root discovery smoke")
    def test_ephemeral_start_from_subdir_uses_git_project_root(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_ephemeral_gitroot_") as tmpdir:
            root = Path(tmpdir)
            project_root = root / "project"
            nested = project_root / "src" / "nested"
            cache_root = root / "cache"
            nested.mkdir(parents=True, exist_ok=True)
            subprocess.run(["git", "init"], check=True, cwd=project_root, capture_output=True, text=True)
            env = {**os.environ, "SYNRAIL_CACHE_HOME": str(cache_root)}

            start = subprocess.run(
                [
                    PYTHON,
                    str(REPO_ROOT / "alpha.py"),
                    "start",
                    "--ephemeral",
                    "ephemeral git root smoke",
                ],
                check=True,
                cwd=nested,
                env=env,
                capture_output=True,
                text=True,
            )

            artifact_line = next(line for line in start.stdout.splitlines() if line.startswith("Artifact root: "))
            artifact_root = Path(artifact_line.split(": ", 1)[1]).expanduser().resolve()
            profile = json_load(artifact_root / "project_profile.json")
            self.assertEqual(Path(profile["project_root"]).resolve(), project_root.resolve())
            self.assertFalse((project_root / ".synrail").exists())
            self.assertFalse((nested / ".synrail").exists())

            cleanup = subprocess.run(
                [
                    PYTHON,
                    str(REPO_ROOT / "alpha.py"),
                    "cleanup",
                    "--ephemeral",
                ],
                check=True,
                cwd=nested,
                env=env,
                capture_output=True,
                text=True,
            )
            self.assertIn("Synrail artifacts removed.", cleanup.stdout)

    def test_supported_installer_can_install_agent_files_into_project(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_install_agent_files_smoke_") as tmpdir:
            root = Path(tmpdir)
            venv_dir = root / "venv"
            project_root = root / "project"
            project_root.mkdir(parents=True, exist_ok=True)
            (project_root / "alpha.py").write_text("print('stub')\n")
            (project_root / "GEMINI.md").write_text("# Existing Gemini Context\n\nKeep this repo focused.\n")

            result = run_checked(
                [
                    PYTHON,
                    str(INSTALLER),
                    "--venv",
                    str(venv_dir),
                    "--project-root",
                    str(project_root),
                ],
                cwd=REPO_ROOT,
            )

            self.assertIn("Agent adoption files are ready.", result.stdout)
            self.assertIn("Agent files installed into:", result.stdout)
            self.assertIn("Git preflight:", result.stdout)
            self.assertIn("No-git proof path: leave git_diff empty and use structured provenance", result.stdout)
            self.assertIn("diff_provenance_records/per_file_diff_provenance", result.stdout)
            self.assertIn("Quick status: run `", result.stdout)
            self.assertIn("inside your project.", result.stdout)
            self.assertIn("Command:", result.stdout)
            self.assertIn('Start a run: `', result.stdout)
            self.assertIn(' start "Describe the bounded local change."`', result.stdout)
            self.assertIn("Repo-native status: `python3 alpha.py`", result.stdout)
            self.assertIn('Repo-native start: `python3 alpha.py start "Describe the bounded local change."`', result.stdout)
            self.assertIn("Repo-native check: `python3 alpha.py check`", result.stdout)
            self.assertIn("Repo-native runtime helper: `python3 alpha.py runtime-helper`", result.stdout)
            self.assertTrue((project_root / "AGENTS.md").exists())
            self.assertTrue((project_root / "CLAUDE.md").exists())
            gemini = (project_root / "GEMINI.md").read_text()
            claude = (project_root / "CLAUDE.md").read_text()
            self.assertIn("# Existing Gemini Context", gemini)
            self.assertIn("<!-- SYNRAIL_GEMINI_START -->", gemini)
            self.assertIn("Use Synrail as the default local control path", gemini)
            self.assertIn("cheapest honest order", gemini)
            self.assertIn("If `git` is unavailable on this host, do not invent `git_diff`", gemini)
            self.assertIn("Keep `diff_provenance.verification_command` recheckable", gemini)
            self.assertIn("Do not use pipes, `&&`, `sed`, `awk`, `perl`, subshells", gemini)
            self.assertIn("Do not create helper scripts or make edits for an orientation-only question.", gemini)
            self.assertIn("Do not turn project recall into repo archaeology.", gemini)
            self.assertIn("Use Synrail as the default local control path", claude)
            self.assertIn("cheapest honest order", claude)
            self.assertIn("If `git` is unavailable on this host, do not invent `git_diff`", claude)
            self.assertIn("Keep `diff_provenance.verification_command` recheckable", claude)
            self.assertIn("Do not use pipes, `&&`, `sed`, `awk`, `perl`, subshells", claude)
            self.assertIn("Do not create helper scripts or make edits for an orientation-only question.", claude)

    def test_current_user_docs_have_a_short_truthful_path(self) -> None:
        first_run_guide = (REPO_ROOT / "docs" / "core" / "FIRST_RUN_GUIDE.md").read_text()
        public_readme = (REPO_ROOT / "README.md").read_text()
        docs_readme = (REPO_ROOT / "docs" / "README.md").read_text()
        review_readme = (REPO_ROOT / "docs" / "review" / "README.md").read_text()
        profiles_guide = (REPO_ROOT / "docs" / "advanced" / "VERIFICATION_PROFILES.md").read_text()
        repo_clean_guide = (REPO_ROOT / "docs" / "advanced" / "REPO_CLEAN_WORKFLOWS.md").read_text()
        reference_readme = (REPO_ROOT / "tools" / "reference" / "README.md").read_text()
        normalized_profiles_guide = " ".join(profiles_guide.split())

        # Public onboarding stays short. The deeper operating detail belongs in
        # explicitly named advanced guides rather than in the landing page.
        self.assertLessEqual(len(public_readme.splitlines()), 190)
        self.assertLessEqual(len(first_run_guide.splitlines()), 220)
        self.assertIn(
            'Synrail is a local acceptance gate for coding agents. It blocks a\nfalse-green "done" claim until task-scoped proof is rechecked.',
            public_readme,
        )
        self.assertIn("## See It In 30 Seconds", public_readme)
        self.assertIn("Agent: fixed add(); tests pass", public_readme)
        self.assertIn("Verification unit: FAIL (exit 1)", public_readme)
        self.assertIn("Synrail: Status: Verification Failed", public_readme)
        self.assertIn("Synrail: Status: Accepted", public_readme)
        self.assertIn("![Synrail false-green demo](examples/false-green-demo/assets/synrail-false-green-hero.gif)", public_readme)
        self.assertIn("## Try It In 2 Minutes", public_readme)
        self.assertIn("make install-dev", public_readme)
        self.assertIn("make demo", public_readme)
        self.assertIn("## Pick The Smallest Useful Lane", public_readme)
        self.assertIn("[Small tracked change](docs/core/FIRST_RUN_GUIDE.md#1-prove-one-small-tracked-change)", public_readme)
        self.assertIn("[Behavioral verification](docs/core/FIRST_RUN_GUIDE.md#2-enforce-a-behavioral-claim)", public_readme)
        self.assertIn("[Repo-clean workflow](docs/core/FIRST_RUN_GUIDE.md#3-keep-artifacts-outside-many-repositories)", public_readme)
        self.assertIn("## Is This Just Post-Review?", public_readme)
        self.assertIn("you are acting as Synrail manually", " ".join(public_readme.split()))
        self.assertIn("## What It Does Not Claim", public_readme)
        self.assertIn("not a hostile same-user security boundary", public_readme)
        self.assertIn("## The Everyday Loop", public_readme)
        self.assertIn("synrail record --all-modified", public_readme)
        self.assertIn("`record` writes proof, not acceptance.", public_readme)
        self.assertIn("[Behavioral profiles](docs/advanced/VERIFICATION_PROFILES.md)", public_readme)
        self.assertIn("[Repo-clean workflows](docs/advanced/REPO_CLEAN_WORKFLOWS.md)", public_readme)
        self.assertNotIn("python3 tools/reference/synrail_install_v0.py", public_readme)

        self.assertIn("# Your First Synrail Run", first_run_guide)
        self.assertIn("Only `Status: Accepted` means the task may be reported as complete.", first_run_guide)
        self.assertIn("make install-dev", first_run_guide)
        self.assertIn("py -3 -m venv .venv", first_run_guide)
        self.assertIn("## 1. Prove One Small Tracked Change", first_run_guide)
        self.assertIn("synrail record path/to/file", first_run_guide)
        self.assertIn("synrail record --all-modified", first_run_guide)
        self.assertIn("## 2. Enforce A Behavioral Claim", first_run_guide)
        self.assertIn("synrail preflight", first_run_guide)
        self.assertIn("synrail verify", first_run_guide)
        self.assertIn("[Behavioral Verification Profiles](../advanced/VERIFICATION_PROFILES.md)", first_run_guide)
        self.assertIn("## 3. Keep Artifacts Outside Many Repositories", first_run_guide)
        self.assertIn("synrail cleanup --ephemeral", first_run_guide)
        self.assertIn("[Repo-Clean Workflows](../advanced/REPO_CLEAN_WORKFLOWS.md)", first_run_guide)
        self.assertIn("## Read A Non-Green Result", first_run_guide)
        self.assertIn("make install-local", first_run_guide)
        self.assertIn("--policy-mode focused", first_run_guide)
        self.assertIn("ordinary read-only questions, planning, and code review outside", first_run_guide)
        self.assertIn("`start` -> `record` -> optional `verify` -> `check`", first_run_guide)
        self.assertNotIn("python3 tools/reference/synrail_install_v0.py", first_run_guide)

        self.assertIn("# Behavioral Verification Profiles", profiles_guide)
        self.assertIn("synrail suggest-verification", profiles_guide)
        self.assertIn("synrail init-verification --name unit -- @synrail-python -m pytest -q", profiles_guide)
        self.assertIn("Behavioral verification: READY", profiles_guide)
        self.assertIn("A convenient read-only `grep` proof cannot substitute", profiles_guide)
        self.assertIn("Do not put secrets in `argv`", normalized_profiles_guide)
        self.assertIn("suggestion only: it never executes a candidate", normalized_profiles_guide)
        self.assertIn("not a hostile\nsame-user boundary", profiles_guide)
        self.assertIn("receipt_hmac.key", profiles_guide)

        self.assertIn("# Repo-Clean Workflows", repo_clean_guide)
        self.assertIn("synrail start --ephemeral", repo_clean_guide)
        self.assertIn("synrail cleanup --ephemeral", repo_clean_guide)
        self.assertIn("synrail cleanup --ephemeral --stale", repo_clean_guide)
        self.assertIn("A process killed mid-run cannot promise instant cleanup.", repo_clean_guide)
        self.assertIn("Use the same `--ephemeral` and `--project-root` values", repo_clean_guide)
        self.assertIn("PATH_SCOPE_VIOLATION", repo_clean_guide)
        self.assertIn("Do not use `git -c`, `--ext-diff`, `--textconv`", repo_clean_guide)
        self.assertIn("multi-command snippets", repo_clean_guide)
        self.assertIn('$env:PYTHONUTF8 = "1"', repo_clean_guide)

        self.assertIn("# Synrail Documentation", docs_readme)
        self.assertIn("## Current User Path", docs_readme)
        self.assertIn("Most first runs need only the README and First Run Guide.", docs_readme)
        self.assertIn("## Historical Review And Research", docs_readme)
        self.assertIn("# Synrail Review And History", review_readme)
        self.assertIn("This directory is evidence and maintainer history, not a setup guide.", review_readme)

        template = subprocess.run(
            [PYTHON, str(REPO_ROOT / "alpha.py"), "final-result-template", "--ephemeral"],
            check=True,
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
        ).stdout
        self.assertIn("Keep diff_provenance.verification_command recheckable", template)
        self.assertIn("Do not use pipes, &&, sed, awk, perl, subshells, or multi-command snippets.", template)

        current_user_docs = {
            "README.md": public_readme,
            "docs/core/FIRST_RUN_GUIDE.md": first_run_guide,
            "docs/advanced/VERIFICATION_PROFILES.md": profiles_guide,
            "docs/advanced/REPO_CLEAN_WORKFLOWS.md": repo_clean_guide,
            "tools/reference/README.md": reference_readme,
        }
        for name, content in current_user_docs.items():
            with self.subTest(current_user_doc=name):
                self.assertNotIn("python3 tools/reference/synrail_install_v0.py --venv .venv", content)
                self.assertNotIn("python3 tools/reference/synrail_install_v0.py", content)

        demo_readme = (REPO_ROOT / "examples" / "false_green_demo.md").read_text()
        demo_pack_readme = (REPO_ROOT / "examples" / "false-green-demo" / "README.md").read_text()
        demo_script = (REPO_ROOT / "examples" / "false-green-demo" / "run_demo.sh").read_text()
        demo_transcript = (REPO_ROOT / "examples" / "false-green-demo" / "transcript.txt").read_text()
        demo_assets_root = REPO_ROOT / "examples" / "false-green-demo" / "assets"
        benchmark_readme = (REPO_ROOT / "examples" / "false-green-benchmark" / "README.md").read_text()
        benchmark_cases = (REPO_ROOT / "examples" / "false-green-benchmark" / "cases.csv").read_text()
        deploy_guard_readme = (REPO_ROOT / "examples" / "deploy_guard" / "README.md").read_text()
        examples_index = (REPO_ROOT / "examples" / "README.md").read_text()
        bug_template = (REPO_ROOT / ".github" / "ISSUE_TEMPLATE" / "bug_report.md").read_text()
        feature_template = (REPO_ROOT / ".github" / "ISSUE_TEMPLATE" / "feature_request.md").read_text()
        false_green_template = (REPO_ROOT / ".github" / "ISSUE_TEMPLATE" / "false_green_case.yml").read_text()
        confusing_output_template = (REPO_ROOT / ".github" / "ISSUE_TEMPLATE" / "confusing_output.yml").read_text()
        alpha_feedback_template = (REPO_ROOT / ".github" / "ISSUE_TEMPLATE" / "alpha_feedback.yml").read_text()
        launch_packet = (REPO_ROOT / "docs" / "review" / "PUBLIC_LAUNCH_PACKET_001.md").read_text()
        first_tester_protocol = (REPO_ROOT / "docs" / "review" / "FIRST_TESTER_PROTOCOL_001.md").read_text()
        first_tester_checklist = (REPO_ROOT / "docs" / "review" / "FIRST_TESTER_CHECKLIST_2026-07.md").read_text()
        server_gemini_finding = (REPO_ROOT / "docs" / "review" / "SERVER_GEMINI_ALPHA_FINDING_001.md").read_text()
        roadmap_status = (REPO_ROOT / "docs" / "review" / "ROADMAP_STATUS_001.md").read_text()
        ci_workflow = (REPO_ROOT / ".github" / "workflows" / "security-hygiene.yml").read_text()
        project_metadata = (REPO_ROOT / "pyproject.toml").read_text()
        contributing = (REPO_ROOT / "CONTRIBUTING.md").read_text()
        security = (REPO_ROOT / "SECURITY.md").read_text()
        pull_request_template = (REPO_ROOT / ".github" / "pull_request_template.md").read_text()
        self.assertIn("# False-Green Demo", demo_readme)
        self.assertIn("Verification unit: FAIL (exit 1)", demo_readme)
        self.assertIn("Synrail: Status: Verification Failed", demo_readme)
        self.assertIn("Synrail: Status: Accepted", demo_readme)
        self.assertIn("only `Status: Accepted` closes the loop", demo_readme)
        self.assertIn("FIRST_TESTER_PROTOCOL_001.md", demo_readme)
        self.assertIn("GitHub issue templates", demo_readme)
        self.assertIn("# False-Green Demo", demo_pack_readme)
        self.assertIn("Run it in under two minutes", demo_pack_readme)
        self.assertIn("1. plausible proof cannot hide a red required test", demo_pack_readme)
        self.assertIn("2. behavioral repair turns the operator-owned profile green", demo_pack_readme)
        self.assertIn("3. accepted closure appears only after fresh verification", demo_pack_readme)
        self.assertIn("./run_demo.sh", demo_pack_readme)
        self.assertIn("`synrail` command when available", demo_pack_readme)
        self.assertIn("this is not a", demo_pack_readme)
        self.assertIn("prewritten transcript printer", demo_pack_readme)
        self.assertIn("assets/synrail-false-green-hero.gif", demo_pack_readme)
        self.assertIn("assets/synrail-false-green-hero.mp4", demo_pack_readme)
        self.assertIn("assets/synrail-false-green-hero-poster.png", demo_pack_readme)
        self.assertIn("hero.tape", demo_pack_readme)
        self.assertTrue((REPO_ROOT / "examples" / "false-green-demo" / "hero.tape").is_file())
        self.assertTrue((demo_assets_root / "synrail-false-green-hero.gif").is_file())
        self.assertTrue((demo_assets_root / "synrail-false-green-hero.mp4").is_file())
        self.assertTrue((demo_assets_root / "synrail-false-green-hero-poster.png").is_file())
        self.assertIn("FIRST_TESTER_PROTOCOL_001.md", demo_pack_readme)
        self.assertIn("GitHub issue templates", demo_pack_readme)
        self.assertIn('"${SYNRAIL[@]}" check --artifact-root .synrail', demo_script)
        self.assertIn('.venv/Scripts/synrail.exe', demo_script)
        self.assertIn('SYNRAIL=("$PYTHON" "$REPO_ROOT/alpha.py")', demo_script)
        self.assertIn("Demo assertion failed", demo_script)
        self.assertIn("Verification unit: FAIL (exit 1)", demo_transcript)
        self.assertIn("Synrail: Status: Verification Failed", demo_transcript)
        self.assertIn("Verification unit: GREEN", demo_transcript)
        self.assertIn("Synrail: Status: Accepted", demo_transcript)
        self.assertIn("plausible proof blocked while tests were red; verified behavior accepted", demo_transcript)
        self.assertIn("false-green-demo/", examples_index)
        self.assertIn("false-green-benchmark/", examples_index)
        self.assertIn("`false_green_demo.md`", examples_index)
        self.assertIn("FIRST_TESTER_PROTOCOL_001.md", examples_index)
        self.assertIn("GitHub issue templates", examples_index)
        self.assertIn("# False-Green Benchmark Starter", benchmark_readme)
        self.assertIn("curated local starter scaffold", benchmark_readme)
        self.assertIn("## How to use it", benchmark_readme)
        self.assertIn("## How to read the result labels", benchmark_readme)
        self.assertIn("`repair-needed` means the contour exposed useful signal", benchmark_readme)
        self.assertIn("not measured external rates", benchmark_readme)
        self.assertIn("FIRST_TESTER_PROTOCOL_001.md", benchmark_readme)
        self.assertIn("GitHub issue templates", benchmark_readme)
        self.assertIn("# Deploy Guard Examples", deploy_guard_readme)
        self.assertIn("FIRST_TESTER_PROTOCOL_001.md", deploy_guard_readme)
        self.assertIn("GitHub issue templates", deploy_guard_readme)
        self.assertIn("Case family,Agent claim,Reality,Synrail result,Manual effort,Overhead notes", benchmark_cases)
        self.assertIn("Partial catch,\"done\",\"one issue caught, another still implied safe\",\"repair-needed\"", benchmark_cases)
        self.assertIn("name: Bug report", bug_template)
        self.assertIn("labels: bug, ownership:needs-triage", bug_template)
        self.assertIn("primary owner assigned", bug_template)
        self.assertIn("do not attach secrets", bug_template)
        self.assertIn("private path in `SECURITY.md`", bug_template)
        self.assertIn("current local alpha lane", bug_template)
        self.assertIn("name: Feature request", feature_template)
        self.assertIn("belongs in Synrail itself", feature_template)
        self.assertIn("current proof-first local alpha lane", feature_template)
        self.assertIn("name: False-green case", false_green_template)
        self.assertIn("Did Synrail catch it?", false_green_template)
        self.assertIn("ownership:needs-triage", false_green_template)
        self.assertIn("Exact Synrail command, redacted working directory, and artifact mode", false_green_template)
        self.assertIn("Do not paste secrets, private source, absolute paths", false_green_template)
        self.assertIn("name: Confusing output", confusing_output_template)
        self.assertIn("Which output was confusing?", confusing_output_template)
        self.assertIn("ownership:needs-triage", confusing_output_template)
        self.assertIn("Did the standalone demo pass on the same install?", confusing_output_template)
        self.assertIn("Do not paste secrets, private source, absolute paths", confusing_output_template)
        self.assertIn("name: Alpha feedback", alpha_feedback_template)
        self.assertIn("Would you use it again?", alpha_feedback_template)
        self.assertIn("ownership:needs-triage", alpha_feedback_template)
        self.assertIn("Which lane did you try?", alpha_feedback_template)
        self.assertIn("Do not paste secrets, private source, absolute paths", alpha_feedback_template)
        self.assertIn("## Issue guidance", contributing)
        self.assertIn("Use the GitHub issue templates to keep bug reports and feature requests bounded.", contributing)
        self.assertIn("ownership:needs-triage", contributing)
        self.assertIn("require a failing", contributing)
        self.assertIn("regression before a product-owned kernel fix", contributing)
        self.assertIn("## Change Category", pull_request_template)
        self.assertIn("## Risk Surface", pull_request_template)
        self.assertIn("## Split / Scope Check", pull_request_template)
        self.assertIn("- [ ] trust/kernel", pull_request_template)
        self.assertIn("- [ ] This change is small enough to review.", pull_request_template)
        self.assertIn("# Security Policy", security)
        self.assertIn("GitHub private vulnerability reporting", security)
        self.assertIn("attach an unredacted `synrail bug-packet` to a public issue", security)
        self.assertIn("current local alpha support boundary", security)
        self.assertIn("# Public Launch Packet 001", launch_packet)
        self.assertIn("## Twitter/X thread", launch_packet)
        self.assertIn("## LinkedIn post", launch_packet)
        self.assertIn("## GitHub / HN launch blurb", launch_packet)
        self.assertIn("## First tester protocol", launch_packet)
        self.assertIn("local acceptance gate", launch_packet)
        self.assertIn("It complements CI and code review", launch_packet)
        self.assertIn("Use `FIRST_TESTER_PROTOCOL_001.md` as the shareable one-page handoff.", launch_packet)
        self.assertIn("Read the repo README first screen.", launch_packet)
        self.assertIn("Try one real small local task.", launch_packet)
        self.assertIn("narrow local alpha signal, not broad product readiness proof", launch_packet)
        self.assertIn("## Public-signal freeze rule", roadmap_status)
        self.assertIn("During the current public-signal period, only these changes should land:", roadmap_status)
        self.assertIn("- install-path fixes", roadmap_status)
        self.assertIn("- kernel growth", roadmap_status)
        self.assertIn("# First Tester Protocol 001", first_tester_protocol)
        self.assertIn("Use the GitHub issue templates:", first_tester_protocol)
        self.assertIn("False-green case", first_tester_protocol)
        self.assertIn('synrail start --ephemeral "Describe the bounded local change."', first_tester_protocol)
        self.assertIn("synrail record path/to/file --ephemeral", first_tester_protocol)
        self.assertIn("## Maintainer triage before any kernel change", first_tester_protocol)
        self.assertIn("ownership:product", first_tester_protocol)
        self.assertIn("ownership:operator", first_tester_protocol)
        self.assertIn("ownership:harness", first_tester_protocol)
        self.assertIn("Remove `ownership:needs-triage` when the primary owner is assigned.", first_tester_protocol)
        self.assertIn('export PATH="$PWD/.venv/bin:$PATH"', first_tester_checklist)
        self.assertIn("Windows PowerShell: `py -3 -m venv .venv`", first_tester_checklist)
        self.assertIn("python.exe -m pip install --upgrade pip", first_tester_checklist)
        self.assertIn("from Git Bash", first_tester_checklist)
        self.assertIn('synrail start --ephemeral "one sentence describing the change"', first_tester_checklist)
        self.assertIn("synrail record path/to/file --ephemeral", first_tester_checklist)
        self.assertIn("synrail cleanup --ephemeral", first_tester_checklist)
        self.assertIn("actions/checkout@df4cb1c069e1874edd31b4311f1884172cec0e10", ci_workflow)
        self.assertIn("actions/setup-python@ece7cb06caefa5fff74198d8649806c4678c61a1", ci_workflow)
        self.assertIn("gitleaks/gitleaks-action@e0c47f4f8be36e29cdc102c57e68cb5cbf0e8d1e", ci_workflow)
        self.assertIn('python-version: ["3.11", "3.12", "3.13", "3.14"]', ci_workflow)
        self.assertIn("Receipt Key Lifecycle", profiles_guide)
        self.assertIn("receipt_hmac.key", profiles_guide)
        self.assertNotIn("uses: actions/checkout@v4", ci_workflow)
        self.assertNotIn("uses: actions/setup-python@v5", ci_workflow)
        self.assertIn(
            'description = "Local acceptance gate that blocks false-green coding-agent claims until task-scoped proof is rechecked."',
            project_metadata,
        )
        self.assertIn("# Server Gemini Alpha Finding 001", server_gemini_finding)
        self.assertIn("PATH_SCOPE_VIOLATION", server_gemini_finding)
        self.assertIn("This is a useful alpha integration finding, not a clean success case.", server_gemini_finding)
        self.assertIn("/root/docs/review/SERVER_GEMINI_ALPHA_FINDING_001.md", server_gemini_finding)

        self.assertIn("strengthen final_result.json first", reference_readme)
        self.assertIn("leave readback/scenario_proof untouched unless synrail check later names them", reference_readme)
        self.assertIn("focus on `final_result.json`: status, changed files, and diff/provenance first", reference_readme)

    def test_current_docs_local_markdown_targets_exist(self) -> None:
        """Keep the curated onboarding path navigable as docs are reorganized."""
        current_docs = (
            REPO_ROOT / "README.md",
            REPO_ROOT / "docs" / "README.md",
            REPO_ROOT / "docs" / "core" / "FIRST_RUN_GUIDE.md",
            REPO_ROOT / "docs" / "advanced" / "VERIFICATION_PROFILES.md",
            REPO_ROOT / "docs" / "advanced" / "REPO_CLEAN_WORKFLOWS.md",
            REPO_ROOT / "docs" / "review" / "README.md",
        )
        markdown_target = re.compile(r"!?\[[^\]]+\]\(([^)]+)\)")

        for document in current_docs:
            for target in markdown_target.findall(document.read_text()):
                local_target = target.split("#", 1)[0]
                if not local_target or "://" in local_target or local_target.startswith("mailto:"):
                    continue
                with self.subTest(document=document.relative_to(REPO_ROOT), target=target):
                    self.assertTrue((document.parent / local_target).exists())


if __name__ == "__main__":
    unittest.main()
