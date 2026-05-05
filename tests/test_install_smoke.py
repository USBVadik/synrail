#!/usr/bin/env python3
"""Install smoke for the supported Synrail tester path."""

from __future__ import annotations

import os
import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
INSTALLER = REPO_ROOT / "tools" / "reference" / "synrail_install_v0.py"


class InstallSmokeTests(unittest.TestCase):
    def _assert_installed_start_path(self, synrail_bin: Path, project_root: Path) -> None:
        artifact_root = project_root / ".synrail"

        help_result = subprocess.run(
            [str(synrail_bin), "start", "--help"],
            check=True,
            capture_output=True,
            text=True,
        )
        self.assertIn("--project-root", help_result.stdout)
        self.assertIn("--task-identity", help_result.stdout)
        self.assertIn("task_request", help_result.stdout)

        project_root.mkdir(parents=True, exist_ok=True)
        start_result = subprocess.run(
            [
                str(synrail_bin),
                "start",
                "install smoke",
            ],
            check=True,
            cwd=project_root,
            capture_output=True,
            text=True,
        )

        self.assertIn("Controlled run started.", start_result.stdout)
        self.assertIn(
            "Do this now: make the bounded change, run local verification, then strengthen final_result.json first.",
            start_result.stdout,
        )
        self.assertIn("Starter proof surface is ready for this run.", start_result.stdout)
        self.assertIn("Artifact root: .synrail", start_result.stdout)
        self.assertIn("fallback note: readback.txt and scenario_proof.txt stay hidden by default unless a later synrail check names one.", start_result.stdout)
        self.assertIn("Need a canonical final_result shape? run synrail final-result-template", start_result.stdout)
        self.assertIn("Then run: synrail check", start_result.stdout)
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

            subprocess.run(
                ["python3", str(INSTALLER), "--venv", str(venv_dir)],
                check=True,
                cwd=REPO_ROOT,
                capture_output=True,
                text=True,
            )
            self._assert_installed_start_path(
                venv_dir / "bin" / "synrail",
                project_root,
            )

    def test_supported_installer_is_idempotent(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_editable_install_smoke_") as tmpdir:
            root = Path(tmpdir)
            venv_dir = root / "venv"
            project_root = root / "project"

            subprocess.run(
                ["python3", str(INSTALLER), "--venv", str(venv_dir)],
                check=True,
                cwd=REPO_ROOT,
                capture_output=True,
                text=True,
            )
            subprocess.run(
                ["python3", str(INSTALLER), "--venv", str(venv_dir)],
                check=True,
                cwd=REPO_ROOT,
                capture_output=True,
                text=True,
            )
            self._assert_installed_start_path(
                venv_dir / "bin" / "synrail",
                project_root,
            )

    def test_supported_installer_can_install_agent_files_into_project(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_install_agent_files_smoke_") as tmpdir:
            root = Path(tmpdir)
            venv_dir = root / "venv"
            project_root = root / "project"
            project_root.mkdir(parents=True, exist_ok=True)
            (project_root / "alpha.py").write_text("print('stub')\n")
            (project_root / "GEMINI.md").write_text("# Existing Gemini Context\n\nKeep this repo focused.\n")

            result = subprocess.run(
                [
                    "python3",
                    str(INSTALLER),
                    "--venv",
                    str(venv_dir),
                    "--project-root",
                    str(project_root),
                ],
                check=True,
                cwd=REPO_ROOT,
                capture_output=True,
                text=True,
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
            self.assertIn("Do not create helper scripts or make edits for an orientation-only question.", gemini)
            self.assertIn("Do not turn project recall into repo archaeology.", gemini)
            self.assertIn("Use Synrail as the default local control path", claude)
            self.assertIn("cheapest honest order", claude)
            self.assertIn("If `git` is unavailable on this host, do not invent `git_diff`", claude)
            self.assertIn("Do not create helper scripts or make edits for an orientation-only question.", claude)

    def test_first_run_guide_mentions_preflight_and_git_missing_path(self) -> None:
        first_run_guide = (REPO_ROOT / "docs" / "core" / "FIRST_RUN_GUIDE.md").read_text()
        public_readme = (REPO_ROOT / "README.md").read_text()
        docs_readme = (REPO_ROOT / "docs" / "README.md").read_text()
        review_readme = (REPO_ROOT / "docs" / "review" / "README.md").read_text()
        reference_readme = (REPO_ROOT / "tools" / "reference" / "README.md").read_text()

        self.assertIn("Agent: tests passed", first_run_guide)
        self.assertIn("Synrail: Status: Proof Invalid", first_run_guide)
        self.assertIn("Reason: verification command not executed / freshness mismatch", first_run_guide)
        self.assertIn("Next: repair final_result.json", first_run_guide)
        self.assertIn("Only `Status: Accepted` means the task may be reported as complete.", first_run_guide)
        self.assertIn("On the normal happy path, treat it as the only proof surface you need to touch.", first_run_guide)
        self.assertIn("leave `readback.txt` untouched unless `synrail check` explicitly names it", first_run_guide)
        self.assertIn("leave `scenario_proof.txt` untouched unless `synrail check` explicitly names it", first_run_guide)
        self.assertIn("Only if `check` later targets a fallback prose surface, use:", first_run_guide)
        self.assertIn("Git Preflight", first_run_guide)
        self.assertIn("synrail preflight", first_run_guide)
        self.assertIn("python3 alpha.py preflight", first_run_guide)
        self.assertIn("Git is not installed. Synrail can still use structured diff_provenance, but git_diff and restore coverage will be weaker. Install git for the normal path.", first_run_guide)
        self.assertIn("If `git` is missing, Synrail can still run. Do not invent a `git_diff`.", first_run_guide)
        self.assertIn("leave `git_diff` empty and use structured provenance instead", first_run_guide)
        self.assertIn("for a multi-file change, use `diff_provenance_records` or `per_file_diff_provenance`", first_run_guide)
        self.assertIn('python3 alpha.py start "Describe the bounded local change."', first_run_guide)
        self.assertIn("python3 alpha.py check", first_run_guide)
        self.assertIn("Repeat until `synrail check` prints `Status: Accepted`.", first_run_guide)
        self.assertIn("`Status: Accepted` means the proof bundle is complete", first_run_guide)
        self.assertIn("`Proof Too Thin To Trust` -- structure is there but evidence is thin.", first_run_guide)
        self.assertIn("`Cannot Continue This Run` -- this run reached a terminal rejected state.", first_run_guide)

        self.assertIn("Synrail catches false-green AI-agent work before you accept it.", public_readme)
        self.assertIn('The failure mode is simple: an agent says "done", the tests look plausible, and the operator is still missing trustworthy proof.', public_readme)
        self.assertIn("Synrail exists to hold that line between execution and acceptance.", public_readme)
        self.assertIn("## 30-Second Demo", public_readme)
        self.assertIn("Agent: tests passed", public_readme)
        self.assertIn("Synrail: Status: Proof Invalid", public_readme)
        self.assertIn("Synrail: Status: Accepted", public_readme)
        self.assertIn("See the standalone [false-green demo](examples/false_green_demo.md).", public_readme)
        self.assertIn("The point is not to make agent output sound confident. The point is to stop false-green closure before it gets accepted as truth.", public_readme)
        self.assertIn("## When To Use It", public_readme)
        self.assertIn("## When Not To Use It", public_readme)
        self.assertIn("narrow local alpha product", public_readme)
        self.assertIn("not yet broad self-serve or broad production-ready", public_readme)
        self.assertIn("[Docs Map](docs/README.md)", public_readme)
        self.assertIn("[Review archive map](docs/review/README.md)", public_readme)

        self.assertIn("This is the short current source-of-truth reading path for the repo.", docs_readme)
        self.assertIn("core/FIRST_RUN_GUIDE.md", docs_readme)
        self.assertIn("core/SYNRAIL_RUNTIME_TRUTH_SURFACE.md", docs_readme)
        self.assertIn("Use `docs/review/README.md` only after this map", docs_readme)
        self.assertIn("This index is for deeper review, critique, and outreach material.", review_readme)
        self.assertIn("It is not the primary public source-of-truth reading path for the repo.", review_readme)

        demo_readme = (REPO_ROOT / "examples" / "false_green_demo.md").read_text()
        examples_index = (REPO_ROOT / "examples" / "README.md").read_text()
        bug_template = (REPO_ROOT / ".github" / "ISSUE_TEMPLATE" / "bug_report.md").read_text()
        feature_template = (REPO_ROOT / ".github" / "ISSUE_TEMPLATE" / "feature_request.md").read_text()
        contributing = (REPO_ROOT / "CONTRIBUTING.md").read_text()
        security = (REPO_ROOT / "SECURITY.md").read_text()
        pull_request_template = (REPO_ROOT / ".github" / "pull_request_template.md").read_text()
        self.assertIn("# False-Green Demo", demo_readme)
        self.assertIn("Next: repair final_result.json", demo_readme)
        self.assertIn("Synrail: Status: Accepted", demo_readme)
        self.assertIn("only `Status: Accepted` closes the loop", demo_readme)
        self.assertIn("`false_green_demo.md`", examples_index)
        self.assertIn("name: Bug report", bug_template)
        self.assertIn("synrail bug-packet --artifact-root .synrail", bug_template)
        self.assertIn("current local alpha lane", bug_template)
        self.assertIn("name: Feature request", feature_template)
        self.assertIn("belongs in Synrail itself", feature_template)
        self.assertIn("current proof-first local alpha lane", feature_template)
        self.assertIn("## Issue guidance", contributing)
        self.assertIn("Use the GitHub issue templates to keep bug reports and feature requests bounded.", contributing)
        self.assertIn("## Change Category", pull_request_template)
        self.assertIn("## Risk Surface", pull_request_template)
        self.assertIn("## Split / Scope Check", pull_request_template)
        self.assertIn("- [ ] trust/kernel", pull_request_template)
        self.assertIn("- [ ] This change is small enough to review.", pull_request_template)
        self.assertIn("# Security Policy", security)
        self.assertIn("Please open a GitHub bug report only for issues that belong in Synrail itself.", security)
        self.assertIn("synrail bug-packet --artifact-root .synrail", security)
        self.assertIn("current local alpha support boundary", security)

        self.assertIn("strengthen final_result.json first", reference_readme)
        self.assertIn("leave readback/scenario_proof untouched unless synrail check later names them", reference_readme)
        self.assertIn("focus on `final_result.json`: status, changed files, and diff/provenance first", reference_readme)


if __name__ == "__main__":
    unittest.main()
